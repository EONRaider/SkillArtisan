#!/usr/bin/env python3
"""Execute a contribution against a third-party skill repository: branch,
commit, push, and open a PR — the real-effects counterpart to
`audit.py pr-plan`'s plan-only output.

Row 32, execution half. `pr-plan` computes what's broken and prints a plan;
it never touches git or `gh`. This script is the opposite: it assumes the
actual fix content has ALREADY been applied to a local clone's working tree
— by the orchestrator, using normal Read/Edit/Write, the same way any other
real fix in a session gets made — and its own job is purely the mechanical
git/gh sequence around that already-made change. Content authoring is
high-freedom, judgment-heavy work; branching/committing/pushing/opening a PR
is low-freedom, exact-script territory (references/writing-philosophy.md's
degrees-of-freedom tiers) — this script is deliberately scoped to only the
second half, not both.

**The confirmation gate is structural, not a script feature.** This script
has no interactive prompt (script-design.md: non-interactive only, no
blocking input()) and no "--yes"/auto-confirm flag that could let a
confirmation be skipped programmatically. `--execute` is the only thing that
unlocks real side effects, and per creating-skills/SKILL.md's "Auditing
existing skills" subsection 6, the orchestrator must obtain a separate,
explicit human confirmation in chat before ever passing it — every time, not
once per skill. This script cannot obtain that confirmation itself; it can
only refuse to run without something already having decided to pass
`--execute`, which is exactly why the decision has to happen one layer up.

**Hard invariant, not a suggestion**: refuses (exit 4) if the working tree's
changes include any deleted or renamed file relative to the base branch.
Additive-only is the entire trust basis for touching a repository this
plugin doesn't own, so this is checked mechanically, not left to the
orchestrator's discretion.

**Idempotent**: if a branch/PR already exists for this skill+upstream
combination (deterministic branch name, not time-stamped), the script
short-circuits to the existing PR's URL rather than opening a duplicate —
verified via `gh pr list`, not assumed from local state alone (a prior run's
branch could exist locally without a corresponding PR, or vice versa after
a fetch).

Usage:
    python scripts/pr_execute.py <clone-path> --upstream-repo <owner/repo> --skill-name <name> --dry-run
    python scripts/pr_execute.py <clone-path> --upstream-repo <owner/repo> --skill-name <name> --execute \
        --pr-title "..." --pr-body-file <path>

`<clone-path>` is a local git clone of (a fork of) `<upstream-repo>`, with
the additive fix already present as uncommitted changes in the working tree.

Exit codes: 0 success (PR opened, or idempotent no-op returning an existing
PR's URL), 2 invalid path/arguments, 3 nothing to contribute (no uncommitted
changes), 4 non-additive change detected (deletion/rename — hard refusal),
10 gh not installed, 11 gh not authenticated, 12 fork failed, 13 push
failed, 14 PR creation failed.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

# git status --porcelain codes that indicate a deletion or rename anywhere
# in either the index or working-tree column — the additive-only invariant.
NON_ADDITIVE_CODES = {"D", "R"}


def run_git(repo_path: Path, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo_path), *args], capture_output=True, text=True, timeout=30)


def run_gh(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True, timeout=timeout)


def check_gh_available() -> tuple[bool, bool]:
    """Returns (installed, authenticated)."""
    if not shutil.which("gh"):
        return False, False
    try:
        result = run_gh(["auth", "status"])
    except subprocess.TimeoutExpired:
        return True, False
    return True, result.returncode == 0


def get_change_status(repo_path: Path) -> list[tuple[str, str]]:
    """Parse `git status --porcelain` into (status_code, path) pairs. Two-
    character status codes (index + working tree) are kept whole, since a
    deletion can show up in either column (e.g. " D" or "D ")."""
    result = run_git(repo_path, ["status", "--porcelain"])
    changes = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        code, path = line[:2], line[3:]
        changes.append((code, path))
    return changes


def verify_additive_only(changes: list[tuple[str, str]]) -> tuple[bool, list[str]]:
    """Hard invariant: no deletion or rename anywhere in the change set."""
    violations = []
    for code, path in changes:
        if any(c in NON_ADDITIVE_CODES for c in code):
            violations.append(f"{code.strip() or code} {path}")
    return not violations, violations


def get_diff_summary(repo_path: Path) -> str:
    result = run_git(repo_path, ["diff", "--stat", "HEAD"])
    return result.stdout.strip()


def get_current_remote_url(repo_path: Path) -> str:
    result = run_git(repo_path, ["remote", "get-url", "origin"])
    return result.stdout.strip()


BRANCH_SAFE_RE = re.compile(r"[^a-z0-9._-]+")


def branch_name_for(skill_name: str) -> str:
    """Deterministic, not time-stamped — this is what makes the idempotency
    check possible. Re-running against the same skill finds the same branch
    rather than piling up a new one per attempt."""
    safe = BRANCH_SAFE_RE.sub("-", skill_name.lower()).strip("-")
    return f"skillartisan-audit-fix-{safe}"


def find_existing_pr(upstream_repo: str, fork_owner: str, branch: str) -> str | None:
    result = run_gh([
        "pr", "list", "--repo", upstream_repo,
        "--head", f"{fork_owner}:{branch}", "--state", "all",
        "--json", "url", "--jq", ".[0].url",
    ])
    url = result.stdout.strip()
    return url or None


def get_authenticated_login() -> str | None:
    result = run_gh(["api", "user", "--jq", ".login"])
    login = result.stdout.strip()
    return login or None


def ensure_fork(upstream_repo: str) -> tuple[bool, str]:
    """gh repo fork is itself idempotent — safe to call whether or not a
    fork already exists. Returns (ok, fork_owner_or_error)."""
    login = get_authenticated_login()
    if not login:
        return False, "could not determine authenticated gh user"
    result = run_gh(["repo", "fork", upstream_repo, "--clone=false"], timeout=60)
    if result.returncode != 0 and "already exists" not in (result.stderr + result.stdout).lower():
        return False, (result.stderr or result.stdout).strip()
    return True, login


def create_branch_commit_push(repo_path: Path, branch: str, commit_message: str, fork_owner: str, repo_name: str) -> tuple[bool, str]:
    checkout = run_git(repo_path, ["checkout", "-B", branch])
    if checkout.returncode != 0:
        return False, checkout.stderr.strip()

    add = run_git(repo_path, ["add", "-A"])
    if add.returncode != 0:
        return False, add.stderr.strip()

    commit = run_git(repo_path, ["commit", "-m", commit_message])
    if commit.returncode != 0:
        return False, commit.stderr.strip()

    push = run_git(repo_path, ["push", "--set-upstream", "origin", branch])
    if push.returncode != 0:
        # origin might be the upstream repo itself (read-only for us) rather
        # than the fork — retry against the fork's URL explicitly rather
        # than assuming "origin" is always right.
        fork_url = f"git@github.com:{fork_owner}/{repo_name}.git"
        push = run_git(repo_path, ["push", "--set-upstream", fork_url, branch])
        if push.returncode != 0:
            return False, push.stderr.strip()
    return True, ""


def open_pr(upstream_repo: str, fork_owner: str, branch: str, base_branch: str, title: str, body: str) -> tuple[bool, str]:
    result = run_gh([
        "pr", "create", "--repo", upstream_repo,
        "--base", base_branch, "--head", f"{fork_owner}:{branch}",
        "--title", title, "--body", body,
    ], timeout=60)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()
    url = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    return True, url


DEFAULT_PR_BODY_TEMPLATE = """This is an additive-only contribution generated with SkillArtisan's audit
mode (`scripts/pr_execute.py`), following its checklist findings for this
skill. Every change here is either a pure addition or an in-place fix to
something the audit found broken — nothing existing was deleted or renamed.

See the diff for the specific changes.
"""


def get_default_branch(repo_path: Path) -> str:
    result = run_git(repo_path, ["remote", "show", "origin"])
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("HEAD branch:"):
            return line.split(":", 1)[1].strip()
    return "main"


def cmd(args: argparse.Namespace) -> int:
    repo_path = Path(args.clone_path).resolve()
    if not repo_path.is_dir() or not (repo_path / ".git").exists():
        print(f"Error: not a git repository: {repo_path}", file=sys.stderr)
        return 2

    installed, authenticated = check_gh_available()
    if not installed:
        print("Error: gh not installed — see https://cli.github.com", file=sys.stderr)
        return 10
    if not authenticated:
        print("Error: gh not authenticated — run `gh auth login`", file=sys.stderr)
        return 11

    changes = get_change_status(repo_path)
    if not changes:
        print("Nothing to contribute — no uncommitted changes in the working tree.", file=sys.stderr)
        print("This script executes fixes already applied by the orchestrator; it does not author them.", file=sys.stderr)
        return 3

    additive, violations = verify_additive_only(changes)
    if not additive:
        print("Refusing: non-additive change(s) detected — deletion or rename in a repo this plugin doesn't own:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 4

    branch = branch_name_for(args.skill_name)
    repo_name = args.upstream_repo.split("/")[-1]
    login = get_authenticated_login()
    fork_owner = login or "<unknown>"

    existing_pr = find_existing_pr(args.upstream_repo, fork_owner, branch) if login else None
    if existing_pr:
        print(f"Idempotent no-op: a PR already exists for {args.skill_name} against {args.upstream_repo}.", file=sys.stderr)
        print(existing_pr)
        return 0

    diff_summary = get_diff_summary(repo_path)
    base_branch = get_default_branch(repo_path)
    pr_title = args.pr_title or f"Additive fixes for {args.skill_name} (via SkillArtisan audit)"
    pr_body = Path(args.pr_body_file).read_text() if args.pr_body_file else DEFAULT_PR_BODY_TEMPLATE

    if args.dry_run:
        print(f"[dry-run] Would fork {args.upstream_repo} to {fork_owner}/{repo_name} (or reuse existing fork)", file=sys.stderr)
        print(f"[dry-run] Would create/reset branch: {branch}", file=sys.stderr)
        print(f"[dry-run] Would commit and push {len(changes)} changed file(s):", file=sys.stderr)
        for code, path in changes:
            print(f"    {code.strip():>2}  {path}", file=sys.stderr)
        print(f"\n[dry-run] Diff summary:\n{diff_summary}\n", file=sys.stderr)
        print(f"[dry-run] Would open PR: {args.upstream_repo} base={base_branch} <- {fork_owner}:{branch}", file=sys.stderr)
        print(f"[dry-run] Title: {pr_title}", file=sys.stderr)
        print("[dry-run] No git or gh mutation performed.", file=sys.stderr)
        return 0

    # --execute path — real side effects from here on. This branch only runs
    # when the caller has already passed --execute, which is the caller's
    # (the orchestrator's) job to gate on a separate, explicit human
    # confirmation obtained in chat — this script has no prompt of its own.
    fork_ok, fork_result = ensure_fork(args.upstream_repo)
    if not fork_ok:
        print(f"Error: fork failed — {fork_result}", file=sys.stderr)
        return 12
    fork_owner = fork_result

    commit_message = args.commit_message or f"Additive fixes for {args.skill_name} (via SkillArtisan audit)"
    push_ok, push_error = create_branch_commit_push(repo_path, branch, commit_message, fork_owner, repo_name)
    if not push_ok:
        print(f"Error: push failed — {push_error}", file=sys.stderr)
        return 13

    pr_ok, pr_result = open_pr(args.upstream_repo, fork_owner, branch, base_branch, pr_title, pr_body)
    if not pr_ok:
        print(f"Error: PR creation failed — {pr_result}", file=sys.stderr)
        return 14

    print(pr_result)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute an additive-only contribution (branch/commit/push/PR) against a third-party skill repo — the real-effects counterpart to audit.py pr-plan",
    )
    parser.add_argument("clone_path", help="Local git clone (of a fork of) the upstream repo, with the fix already applied as uncommitted changes")
    parser.add_argument("--upstream-repo", required=True, metavar="owner/repo", help="Upstream repository to open the PR against")
    parser.add_argument("--skill-name", required=True, help="Name of the skill being fixed (used for the deterministic branch name and default PR title)")
    parser.add_argument("--pr-title", default=None, help="PR title (default: generated from --skill-name)")
    parser.add_argument("--pr-body-file", default=None, help="Path to a file with the PR body (default: a generic additive-only-changes template)")
    parser.add_argument("--commit-message", default=None, help="Commit message (default: generated from --skill-name)")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Preview the branch/diff/PR that would be created — no git or gh mutation")
    mode.add_argument("--execute", action="store_true", help="Actually fork/branch/commit/push/open the PR. Only pass this after a separate, explicit human confirmation obtained in chat — this script has no confirmation prompt of its own.")
    parser.set_defaults(func=cmd)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
