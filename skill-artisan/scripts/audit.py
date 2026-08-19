#!/usr/bin/env python3
"""Audit an existing skill (or a whole directory of them) against the Gap
Table's Synthesized Checklist, and recommend upgrade-vs-rebuild.

Row 31, 32; Stage 6. Reuses v1's Stage 1-4 infrastructure rather than
reimplementing it: `validate.py` for frontmatter/naming/path-references,
`security_scan.py` for gitleaks/pattern findings and the tamper marker,
`_common.find_skill_dirs` for bulk-mode discovery. This script does NOT run
the eval engine itself — regression benchmarking (item 4 below) needs the
Task tool to spawn subagents, which a standalone script can't do; that
orchestration is `SKILL.md`'s job (see "Auditing existing skills"), exactly
the same division of labor v1 already uses for the eval engine proper.

What this script CAN verify mechanically vs. what needs a human/LLM read:
most of the Synthesized Checklist's structural items (frontmatter validity,
security-scan cleanliness, evals presence, body-size limits, reference
depth) are checkable from the files alone. A handful of items are
judgment calls no pattern can substitute for — multi-model testing actually
having happened, whether a description's triggering logic is *good* and not
just present, whether the skill's boundary is genuinely one coherent unit of
work. Those are reported as MANUAL, not guessed at or silently skipped —
per the master spec's own instruction: "never a bare binary verdict."

Usage:
    python scripts/audit.py report <skill-path>
    python scripts/audit.py report <skill-path> --timelessness 8 --lifecycle capability-uplift
    python scripts/audit.py report <skill-path> --json
    python scripts/audit.py bulk <skills-dir>
    python scripts/audit.py bulk <skills-dir> --json
    python scripts/audit.py pr-plan <skill-path> --upstream-repo <owner/repo>

Exit codes: 0 report generated (regardless of pass/fail — this is a report,
not a gate, same convention as dedup_search.py), 2 path not found,
4 SKILL.md unreadable/unparseable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pr_execute
import security_scan
import validate
from _common import find_skill_dirs, parse_skill_md

# --- Checklist item registry -------------------------------------------------
# Each check returns (status, detail). Status is one of:
#   PASS   - verified true
#   FAIL   - verified false, a real problem
#   WARN   - a heuristic signal worth a look, not a hard failure
#   MANUAL - script cannot verify this; needs a human or LLM read
# Only PASS/FAIL count toward the pass-rate summary (item 1's requirement:
# "never a bare binary verdict" means the report itself must be itemized,
# not that every item can be force-fit into a binary).

KNOWN_SECTION_KEYWORDS = (
    "decision gate", "frontmatter", "description", "naming", "security",
    "evals", "evaluat", "testing", "packaging", "surface", "degrees of freedom",
    "writing", "reference", "lifecycle", "audit", "compatibility", "install",
    "usage", "coherent", "fork", "inline",
)

HEADING_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
BARE_DIRECTIVE_RE = re.compile(r"\b(MUST|ALWAYS|NEVER)\b")
TIME_SENSITIVE_RE = re.compile(r"\bas of 20\d\d\b|\bcurrently\b|\bcurrent version is\b", re.IGNORECASE)
WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\\\|[A-Za-z]:\\[A-Za-z]")


def get_body(skill_path: Path) -> tuple[str, dict[str, str]]:
    _, _, content = parse_skill_md(skill_path)
    lines = content.split("\n")
    body = content
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                body = "\n".join(lines[i + 1:])
                break
    from _common import parse_frontmatter_raw
    return body, parse_frontmatter_raw(content)


def check_frontmatter_and_paths(skill_path: Path) -> list[dict]:
    result = validate.validate(skill_path)
    items = []
    ref_errors = [e for e in result["errors"] if e.startswith("Missing referenced files")]
    other_errors = [e for e in result["errors"] if not e.startswith("Missing referenced files")]
    items.append({
        "id": "frontmatter-valid",
        "status": "PASS" if not other_errors else "FAIL",
        "detail": "; ".join(other_errors) or "skills-ref + Claude-specific checks pass",
    })
    items.append({
        "id": "path-references-exist",
        "status": "FAIL" if ref_errors else "PASS",
        "detail": "; ".join(ref_errors) or "every relative link resolves",
    })
    gerund_warnings = [w for w in result["warnings"] if "gerund" in w]
    items.append({
        "id": "gerund-naming",
        "status": "WARN" if gerund_warnings else "PASS",
        "detail": "; ".join(gerund_warnings) or "name is gerund-form",
    })
    return items


def is_user_invoked_only(frontmatter: dict[str, str]) -> bool:
    return frontmatter.get("disable-model-invocation", "").strip().lower() == "true"


def check_description_quality(frontmatter: dict[str, str]) -> dict:
    desc = frontmatter.get("description", "")
    if not desc:
        return {"id": "description-pushy-imperative", "status": "FAIL", "detail": "description missing"}
    if is_user_invoked_only(frontmatter):
        status = "PASS" if len(desc) >= 20 else "WARN"
        detail = ("disable-model-invocation: true — pushy/'Use when...' triggering framing doesn't apply; description just needs to accurately state what the skill does"
                  if status == "PASS" else "description too short to be useful even for a plain, non-triggering description")
        return {"id": "description-pushy-imperative", "status": status, "detail": detail}
    if len(desc) < 40:
        return {"id": "description-pushy-imperative", "status": "FAIL",
                "detail": f"description missing or under 40 chars ({len(desc)} chars) — likely fails to trigger reliably"}
    has_use_when = "use when" in desc.lower()
    status = "PASS" if has_use_when and len(desc) >= 100 else "WARN"
    detail = ("has 'Use when...' framing and real length" if status == "PASS"
              else "missing 'Use when...' framing or short — read against references/frontmatter-spec.md's worked example")
    return {"id": "description-pushy-imperative", "status": status, "detail": detail}


def check_body_size(body: str) -> dict:
    lines = body.count("\n") + 1
    approx_tokens = int(len(body.split()) * 1.3)
    if lines <= 500 and approx_tokens <= 5000:
        status = "PASS"
    elif lines <= 1000 and approx_tokens <= 10000:
        status = "WARN"
    else:
        status = "FAIL"
    return {"id": "body-size-limits", "status": status,
            "detail": f"{lines} lines, ~{approx_tokens} tokens (approx — word count x1.3, not a real tokenizer)"}


def check_references_depth_and_toc(skill_path: Path) -> list[dict]:
    ref_dir = skill_path / "references"
    items = []
    if not ref_dir.is_dir():
        return [{"id": "references-one-level-deep", "status": "PASS", "detail": "no references/ directory"},
                {"id": "references-toc-for-long-files", "status": "PASS", "detail": "no references/ directory"}]

    nested_violations = []
    toc_violations = []
    for ref_file in sorted(ref_dir.rglob("*.md")):
        rel_depth = len(ref_file.relative_to(ref_dir).parts)
        if rel_depth > 1:
            nested_violations.append(str(ref_file.relative_to(skill_path)))
        text = ref_file.read_text(errors="replace")
        line_count = text.count("\n") + 1
        if line_count > 100 and "table of contents" not in text.lower():
            toc_violations.append(str(ref_file.relative_to(skill_path)))

    items.append({
        "id": "references-one-level-deep", "status": "FAIL" if nested_violations else "PASS",
        "detail": f"nested reference files: {', '.join(nested_violations)}" if nested_violations else "all references one level deep",
    })
    items.append({
        "id": "references-toc-for-long-files", "status": "FAIL" if toc_violations else "PASS",
        "detail": f"missing TOC (>100 lines): {', '.join(toc_violations)}" if toc_violations else "long reference files have a TOC",
    })
    return items


def check_no_human_docs_in_skill_dir(skill_path: Path) -> dict:
    offenders = [f for f in ("README.md", "CHANGELOG.md") if (skill_path / f).exists()]
    return {"id": "no-human-docs-in-skill-dir", "status": "FAIL" if offenders else "PASS",
            "detail": f"found inside the skill directory: {', '.join(offenders)} (row 34 — belongs at plugin root instead)" if offenders else "clean"}


def check_evals_present(skill_path: Path) -> dict:
    evals_file = skill_path / "evals" / "evals.json"
    if not evals_file.exists():
        return {"id": "evals-present", "status": "FAIL", "detail": "no evals/evals.json"}
    try:
        data = json.loads(evals_file.read_text())
    except json.JSONDecodeError as e:
        return {"id": "evals-present", "status": "FAIL", "detail": f"evals.json invalid JSON: {e}"}
    count = len(data.get("evals", []))
    if count >= 3:
        return {"id": "evals-present", "status": "PASS", "detail": f"{count} eval case(s)"}
    return {"id": "evals-present", "status": "WARN", "detail": f"only {count} eval case(s) — spec recommends starting with >=3"}


def check_security(skill_path: Path) -> list[dict]:
    items = []
    marker_valid, marker_reason = security_scan.verify_marker(skill_path)
    items.append({"id": "security-scan-marker-current", "status": "PASS" if marker_valid else "FAIL", "detail": marker_reason})

    gitleaks_findings, installed, error = security_scan.run_gitleaks(skill_path)
    if not installed:
        items.append({"id": "security-gitleaks-clean", "status": "MANUAL", "detail": "gitleaks not installed on this machine — cannot verify, install it before trusting a green marker"})
    elif error:
        items.append({"id": "security-gitleaks-clean", "status": "MANUAL", "detail": "gitleaks scan errored — rerun manually"})
    else:
        items.append({"id": "security-gitleaks-clean", "status": "FAIL" if gitleaks_findings else "PASS",
                       "detail": f"{len(gitleaks_findings)} finding(s)" if gitleaks_findings else "clean"})

    pattern_findings = security_scan.run_pattern_checks(skill_path)
    high = [f for f in pattern_findings if f["severity"] == "HIGH"]
    medium = [f for f in pattern_findings if f["severity"] == "MEDIUM"]
    if high:
        status, detail = "FAIL", f"{len(high)} HIGH pattern finding(s): {', '.join(sorted({f['check'] for f in high}))}"
    elif medium:
        status, detail = "WARN", f"{len(medium)} MEDIUM (informational) finding(s)"
    else:
        status, detail = "PASS", "no pattern findings"
    items.append({"id": "security-pattern-checks", "status": status, "detail": detail})
    return items


def check_content_hygiene(body: str) -> list[dict]:
    items = []
    time_hits = TIME_SENSITIVE_RE.findall(body)
    items.append({"id": "no-time-sensitive-info", "status": "WARN" if time_hits else "PASS",
                   "detail": f"{len(time_hits)} possible time-sensitive phrase(s) — heuristic, verify by reading" if time_hits else "none found"})
    win_hits = WINDOWS_PATH_RE.findall(body)
    items.append({"id": "forward-slash-paths-only", "status": "FAIL" if win_hits else "PASS",
                   "detail": f"{len(win_hits)} Windows-style path(s) found" if win_hits else "none found"})
    return items


def check_lifecycle_classified(body: str, frontmatter: dict[str, str]) -> dict:
    has_marker = "lifecycle" in body.lower() and "timelessness" in body.lower()
    has_metadata = "lifecycle" in frontmatter.get("metadata", "").lower()
    if has_marker or has_metadata:
        return {"id": "lifecycle-classified", "status": "PASS", "detail": "lifecycle/timelessness classification present (see references/lifecycle.md)"}
    return {"id": "lifecycle-classified", "status": "FAIL", "detail": "no lifecycle classification found — add one per references/lifecycle.md"}


def check_degrees_of_freedom_proxy(body: str) -> dict:
    """Heuristic proxy for "explain the why, don't just say MUST/ALWAYS/NEVER"
    — counts bare all-caps directives. A real judgment of whether each one
    has a nearby explanation needs a human/LLM read; this only flags volume."""
    hits = BARE_DIRECTIVE_RE.findall(body)
    if len(hits) <= 2:
        return {"id": "degrees-of-freedom-writing-style", "status": "PASS", "detail": f"{len(hits)} bare MUST/ALWAYS/NEVER — low, likely explained elsewhere"}
    return {"id": "degrees-of-freedom-writing-style", "status": "WARN",
            "detail": f"{len(hits)} bare MUST/ALWAYS/NEVER directives — heuristic only, read each for an explained why (references/writing-philosophy.md)"}


MANUAL_ONLY_ITEMS = [
    {"id": "coherent-unit-scoping", "status": "MANUAL",
     "detail": "read the skill's one-sentence job description — does it need 'and' to join two unrelated verbs? (references/writing-philosophy.md)"},
    {"id": "multi-model-tested", "status": "MANUAL", "detail": "cannot verify from files alone — confirm a smoke-preset pass exists for Haiku, Sonnet, and Opus"},
    {"id": "description-optimizer-run", "status": "MANUAL", "detail": "cannot verify from files alone — confirm the 20-query/60-40-split optimizer was run, not just a hand-written description"},
    {"id": "inline-vs-fork-decision-correct", "status": "MANUAL",
     "detail": "presence of `context: fork` is checkable, but whether it's the *right* call needs the worked examples in SKILL.md's Decision Gate section"},
]


def run_checklist(skill_path: Path) -> list[dict]:
    body, frontmatter = get_body(skill_path)
    items: list[dict] = []
    items += check_frontmatter_and_paths(skill_path)
    items.append(check_description_quality(frontmatter))
    items.append(check_body_size(body))
    items += check_references_depth_and_toc(skill_path)
    items.append(check_no_human_docs_in_skill_dir(skill_path))
    items.append(check_evals_present(skill_path))
    items += check_security(skill_path)
    items += check_content_hygiene(body)
    items.append(check_lifecycle_classified(body, frontmatter))
    items.append(check_degrees_of_freedom_proxy(body))
    context_value = frontmatter.get("context", "inline (default)")
    items.append({"id": "architecture-declared", "status": "PASS", "detail": f"context: {context_value}"})
    for item in MANUAL_ONLY_ITEMS:
        if item["id"] == "description-optimizer-run" and is_user_invoked_only(frontmatter):
            items.append({"id": "description-optimizer-run", "status": "PASS",
                           "detail": "disable-model-invocation: true — skill is user-invoked only, description-optimizer is not applicable"})
        else:
            items.append(dict(item))
    return items


def summarize(items: list[dict]) -> dict:
    scored = [i for i in items if i["status"] in ("PASS", "FAIL")]
    passed = sum(1 for i in scored if i["status"] == "PASS")
    failed = sum(1 for i in scored if i["status"] == "FAIL")
    warned = sum(1 for i in items if i["status"] == "WARN")
    manual = sum(1 for i in items if i["status"] == "MANUAL")
    total_scored = passed + failed
    return {
        "passed": passed, "failed": failed, "warned": warned, "manual": manual,
        "total_scored": total_scored,
        "pass_rate": round(passed / total_scored, 3) if total_scored else 0.0,
    }


# --- Upgrade-vs-rebuild decision gate ----------------------------------------


def decide_upgrade_vs_rebuild(items: list[dict], timelessness: int | None, lifecycle_category: str | None) -> dict:
    by_id = {i["id"]: i for i in items}
    reasons = []

    desc_item = by_id.get("description-pushy-imperative", {})
    fm_item = by_id.get("frontmatter-valid", {})
    if desc_item.get("status") == "FAIL" and fm_item.get("status") == "FAIL":
        reasons.append("triggering logic is fundamentally broken: both frontmatter validity and description quality fail, not just one structural gap")

    if lifecycle_category == "capability-uplift" and timelessness is not None and timelessness < 7:
        reasons.append(f"obsolete capability-uplift skill: timelessness {timelessness}/10 is under the 7/10 durable bar (references/lifecycle.md)")

    body_item = by_id.get("body-size-limits", {})
    if body_item.get("status") == "FAIL":
        reasons.append("body is more than double the size limit — likely conflicts badly enough with degrees-of-freedom tiering that patching means rewriting most of it (verify by reading, this is a size proxy, not a direct read of the prose)")

    if reasons:
        return {"decision": "rebuild", "reasons": reasons}
    return {"decision": "upgrade-in-place", "reasons": ["failures found are structural (naming, frontmatter details, missing security/evals) — additive fixes, not a rewrite"]}


# --- Institutional-knowledge safeguard ---------------------------------------


def find_unmapped_sections(body: str) -> list[str]:
    headings = HEADING_RE.findall(body)
    unmapped = []
    for h in headings:
        lowered = h.lower()
        if not any(kw in lowered for kw in KNOWN_SECTION_KEYWORDS):
            unmapped.append(h.strip())
    return unmapped


# --- Single-skill report ------------------------------------------------------


def audit_skill(skill_path: Path, timelessness: int | None, lifecycle_category: str | None) -> dict:
    items = run_checklist(skill_path)
    summary = summarize(items)
    decision = decide_upgrade_vs_rebuild(items, timelessness, lifecycle_category)
    body, _ = get_body(skill_path)
    unmapped = find_unmapped_sections(body)
    name, _, _ = parse_skill_md(skill_path)
    return {
        "skill_name": name or skill_path.name,
        "skill_path": str(skill_path),
        "items": items,
        "summary": summary,
        "decision": decision,
        "institutional_knowledge_candidates": unmapped,
    }


def print_report(report: dict) -> None:
    s = report["summary"]
    print(f"Audit: {report['skill_name']} ({report['skill_path']})")
    print(f"Checklist: {s['passed']}/{s['total_scored']} pass ({s['pass_rate']*100:.0f}%), {s['warned']} warning(s), {s['manual']} item(s) need a manual/LLM read\n")
    for i in report["items"]:
        print(f"  [{i['status']:>6}] {i['id']} — {i['detail']}")
    print(f"\nDecision: {report['decision']['decision'].upper()}")
    for r in report["decision"]["reasons"]:
        print(f"  - {r}")
    if report["institutional_knowledge_candidates"]:
        print("\nInstitutional-knowledge safeguard — sections with no obvious checklist counterpart (keep, fold in, or discard? never drop silently):")
        for h in report["institutional_knowledge_candidates"]:
            print(f"  - {h}")
    else:
        print("\nInstitutional-knowledge safeguard: every section heading maps to a known checklist area — nothing flagged for review.")
    print(
        "\nRegression benchmarking is not run by this script (needs the Task tool to spawn subagents). "
        "Before/after: snapshot the skill, run scripts/eval_loop.py aggregate on both, and only accept "
        "changes that don't regress the pre-change baseline — see SKILL.md's \"Auditing existing skills\"."
    )


# --- Bulk mode -----------------------------------------------------------------


def cmd_bulk(args: argparse.Namespace) -> int:
    target = Path(args.skills_dir).resolve()
    if not target.is_dir():
        print(f"Error: not a directory: {target}", file=sys.stderr)
        return 2

    skill_dirs = find_skill_dirs([target])
    if not skill_dirs:
        print(f"No skills found under {target}", file=sys.stderr)
        return 2

    reports = []
    for skill_dir in skill_dirs:
        try:
            reports.append(audit_skill(skill_dir, args.timelessness, args.lifecycle))
        except (ValueError, OSError) as e:
            reports.append({"skill_name": skill_dir.name, "skill_path": str(skill_dir), "error": str(e)})

    if args.json:
        print(json.dumps({"skills_dir": str(target), "reports": reports}, indent=2))
        return 0

    print(f"Bulk audit: {len(reports)} skill(s) under {target}\n")
    for r in reports:
        if "error" in r:
            print(f"  {r['skill_name']}: ERROR — {r['error']}")
            continue
        s = r["summary"]
        print(f"  {r['skill_name']:<30} {s['passed']}/{s['total_scored']} pass ({s['pass_rate']*100:.0f}%)  "
              f"{s['warned']} warn  {s['manual']} manual  -> {r['decision']['decision']}")
    print("\nRun `audit.py report <skill-path>` on any individual skill above for the full itemized breakdown.")
    return 0


# --- pr-plan (row 32, optional stretch) ---------------------------------------


def cmd_pr_plan(args: argparse.Namespace) -> int:
    skill_path = Path(args.skill_path).resolve()
    if not skill_path.is_dir():
        print(f"Error: not a directory: {skill_path}", file=sys.stderr)
        return 2
    name, _, _ = parse_skill_md(skill_path)
    report = audit_skill(skill_path, None, None)
    print(f"Contribution plan for {name or skill_path.name} -> {args.upstream_repo}\n")
    print("This command itself is a PLAN only — it does not fork, commit, or open a PR. Real")
    print("execution exists separately (`audit.py pr-execute` / `pr_execute.py`), gated behind an")
    print("--execute flag the orchestrator only passes after explicit user confirmation in chat,")
    print("every time, not just once per skill — never a script-side auto-confirm.\n")
    print("Additive-only-changes principle: never delete or rename anything in the upstream skill's")
    print("directory. Every change below must be a pure addition or an in-place fix to something")
    print("this audit found broken — not a stylistic rewrite of content that already worked.\n")
    print("Proposed changes (from this audit's FAIL items only — WARN/MANUAL items are notes for the")
    print("upstream maintainer to consider, not this plugin's call to make unilaterally):")
    fails = [i for i in report["items"] if i["status"] == "FAIL"]
    if not fails:
        print("  (none — this skill has no FAIL items; there's nothing additive to contribute)")
    for i in fails:
        print(f"  - {i['id']}: {i['detail']}")
    print("\nNext step: present this plan to the user and get explicit confirmation before forking,")
    print("committing, or calling `gh pr create` against the upstream repository.")
    return 0


def cmd_pr_execute(args: argparse.Namespace) -> int:
    """Delegates to pr_execute.py — the real-effects counterpart to
    pr-plan. Kept as a thin wrapper (same pattern as validate/security_scan
    reuse above) so `audit.py` stays the single entry point for every
    audit-related subcommand, while the actual git/gh logic lives in its own
    tiny, separately-runnable module per the scripts/ discipline."""
    return pr_execute.cmd(args)


# --- CLI -----------------------------------------------------------------------


def cmd_report(args: argparse.Namespace) -> int:
    skill_path = Path(args.skill_path).resolve()
    if not skill_path.is_dir():
        print(f"Error: not a directory: {skill_path}", file=sys.stderr)
        return 2
    try:
        report = audit_skill(skill_path, args.timelessness, args.lifecycle)
    except (ValueError, OSError) as e:
        print(f"Error: could not audit {skill_path}: {e}", file=sys.stderr)
        return 4

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit an existing skill (or a directory of skills) against the Synthesized Checklist")
    sub = parser.add_subparsers(dest="command", required=True)

    p_report = sub.add_parser("report", help="Audit a single skill directory")
    p_report.add_argument("skill_path", help="Path to the skill directory")
    p_report.add_argument("--timelessness", type=int, default=None, metavar="0-10",
                           help="Timelessness score (references/lifecycle.md) — supply if known, feeds the upgrade-vs-rebuild decision")
    p_report.add_argument("--lifecycle", choices=["capability-uplift", "encoded-preference"], default=None,
                           help="Lifecycle category (references/lifecycle.md) — supply alongside --timelessness")
    p_report.add_argument("--json", action="store_true", help="Emit structured JSON instead of a text report")
    p_report.set_defaults(func=cmd_report)

    p_bulk = sub.add_parser("bulk", help="Audit every skill found under a directory (row 31)")
    p_bulk.add_argument("skills_dir", help="Directory to search for skills (e.g. ~/.claude/skills/)")
    p_bulk.add_argument("--timelessness", type=int, default=None, metavar="0-10", help="Applied to every skill audited — omit unless every skill genuinely shares one score")
    p_bulk.add_argument("--lifecycle", choices=["capability-uplift", "encoded-preference"], default=None)
    p_bulk.add_argument("--json", action="store_true", help="Emit structured JSON instead of a text report")
    p_bulk.set_defaults(func=cmd_bulk)

    p_pr = sub.add_parser("pr-plan", help="Print an additive-only contribution plan for a third-party skill (row 32 — plan only, this subcommand never executes)")
    p_pr.add_argument("skill_path", help="Path to the (third-party) skill directory")
    p_pr.add_argument("--upstream-repo", required=True, metavar="owner/repo", help="Upstream repository this skill came from")
    p_pr.set_defaults(func=cmd_pr_plan)

    p_pr_exec = sub.add_parser("pr-execute", help="Execute a contribution (branch/commit/push/PR) against a third-party skill repo — real side effects, see pr_execute.py")
    p_pr_exec.add_argument("clone_path", help="Local git clone (of a fork of) the upstream repo, with the fix already applied as uncommitted changes")
    p_pr_exec.add_argument("--upstream-repo", required=True, metavar="owner/repo", help="Upstream repository to open the PR against")
    p_pr_exec.add_argument("--skill-name", required=True, help="Name of the skill being fixed")
    p_pr_exec.add_argument("--pr-title", default=None, help="PR title (default: generated from --skill-name)")
    p_pr_exec.add_argument("--pr-body-file", default=None, help="Path to a file with the PR body (default: a generic additive-only-changes template)")
    p_pr_exec.add_argument("--commit-message", default=None, help="Commit message (default: generated from --skill-name)")
    pr_exec_mode = p_pr_exec.add_mutually_exclusive_group(required=True)
    pr_exec_mode.add_argument("--dry-run", action="store_true", help="Preview the branch/diff/PR that would be created — no git or gh mutation")
    pr_exec_mode.add_argument("--execute", action="store_true", help="Actually fork/branch/commit/push/open the PR. Only pass this after a separate, explicit human confirmation obtained in chat.")
    p_pr_exec.set_defaults(func=cmd_pr_execute)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
