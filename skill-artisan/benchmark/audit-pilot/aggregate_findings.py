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

    # Chunked mode, for a large single source (hundreds of skills) — audits
    # only skill-dirs [start, end) of the sorted discovery list, so a crash
    # or interruption only costs one chunk's worth of re-work, not the whole
    # corpus, and each chunk's results are safely on disk before the next
    # chunk starts:
    python aggregate_findings.py <source-dir> --start 0 --end 100 --json chunk-00.json
    python aggregate_findings.py <source-dir> --start 100 --end 200 --json chunk-01.json
    ...
    # Then combine every chunk's output into one final aggregate/review-queue:
    python aggregate_findings.py --merge chunk-*.json --json combined.json

Each <source-dir> is searched for skills the same way `audit.py bulk` does
(_common.find_skill_dirs) — pass one directory per source repo/corpus so
the per-source breakdown means something (e.g. one for mattpocock-skills,
one for daymade/claude-code-skills, etc.). A single skill that raises any
exception (not just the two originally anticipated) is caught and recorded
as an error entry rather than crashing the whole run — found the hard way
in Phase 3, where an uncaught AttributeError on one skill's evals.json shape
would otherwise have taken down the entire aggregation. Exit codes: 0 always
(this is a report, not a gate, same convention as audit.py/dedup_search.py)
unless a given path doesn't exist (2).
"""

from __future__ import annotations

import argparse
import hashlib
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


def dedup_by_content(skill_dirs: list[Path], label: str) -> list[Path]:
    """Drop any skill directory whose SKILL.md is byte-identical to one
    already kept (first occurrence wins, in `find_skill_dirs`'s own sorted
    order — deterministic regardless of which duplicate happens to be
    "canonical"). `find_skill_dirs` deliberately doesn't do this itself (a
    content judgment, not a structural one) — needed here because
    alirezarezvani/claude-skills packages some skills twice: once in a flat
    per-category collection, again as a fully self-contained mini-plugin.
    Auditing both would silently double-count 12 of that repo's skills
    without changing a single finding — same result, wasted effort, and a
    review-queue count that overstates real coverage."""
    seen_hashes: dict[str, Path] = {}
    kept = []
    skipped = 0
    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        try:
            digest = hashlib.sha256(skill_md.read_bytes()).hexdigest()
        except OSError:
            kept.append(skill_dir)
            continue
        if digest in seen_hashes:
            skipped += 1
            continue
        seen_hashes[digest] = skill_dir
        kept.append(skill_dir)
    if skipped:
        print(f"[{label}] skipped {skipped} exact-content duplicate(s) of an already-kept skill", file=sys.stderr)
    return kept


def audit_source(
    label: str,
    root: Path,
    timelessness: int | None,
    lifecycle: str | None,
    start: int = 0,
    end: int | None = None,
) -> list[dict]:
    skill_dirs = dedup_by_content(find_skill_dirs([root]), label)
    total_found = len(skill_dirs)
    skill_dirs = skill_dirs[start:end]
    if start or end is not None:
        print(f"[{label}] chunk [{start}:{end if end is not None else total_found}] "
              f"of {total_found} discovered skill(s)", file=sys.stderr)
    reports = []
    for skill_dir in skill_dirs:
        try:
            report = audit.audit_skill(skill_dir, timelessness, lifecycle)
        except Exception as e:  # noqa: BLE001 — a single skill's crash must never sink the whole run (Phase 3's Bug #3)
            report = {"skill_name": skill_dir.name, "skill_path": str(skill_dir),
                      "error": f"{type(e).__name__}: {e}"}
        report["source_label"] = label
        reports.append(report)
    return reports


def load_reports_from_json(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    return data["reports"]


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
    p.add_argument("source_dirs", nargs="*", help="One directory per source corpus/repo to audit and aggregate")
    p.add_argument("--label", action="append", default=[], metavar="NAME=PATH",
                    help="Explicit label for a source dir (default: the directory's own basename)")
    p.add_argument("--timelessness", type=int, default=None, metavar="0-10")
    p.add_argument("--lifecycle", choices=["capability-uplift", "encoded-preference"], default=None)
    p.add_argument("--boilerplate-threshold", type=float, default=0.95,
                    help="Dominant-status rate above which a checklist item is flagged as likely boilerplate (default 0.95)")
    p.add_argument("--json", metavar="FILE", default=None, help="Write full structured output to FILE as JSON")
    p.add_argument("--start", type=int, default=0,
                    help="Chunked mode: audit only skill-dirs starting at this 0-based index (of the sorted discovery list)")
    p.add_argument("--end", type=int, default=None,
                    help="Chunked mode: audit only skill-dirs before this 0-based index (exclusive)")
    p.add_argument("--merge", nargs="+", metavar="CHUNK.json", default=None,
                    help="Skip auditing entirely; load and combine previously-written chunk JSON files instead")
    args = p.parse_args()

    if args.merge:
        all_reports = []
        for chunk_path in args.merge:
            reports = load_reports_from_json(Path(chunk_path))
            print(f"[merge] {len(reports)} report(s) loaded from {chunk_path}", file=sys.stderr)
            all_reports.extend(reports)
        agg = aggregate(all_reports, args.boilerplate_threshold)
        if args.json:
            Path(args.json).write_text(json.dumps({"reports": all_reports, "aggregate": agg}, indent=2))
            print(f"Wrote merged JSON to {args.json}", file=sys.stderr)
        print_summary(agg, args.boilerplate_threshold)
        return

    if not args.source_dirs:
        print("Error: at least one source-dir is required (unless using --merge)", file=sys.stderr)
        sys.exit(2)
    if len(args.source_dirs) > 1 and (args.start or args.end is not None):
        print("Error: --start/--end only make sense with a single source-dir (chunking one large corpus)", file=sys.stderr)
        sys.exit(2)

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
        reports = audit_source(label, root, args.timelessness, args.lifecycle, args.start, args.end)
        print(f"[{label}] {len(reports)} skill(s) audited under {root}", file=sys.stderr)
        all_reports.extend(reports)

    agg = aggregate(all_reports, args.boilerplate_threshold)

    if args.json:
        Path(args.json).write_text(json.dumps({"reports": all_reports, "aggregate": agg}, indent=2))
        print(f"Wrote full JSON to {args.json}", file=sys.stderr)

    print_summary(agg, args.boilerplate_threshold)


if __name__ == "__main__":
    main()
