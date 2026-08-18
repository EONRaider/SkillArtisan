#!/usr/bin/env python3
"""Build the Best-in-Market Scorecard's reporting table from Phase 4-6 results.

One row per arm: checklist compliance %, trigger-accuracy (should-trigger and
should-not-trigger, reported separately per the master spec), task-success
delta (blank until Phase 5's task-success half is scored — this only
consumes what axis2_trigger_scorer.py produces today), security-clean rate,
and cost (tokens/time, from run_authoring.py's tracking).

Usage:
    python report.py [--harness-dir DIR] [--json] [--markdown]

Exit codes: 0 success, 2 missing input data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ARMS = ["skill-creator", "daymade-fork", "skillforge", "creating-skills"]


def load_json(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.is_file() else None


def build_report(harness_dir: Path) -> dict:
    axis1 = load_json(harness_dir / "axis1-results" / "axis1_summary.json") or []
    axis2 = load_json(harness_dir / "axis2-results" / "axis2_summary_final.json") or []
    axis3 = load_json(harness_dir / "axis3-results" / "axis3_summary.json") or []

    workspace = harness_dir / "workspace"
    cost_by_arm: dict[str, list[dict]] = {arm: [] for arm in ARMS}
    for status_path in sorted(workspace.glob("*/*/status.json")):
        status = json.loads(status_path.read_text())
        if status.get("state") == "complete" and status.get("arm") in cost_by_arm:
            cost_by_arm[status["arm"]].append(status)

    rows = []
    for arm in ARMS:
        a1 = [r for r in axis1 if r["arm"] == arm]
        a2 = [r for r in axis2 if r["arm"] == arm]
        a3 = [r for r in axis3 if r["arm"] == arm]
        costs = cost_by_arm[arm]

        checklist_pct = (sum(r["pass_rate"] for r in a1) / len(a1) * 100) if a1 else None
        trig = (sum(r["should_trigger"] for r in a2) / len(a2) * 100) if a2 else None
        no_trig = (sum(r["should_not_trigger"] for r in a2) / len(a2) * 100) if a2 else None
        sec_clean = (sum(1 for r in a3 if r["clean"]) / len(a3) * 100) if a3 else None
        avg_tokens = (sum(c["total_tokens"] for c in costs) / len(costs)) if costs else None
        avg_ms = (sum(c["duration_ms"] for c in costs) / len(costs)) if costs else None

        rows.append({
            "arm": arm,
            "n_skills_scored": {"axis1": len(a1), "axis2": len(a2), "axis3": len(a3)},
            "checklist_compliance_pct": round(checklist_pct, 1) if checklist_pct is not None else None,
            "trigger_should_trigger_pct": round(trig, 1) if trig is not None else None,
            "trigger_should_not_trigger_pct": round(no_trig, 1) if no_trig is not None else None,
            "task_success_delta": None,  # not yet scored — see Phase 5 status
            "security_clean_rate_pct": round(sec_clean, 1) if sec_clean is not None else None,
            "avg_tokens_per_run": round(avg_tokens) if avg_tokens is not None else None,
            "avg_duration_s": round(avg_ms / 1000, 1) if avg_ms is not None else None,
        })

    return {
        "scope": "PILOT (3 of 16 corpus skills) — not the full Best-in-Market Scorecard",
        "rows": rows,
    }


def render_markdown(report: dict) -> str:
    lines = [f"**Scope: {report['scope']}**", "", "| Arm | Checklist % | Trigger (should) | Trigger (should-not) | Task-success Δ | Security-clean % | Avg tokens | Avg time |", "|---|---|---|---|---|---|---|---|"]
    for r in report["rows"]:
        def fmt(v, suffix=""):
            return f"{v}{suffix}" if v is not None else "—"
        lines.append(
            f"| {r['arm']} | {fmt(r['checklist_compliance_pct'], '%')} | "
            f"{fmt(r['trigger_should_trigger_pct'], '%')} | {fmt(r['trigger_should_not_trigger_pct'], '%')} | "
            f"{fmt(r['task_success_delta'])} | {fmt(r['security_clean_rate_pct'], '%')} | "
            f"{fmt(r['avg_tokens_per_run'])} | {fmt(r['avg_duration_s'], 's')} |"
        )
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--harness-dir", default=str(Path(__file__).resolve().parent))
    p.add_argument("--json", action="store_true")
    p.add_argument("--markdown", action="store_true")
    args = p.parse_args()

    harness_dir = Path(args.harness_dir)
    report = build_report(harness_dir)

    if args.json:
        print(json.dumps(report, indent=2))
    elif args.markdown:
        print(render_markdown(report))
    else:
        print(render_markdown(report))
        print(f"\n(--json for structured output)")


if __name__ == "__main__":
    main()
