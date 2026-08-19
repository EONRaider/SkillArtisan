#!/usr/bin/env python3
"""GitHub Action entrypoint: audit every skill found in a target repo, and —
whenever an Anthropic API key is supplied — author additive fixes for the
skills that fail the checklist and open a PR per skill via pr_execute.py.

Reuses v1/v2 infrastructure rather than reimplementing it: `audit.audit_skill`
for the mechanical checklist (see audit.py's own docstring — nothing here
duplicates that), `_common.find_skill_dirs` for discovery, `pr_execute` for
the git/gh mechanics of opening a PR. This script's own job is just the glue:
render a report, and — only when an API key is present — call Claude to
author fix content and hand it to pr_execute.

Behavior is gated on secret presence, not a mode flag: the caller either
passes an API key (via --anthropic-api-key or $ANTHROPIC_API_KEY) or doesn't.
No key -> report only, nothing written, nothing pushed. Key present -> same
report, plus a PR per skill with FAIL items (skipped skills are reported, not
silently dropped).

Usage:
    python scripts/gha_audit.py --skills-path . --repo-path .
    python scripts/gha_audit.py --skills-path . --repo-path . \
        --anthropic-api-key sk-ant-... --upstream-repo owner/repo

Exit codes: 0 report generated (regardless of pass/fail, or of individual
fix-PR failures — those are reported per-skill, not fatal to the run),
2 skills-path not found.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import anthropic_client
import audit
import pr_execute
from _common import find_skill_dirs

DEFAULT_MAX_SKILLS = 10

FENCE_RE = re.compile(r"^```[a-zA-Z]*\n|\n```$")


# --- Report rendering ---------------------------------------------------------


def render_markdown_summary(reports: list[dict], pr_results: dict[str, str]) -> str:
    lines = ["# SkillArtisan audit report", ""]
    if not reports:
        lines.append("No skills found.")
        return "\n".join(lines)

    lines.append(f"Audited {len(reports)} skill(s).")
    lines.append("")
    lines.append("| Skill | Pass rate | Warnings | Manual | Decision | Fix PR |")
    lines.append("|---|---|---|---|---|---|")
    for r in reports:
        if "error" in r:
            lines.append(f"| {r['skill_name']} | — | — | — | ERROR: {r['error']} | — |")
            continue
        s = r["summary"]
        pr_cell = pr_results.get(r["skill_name"], "—")
        lines.append(
            f"| {r['skill_name']} | {s['passed']}/{s['total_scored']} ({s['pass_rate']*100:.0f}%) | "
            f"{s['warned']} | {s['manual']} | {r['decision']['decision']} | {pr_cell} |"
        )
    return "\n".join(lines)


# --- LLM fix authoring ---------------------------------------------------------


def build_fix_prompt(skill_name: str, skill_md_text: str, fail_items: list[dict]) -> str:
    findings = "\n".join(f"- {i['id']}: {i['detail']}" for i in fail_items)
    return f"""You are proposing an additive-only fix for a Claude Agent Skill named \
"{skill_name}" that failed the following SkillArtisan audit checklist items:

{findings}

Current SKILL.md content:
---
{skill_md_text}
---

Propose a fix that addresses ONLY the failed items above. Rules:
- Additive only: you may add new files or change file contents in place, but
  must never suggest deleting or renaming anything.
- Don't rewrite unrelated content — the smallest change that fixes the listed
  items is correct, not a stylistic pass over the rest of the file.
- Every file path is relative to the skill's own directory (e.g. "SKILL.md",
  "evals/evals.json").

Respond with ONLY a single JSON object, no markdown code fences, no prose
before or after, in exactly this shape:
{{"summary": "<one paragraph: what changed and why>", "files": [{{"path": "<relative path>", "content": "<full new file content>"}}]}}
"""


def parse_fix_response(text: str) -> dict:
    """Parse and validate the LLM's JSON response. Raises ValueError with a
    clear message on anything malformed — callers skip-and-warn rather than
    crash the whole run on one bad response."""
    stripped = text.strip()
    stripped = FENCE_RE.sub("", stripped).strip()
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ValueError(f"response is not valid JSON: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("response JSON is not an object")
    if "summary" not in data or not isinstance(data["summary"], str):
        raise ValueError("response missing string 'summary'")
    if "files" not in data or not isinstance(data["files"], list) or not data["files"]:
        raise ValueError("response missing non-empty 'files' list")
    for entry in data["files"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or not isinstance(entry.get("content"), str):
            raise ValueError(f"malformed file entry: {entry!r}")
        if entry["path"].startswith("/") or ".." in Path(entry["path"]).parts:
            raise ValueError(f"unsafe file path (must stay inside the skill directory): {entry['path']!r}")
    return data


def apply_fix_files(skill_path: Path, files: list[dict]) -> None:
    for entry in files:
        target = (skill_path / entry["path"]).resolve()
        if skill_path.resolve() not in target.parents and target != skill_path.resolve():
            raise ValueError(f"refusing to write outside the skill directory: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(entry["content"])


# --- Orchestration -------------------------------------------------------------


def process_fix_pr(
    report: dict,
    repo_path: Path,
    upstream_repo: str,
    api_key: str,
    model: str,
    base_ref: str,
) -> str:
    """Author a fix for one skill and open a PR. Returns a short status
    string for the summary table; never raises — failures are caught and
    reported per-skill so one bad skill doesn't stop the others."""
    skill_path = Path(report["skill_path"])
    skill_name = report["skill_name"]
    fail_items = [i for i in report["items"] if i["status"] == "FAIL"]
    if not fail_items:
        return "no FAIL items"

    try:
        skill_md_text = (skill_path / "SKILL.md").read_text()
        prompt = build_fix_prompt(skill_name, skill_md_text, fail_items)
        response_text = anthropic_client.create_message(prompt, api_key=api_key, model=model)
        fix = parse_fix_response(response_text)
        apply_fix_files(skill_path, fix["files"])
    except (ValueError, OSError, anthropic_client.AnthropicAPIError) as e:
        pr_execute.run_git(repo_path, ["checkout", "-f", base_ref])
        return f"skipped — fix authoring failed: {e}"

    body = f"{fix['summary']}\n\n---\nGenerated by SkillArtisan's audit GitHub Action from these findings:\n\n" + \
        "\n".join(f"- {i['id']}: {i['detail']}" for i in fail_items)
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(body)
        body_file = f.name

    args = argparse.Namespace(
        clone_path=str(repo_path),
        upstream_repo=upstream_repo,
        skill_name=skill_name,
        pr_title=f"SkillArtisan audit: fix {skill_name}",
        pr_body_file=body_file,
        commit_message=f"Additive fixes for {skill_name} (via SkillArtisan audit)",
        dry_run=False,
        execute=True,
    )
    exit_code = pr_execute.cmd(args)
    pr_execute.run_git(repo_path, ["checkout", "-f", base_ref])
    return "PR opened" if exit_code == 0 else f"pr_execute failed (exit {exit_code})"


def get_base_ref(repo_path: Path) -> str:
    result = pr_execute.run_git(repo_path, ["rev-parse", "HEAD"])
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit every skill in a repo; open fix PRs when an API key is supplied")
    parser.add_argument("--skills-path", default=".", help="Directory to search for skills")
    parser.add_argument("--repo-path", default=".", help="Git repository root (for committing/pushing fix PRs)")
    parser.add_argument("--upstream-repo", default=os.environ.get("GITHUB_REPOSITORY"), metavar="owner/repo")
    parser.add_argument("--anthropic-api-key", default=os.environ.get("ANTHROPIC_API_KEY", ""))
    parser.add_argument("--model", default=anthropic_client.DEFAULT_MODEL)
    parser.add_argument("--max-skills", type=int, default=DEFAULT_MAX_SKILLS, help="Cap on how many skills get fix-PR treatment per run")
    parser.add_argument("--summary-file", default=os.environ.get("GITHUB_STEP_SUMMARY"))
    args = parser.parse_args()

    skills_path = Path(args.skills_path).resolve()
    if not skills_path.is_dir():
        print(f"Error: not a directory: {skills_path}", file=sys.stderr)
        return 2

    skill_dirs = find_skill_dirs([skills_path])
    reports = []
    for skill_dir in skill_dirs:
        try:
            reports.append(audit.audit_skill(skill_dir, None, None))
        except (ValueError, OSError) as e:
            reports.append({"skill_name": skill_dir.name, "skill_path": str(skill_dir), "error": str(e)})

    pr_results: dict[str, str] = {}
    if args.anthropic_api_key:
        repo_path = Path(args.repo_path).resolve()
        base_ref = get_base_ref(repo_path)
        fixable = [r for r in reports if "error" not in r and any(i["status"] == "FAIL" for i in r["items"])]
        skipped = fixable[args.max_skills:]
        for report in fixable[: args.max_skills]:
            pr_results[report["skill_name"]] = process_fix_pr(
                report, repo_path, args.upstream_repo, args.anthropic_api_key, args.model, base_ref,
            )
        for report in skipped:
            pr_results[report["skill_name"]] = f"skipped — over --max-skills ({args.max_skills})"

    summary = render_markdown_summary(reports, pr_results)
    print(summary)
    if args.summary_file:
        with open(args.summary_file, "a") as f:
            f.write(summary + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
