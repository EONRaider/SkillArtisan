#!/usr/bin/env python3
"""Cross-corpus aggregation for the real-world audit pilot.

Built for scaling this pilot's methodology past hand-eyeballing: the
35-skill mattpocock run (benchmark/audit-pilot/RESULTS.md) was small enough
to read every audit report myself and manually notice which checklist items
were boilerplate (100% FAIL regardless of skill quality) versus real
signal. That doesn't scale to hundreds of skills across multiple source
repos. This script does the counting/triage mechanically so a human (or an
LLM doing the grading pass) only has to deep-read the skills flagged as
actually interesting.

What it does NOT do: grade whether a finding is a true or false positive.
That step is inherently a judgment call requiring a read of the actual
skill source — see README.md's Methodology and the "avoid circularity"
principle (grading must not be derived from audit.py's own reasoning about
itself). This script only narrows *which* skills need that human read, and
surfaces checklist items whose FAIL/PASS rate suggests they're not
discriminating between good and bad skills at all (the "boilerplate FAIL"
pattern found in the mattpocock run: evals-present,
security-scan-marker-current, lifecycle-classified all FAILed 35/35 times).

Usage:
    python aggregate_findings.py <source-dir> [<source-dir> ...] [--label NAME=PATH ...]
    python aggregate_findings.py <source-dir> --json out.json
    python aggregate_findings.py <source-dir> --boilerplate-threshold 0.9

Each <source-dir> is searched for skills the same way `audit.py bulk` does
(_common.find_skill_dirs) — pass one directory per source repo/corpus so
the per-source breakdown means something (e.g. one for mattpocock-skills,
one for daymade/claude-code-skills, etc.). Exit codes: 0 always (this is a
report, not a gate, same convention as audit.py/dedup_search.py) unless a
given path doesn't exist (2).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import audit  # noqa: E402
from _common import find_skill_dirs  # noqa: E402

# Established from the mattpocock-skills 35-skill pilot (RESULTS.md) — these
# fire on effectively every third-party skill regardless of quality, since
# they check for SkillArtisan-specific artifacts (its own evals/evals.json
# schema, its own packaging tamper marker, its own lifecycle-classification
# convention) no skill authored outside this pipeline will ever have. A
# skill's *other* findings are what's worth a human read; these three (plus
# the naming-convention WARN, which is a soft recommendation, not an error)
# are known noise for a third-party audit until row 31/32's third-party mode
# ships (see CHANGELOG's [2.4.6] "Deferred, not forgotten").
KNOWN_BOILERPLATE_IDS = {
    "evals-present",
    "security-scan-marker-current",
    "lifecycle-classified",
    "gerund-naming",
}


def audit_source(label: str, root: Path, timelessness: int | None, lifecycle: str | None) -> list[dict]:
    skill_dirs = find_skill_dirs([root])
    reports = []
    for skill_dir in skill_dirs:
        try:
            report = audit.audit_skill(skill_dir, timelessness, lifecycle)
        except (ValueError, OSError) as e:
            report = {"skill_name": skill_dir.name, "skill_path": str(skill_dir), "error": str(e)}
        report["source_label"] = label
        reports.append(report)
    return reports


def aggregate(all_reports: list[dict], boilerplate_threshold: float) -> dict:
    item_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    decision_counts: dict[str, int] = defaultdict(int)
    review_queue: list[dict] = []
    errored: list[dict] = []

    for r in all_reports:
        if "error" in r:
            errored.append(r)
            continue
        decision_counts[r["decision"]["decision"]] += 1
        interesting = []
        for item in r["items"]:
            item_counts[item["id"]][item["status"]] += 1
            if item["status"] in ("FAIL", "WARN") and item["id"] not in KNOWN_BOILERPLATE_IDS:
                interesting.append(item)
        if interesting:
            review_queue.append({
                "skill_name": r["skill_name"],
                "skill_path": r["skill_path"],
                "source_label": r.get("source_label", ""),
                "findings": [{"id": i["id"], "status": i["status"], "detail": i["detail"]} for i in interesting],
            })

    checklist_summary = {}
    for item_id, counts in item_counts.items():
        total = sum(counts.values())
        dominant_status, dominant_count = max(counts.items(), key=lambda kv: kv[1])
        rate = dominant_count / total if total else 0.0
        checklist_summary[item_id] = {
            "counts": dict(counts),
            "total": total,
            "dominant_status": dominant_status,
            "dominant_rate": round(rate, 3),
            "likely_boilerplate": rate >= boilerplate_threshold and item_id not in KNOWN_BOILERPLATE_IDS,
        }

    return {
        "total_skills": len([r for r in all_reports if "error" not in r]),
        "errored_skills": errored,
        "decision_counts": dict(decision_counts),
        "checklist_summary": checklist_summary,
        "review_queue": review_queue,
        "review_queue_size": len(review_queue),
    }


def print_summary(agg: dict, boilerplate_threshold: float) -> None:
    print(f"Audited {agg['total_skills']} skill(s), {len(agg['errored_skills'])} error(s)\n")
    print("Decision distribution:")
    for decision, count in sorted(agg["decision_counts"].items()):
        print(f"  {decision:<20} {count}")

    print("\nChecklist items whose dominant status covers "
          f">= {boilerplate_threshold*100:.0f}% of skills (candidates for a boilerplate/scope-mismatch check,\n"
          "beyond the already-known ones baked into KNOWN_BOILERPLATE_IDS):")
    newly_flagged = {k: v for k, v in agg["checklist_summary"].items() if v["likely_boilerplate"]}
    if newly_flagged:
        for item_id, v in sorted(newly_flagged.items(), key=lambda kv: -kv[1]["dominant_rate"]):
            print(f"  {item_id:<35} {v['dominant_status']:>6} {v['dominant_rate']*100:.0f}% ({v['total']} skills)")
    else:
        print("  none — no new boilerplate-shaped items beyond the ones already known")

    print(f"\nReview queue ({agg['review_queue_size']} skill(s) with a non-boilerplate FAIL/WARN — "
          "read these directly, don't trust the report alone):")
    for entry in agg["review_queue"]:
        print(f"  [{entry['source_label']}] {entry['skill_name']} ({entry['skill_path']})")
        for f in entry["findings"]:
            print(f"      [{f['status']:>4}] {f['id']} — {f['detail']}")

    if agg["errored_skills"]:
        print("\nErrors:")
        for e in agg["errored_skills"]:
            print(f"  {e['skill_name']}: {e['error']}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("source_dirs", nargs="+", help="One directory per source corpus/repo to audit and aggregate")
    p.add_argument("--label", action="append", default=[], metavar="NAME=PATH",
                    help="Explicit label for a source dir (default: the directory's own basename)")
    p.add_argument("--timelessness", type=int, default=None, metavar="0-10")
    p.add_argument("--lifecycle", choices=["capability-uplift", "encoded-preference"], default=None)
    p.add_argument("--boilerplate-threshold", type=float, default=0.95,
                    help="Dominant-status rate above which a checklist item is flagged as likely boilerplate (default 0.95)")
    p.add_argument("--json", metavar="FILE", default=None, help="Write full structured output to FILE as JSON")
    args = p.parse_args()

    label_overrides = {}
    for entry in args.label:
        if "=" not in entry:
            print(f"--label must be NAME=PATH, got: {entry}", file=sys.stderr)
            sys.exit(2)
        name, path = entry.split("=", 1)
        label_overrides[str(Path(path).resolve())] = name

    all_reports = []
    for source_dir in args.source_dirs:
        root = Path(source_dir).resolve()
        if not root.is_dir():
            print(f"Error: not a directory: {root}", file=sys.stderr)
            sys.exit(2)
        label = label_overrides.get(str(root), root.name)
        reports = audit_source(label, root, args.timelessness, args.lifecycle)
        print(f"[{label}] {len(reports)} skill(s) found under {root}", file=sys.stderr)
        all_reports.extend(reports)

    agg = aggregate(all_reports, args.boilerplate_threshold)

    if args.json:
        Path(args.json).write_text(json.dumps({"reports": all_reports, "aggregate": agg}, indent=2))
        print(f"Wrote full JSON to {args.json}", file=sys.stderr)

    print_summary(agg, args.boilerplate_threshold)


if __name__ == "__main__":
    main()
