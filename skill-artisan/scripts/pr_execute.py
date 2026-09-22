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
unlocks real side effects, and the decision to pass it always happens one
layer up.

**The default is per-run human confirmation.** Per creating-skills/SKILL.md's
"Auditing existing skills" subsection 6, the orchestrator must obtain a
separate, explicit human confirmation before ever passing `--execute` —
every time, not once per skill, and not once per session.

There is exactly one exception, and it is not a general one: **the GitHub
Action** (`../action.yml`, driven by `scripts/gha_audit.py`). There, a target
repo's maintainer installing the workflow and provisioning the
`ANTHROPIC_API_KEY` secret is itself the authorization event, and the run has
no human present to ask. The carve-out is scoped to that one caller and that
one reason — a human deliberately configured this exact automation on this
exact repository in advance.

Do not generalize it. "This context is automated", "this is CI", "this is a
non-interactive session", "the user already approved a similar run" are not
instances of the carve-out; they are the cases it excludes. Any caller other
than gha_audit.py's Action path needs a fresh human confirmation for each
`--execute`. Every other invariant below (additive-only, explicit staging,
lease-checked push, idempotent, no `--yes` flag) applies to the Action path
unchanged.

Either way, this script cannot obtain that confirmation itself; it can only
refuse to run without something already having decided to pass `--execute`.

**Hard invariant, not a suggestion**: refuses (exit 4) if the working tree's
changes include any deleted or renamed file relative to the base branch.
Additive-only is the entire trust basis for touching a repository this
plugin doesn't own, so this is checked mechanically, not left to the
orchestrator's discretion.

**Only the inspected changes are committed.** Staging is by explicit path
(the exact set `--dry-run` prints), never `git add -A`, so an unrelated file
sitting in the clone cannot ride along into a public PR. The push uses
`--force-with-lease`, so re-running resets this script's own branch as
intended but refuses to overwrite a remote branch that moved underneath it.
`--pr-body-file` must resolve inside the clone or the working directory and
is size-capped — its contents get published, so it is not an arbitrary file
read.

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

# GitHub rejects a PR body over 65536 characters outright, so anything
# larger is a mistake (a wrong path, a log file) rather than a long body.
MAX_PR_BODY_BYTES = 65536


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
    """Parse `git status --porcelain -z` into (status_code, path) pairs. Two-
    character status codes (index + working tree) are kept whole, since a
    deletion can show up in either column (e.g. " D" or "D ").

    `-z` rather than line-based parsing: without it git C-quotes any path
    containing a space, a quote, or a non-ASCII byte, so the path read back
    out is not the path on disk. That was tolerable while the paths were
    only ever printed, but they are now passed to `git add` as the exact set
    to stage (see stage_paths), and a mangled path there would either fail
    the add or stage the wrong thing.
    """
    result = run_git(repo_path, ["status", "--porcelain", "-z"])
    changes = []
    fields = [f for f in result.stdout.split("\0")]
    i = 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if not entry.strip():
            continue
        code, path = entry[:2], entry[3:]
        # A rename/copy entry is followed by its source path as a separate
        # NUL-terminated field. Consume it so it isn't read as a new entry.
        if code and code[0] in ("R", "C"):
            i += 1
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


def normalize_repo_slug(value: str) -> str:
    """owner/repo, whether given as a bare slug or a git remote URL (ssh or
    https, with or without a trailing .git)."""
    s = value.strip()
    if s.endswith(".git"):
        s = s[:-4]
    for prefix in ("git@github.com:", "https://github.com/", "http://github.com/"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return s.lower()


def is_same_repo(repo_path: Path, upstream_repo: str) -> bool:
    """True when repo_path's own `origin` remote already points at
    upstream_repo — this isn't a third-party repo at all, it's a repo
    running this against itself (e.g. the GitHub Action self-auditing its
    own installer repo). Checked directly rather than inferred from
    viewerPermission: found live, running the Action's fix-PR path in this
    repo's own CI — the ephemeral GITHUB_TOKEN issued to a workflow can push
    directly per the workflow's `permissions:` block, but isn't a
    collaborator, so `gh repo view --json viewerPermission` legitimately
    reports less than WRITE for it even though the token can push right
    now. That misled has_push_access into treating a same-repo run as
    fork-required, which then hard-failed — GitHub refuses to fork a repo
    into an account that already owns it."""
    remote = get_current_remote_url(repo_path)
    if not remote:
        return False
    return normalize_repo_slug(remote) == normalize_repo_slug(upstream_repo)


BRANCH_SAFE_RE = re.compile(r"[^a-z0-9._-]+")


def branch_name_for(skill_name: str) -> str:
    """Deterministic, not time-stamped — this is what makes the idempotency
    check possible. Re-running against the same skill finds the same branch
    rather than piling up a new one per attempt."""
    safe = BRANCH_SAFE_RE.sub("-", skill_name.lower()).strip("-")
    return f"skillartisan-audit-fix-{safe}"


def find_existing_pr(upstream_repo: str, fork_owner: str, branch: str, direct_push: bool) -> str | None:
    """`gh pr list --head` takes a bare branch name for a same-repo PR (the
    direct-push, no-fork case) but requires `owner:branch` for a cross-repo
    (forked) PR — using `owner:branch` unconditionally silently matches
    nothing in the same-repo case. Found live: a second run against a
    disposable repo the author already had push access to fell through this
    check entirely and attempted a real push that then failed on an
    unrelated non-fast-forward error, rather than being caught here first.

    Only OPEN PRs count as "already exists" — not `--state all`. A closed
    (unmerged) PR means the fix never landed, so the underlying finding is
    presumably still true and a later run should get a fresh attempt, not a
    permanent no-op citing a dead PR. Found live: closing a smoke-test PR as
    cleanup, then re-running against the same skill+repo, silently
    short-circuited to that same closed PR's URL every time afterward — the
    deterministic branch name means the head-branch match never changes, so
    with `--state all` this skill could never be proposed again. A merged PR
    isn't specifically excluded either, on the same reasoning: if the audit
    still finds the item failing after a merge, something about the merge
    didn't actually fix it, and a fresh attempt is the right response, not a
    silent no-op."""
    head_filter = branch if direct_push else f"{fork_owner}:{branch}"
    result = run_gh([
        "pr", "list", "--repo", upstream_repo,
        "--head", head_filter, "--state", "open",
        "--json", "url", "--jq", ".[0].url",
    ])
    url = result.stdout.strip()
    return url or None


def get_authenticated_login() -> str | None:
    result = run_gh(["api", "user", "--jq", ".login"])
    login = result.stdout.strip()
    return login or None


def has_push_access(repo_path: Path, upstream_repo: str) -> bool:
    """True if the current run can already push to upstream_repo directly
    (same-repo CI run, owner, or a collaborator with WRITE/MAINTAIN/ADMIN) —
    in which case forking is both unnecessary and impossible (GitHub doesn't
    support forking a repo into an account that already owns it). Checks
    is_same_repo first (cheap, reliable, no gh API call) before falling back
    to viewerPermission — the latter reflects collaborator ACL, not what an
    ephemeral CI token can actually do (see is_same_repo's docstring).
    Non-same-repo case found by actually trying to test --execute against a
    disposable repo the user owns: a genuinely third-party repo needs a
    fork, but a repo the user already has write access to (their own
    scratch repo, or one they collaborate on) doesn't, and treating every
    target as fork-required would hard-fail exactly the case a live test
    needs."""
    if is_same_repo(repo_path, upstream_repo):
        return True
    result = run_gh(["repo", "view", upstream_repo, "--json", "viewerPermission"])
    if result.returncode != 0:
        return False
    return '"viewerPermission":"WRITE"' in result.stdout or \
        '"viewerPermission":"MAINTAIN"' in result.stdout or \
        '"viewerPermission":"ADMIN"' in result.stdout


def ensure_fork(repo_path: Path, upstream_repo: str) -> tuple[bool, str]:
    """Returns (ok, push_target_owner_or_error). If the current run already
    has push access to upstream_repo (including the same-repo CI case),
    skips forking entirely and pushes directly to it — forking would fail
    outright in that case. Otherwise, gh repo fork is itself idempotent —
    safe to call whether or not a fork already exists."""
    if has_push_access(repo_path, upstream_repo):
        return True, upstream_repo.split("/")[0]

    login = get_authenticated_login()
    if not login:
        return False, "could not determine authenticated gh user"

    result = run_gh(["repo", "fork", upstream_repo, "--clone=false"], timeout=60)
    if result.returncode != 0 and "already exists" not in (result.stderr + result.stdout).lower():
        return False, (result.stderr or result.stdout).strip()
    return True, login


def stage_paths(repo_path: Path, paths: list[str]) -> tuple[bool, str]:
    """Stage exactly `paths` — never `git add -A`.

    `-A` stages whatever is in the working tree at the moment it runs, which
    is not the same set the caller inspected and approved. The gap matters in
    two ways. It is wider than the verified set: the only content gate here
    is verify_additive_only, which rejects deletions and renames but says
    nothing about untracked files, so a stray `.env`, a credentials file, or
    scratch output sitting in the clone was swept into the commit and then
    force-pushed to a repository this plugin does not own. And it is a moving
    set: anything written to the tree between the status call and the add —
    by a concurrent process, an editor, a build — was picked up too.

    Passing the explicit list closes both. What `--dry-run` printed is
    exactly what gets committed, and nothing else can join it in between.

    Paths are sent in batches because a large change set can otherwise
    exceed the platform's argument-length limit.
    """
    if not paths:
        return False, "nothing to stage"
    batch_size = 200
    for start in range(0, len(paths), batch_size):
        batch = paths[start:start + batch_size]
        result = run_git(repo_path, ["add", "--"] + batch)
        if result.returncode != 0:
            return False, result.stderr.strip()
    return True, ""


def create_branch_commit_push(repo_path: Path, branch: str, commit_message: str, fork_owner: str, repo_name: str, paths: list[str]) -> tuple[bool, str]:
    checkout = run_git(repo_path, ["checkout", "-B", branch])
    if checkout.returncode != 0:
        return False, checkout.stderr.strip()

    staged_ok, stage_error = stage_paths(repo_path, paths)
    if not staged_ok:
        return False, stage_error

    commit = run_git(repo_path, ["commit", "-m", commit_message])
    if commit.returncode != 0:
        return False, commit.stderr.strip()

    # A force push of some kind is genuinely required: branch_name_for is
    # deterministic specifically so re-running finds and resets the same
    # branch rather than piling up new ones (see its own docstring), and
    # `checkout -B` above always rebuilds it fresh from the current base. A
    # plain push only works on the branch's first-ever push — any second run
    # (a genuinely different fix, or a retry after a downstream step like PR
    # creation failed last time, which still leaves the branch pushed) is a
    # guaranteed non-fast-forward. Found live: a run that got past pushing
    # but then failed at `gh pr create` (a since-fixed repo permission gap)
    # left exactly that state, and the next run's plain push rejected as
    # non-fast-forward — except the real error never surfaced, because it
    # silently fell through to the SSH fallback below instead (fixed by only
    # trying that fallback when we're not already pushing to the same repo,
    # since retrying the exact same push over SSH can't succeed either, and
    # its unrelated "Permission denied (publickey)" was masking the actual
    # failure).
    #
    # But --force is the wrong force. It overwrites the remote branch
    # whatever is on it, including work this run has never seen: a
    # same-named branch someone else opened, or commits a collaborator
    # pushed on top. With push access to the upstream repo — which
    # ensure_fork deliberately detects and uses — that discards someone
    # else's commits from a repository this plugin does not own.
    # --force-with-lease overwrites only if the remote is still where this
    # run last observed it, so the reset-my-own-branch case keeps working and
    # the clobber-somebody-else's-work case fails loudly instead.
    #
    # The fetch establishes that observation. Without it the lease has no
    # baseline to compare against and a legitimate re-push is rejected as
    # stale; it is best-effort because a branch that does not exist on the
    # remote yet makes the fetch fail, and that case is a normal first push.
    def push_to(remote: str) -> subprocess.CompletedProcess:
        run_git(repo_path, ["fetch", remote, branch])
        return run_git(repo_path, ["push", "--force-with-lease", "--set-upstream", remote, branch])

    push = push_to("origin")
    if push.returncode != 0 and not is_same_repo(repo_path, f"{fork_owner}/{repo_name}"):
        # origin is the upstream repo itself (read-only for us) rather than
        # the fork — retry against the fork's URL explicitly rather than
        # assuming "origin" is always right.
        push = push_to(f"git@github.com:{fork_owner}/{repo_name}.git")
        if push.returncode != 0:
            return False, _push_error(push)
    elif push.returncode != 0:
        return False, _push_error(push)
    return True, ""


def _push_error(push: subprocess.CompletedProcess) -> str:
    """Make a refused lease legible rather than looking like a transient error."""
    stderr = push.stderr.strip()
    if "stale info" in stderr or "fetch first" in stderr or "non-fast-forward" in stderr:
        return (
            f"{stderr}\n"
            "The remote branch has moved since this run last saw it, so the push was refused "
            "rather than overwriting commits this run did not create. Inspect the branch before "
            "retrying; if the remote content really is disposable, delete the branch explicitly."
        )
    return stderr


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


def read_pr_body_file(raw_path: str, repo_path: Path) -> str:
    """Read the PR body from a file, contained and size-capped.

    The path arrives from the orchestrator and its contents get published to
    a repository this plugin does not own, so it is neither trusted nor
    unbounded. Two limits:

    Containment — the resolved path must sit inside the clone being
    contributed to or inside the current working directory. Without that,
    `--pr-body-file ~/.ssh/id_rsa` or `--pr-body-file /etc/passwd` reads an
    arbitrary file and posts it publicly, which is a plausible way for a
    path built from audit output to go wrong, and an obvious one for a
    malicious PR body template to be aimed. Symlinks are resolved before the
    check, so a link inside the clone cannot point out of it.

    Size — capped at MAX_PR_BODY_BYTES. Pointing this at a log file or a
    binary shouldn't turn into an enormous API request.

    Raises ValueError with a message meant for the operator.
    """
    path = Path(raw_path).resolve()
    if not path.is_file():
        raise ValueError(f"--pr-body-file is not a readable file: {path}")

    roots = [repo_path.resolve(), Path.cwd().resolve()]
    if not any(path == root or root in path.parents for root in roots):
        raise ValueError(
            f"--pr-body-file must live inside the clone ({roots[0]}) or the current directory "
            f"({roots[1]}); refusing to read {path} and publish it to a repository this plugin "
            "does not own."
        )

    size = path.stat().st_size
    if size > MAX_PR_BODY_BYTES:
        raise ValueError(
            f"--pr-body-file is {size} bytes; the maximum is {MAX_PR_BODY_BYTES} "
            "(GitHub rejects PR bodies above that anyway)."
        )

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"--pr-body-file is not valid UTF-8 text: {e}")


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
    direct_push = has_push_access(repo_path, args.upstream_repo)
    login = get_authenticated_login()
    fork_owner = (args.upstream_repo.split("/")[0] if direct_push else login) or "<unknown>"

    existing_pr = find_existing_pr(args.upstream_repo, fork_owner, branch, direct_push) if (direct_push or login) else None
    if existing_pr:
        print(f"Idempotent no-op: a PR already exists for {args.skill_name} against {args.upstream_repo}.", file=sys.stderr)
        print(existing_pr)
        return 0

    diff_summary = get_diff_summary(repo_path)
    base_branch = get_default_branch(repo_path)
    pr_title = args.pr_title or f"Additive fixes for {args.skill_name} (via SkillArtisan audit)"
    if args.pr_body_file:
        try:
            pr_body = read_pr_body_file(args.pr_body_file, repo_path)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
    else:
        pr_body = DEFAULT_PR_BODY_TEMPLATE

    if args.dry_run:
        if direct_push:
            print(f"[dry-run] Already have push access to {args.upstream_repo} — would push directly, no fork needed", file=sys.stderr)
        else:
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
    fork_ok, fork_result = ensure_fork(repo_path, args.upstream_repo)
    if not fork_ok:
        print(f"Error: fork failed — {fork_result}", file=sys.stderr)
        return 12
    fork_owner = fork_result

    commit_message = args.commit_message or f"Additive fixes for {args.skill_name} (via SkillArtisan audit)"
    # Exactly the paths verified above and printed by --dry-run; see stage_paths.
    push_ok, push_error = create_branch_commit_push(
        repo_path, branch, commit_message, fork_owner, repo_name, [path for _, path in changes]
    )
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
