#!/usr/bin/env python3
"""Score an authored skill's trigger accuracy against a corpus entry's
trigger-evals.json, for Axis 2 of the Best-in-Market Scorecard.

Pure scoring, no optimization loop — this is description_optimizer.py's
run_eval() called once against whatever description an authoring arm
actually produced, not iterated toward a better one. Reuses that function
directly rather than reimplementing the claude -p trigger-detection
mechanism (registering a uniquely-named synthetic skill, watching the
stream-json output for a Skill/Read tool call against it).

Usage:
    python axis2_trigger_scorer.py <skill-output-dir> <trigger-evals.json> \\
        [--runs-per-query 3] [--num-workers 4] [--timeout 60] [--model MODEL]
        [--json]

Exit codes: 0 success, 1 bad input, 4 unexpected error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from _common import parse_skill_md  # noqa: E402
from description_optimizer import IsolationError, check_isolation, run_eval  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("skill_dir", help="Path to the authored skill directory (must have SKILL.md)")
    p.add_argument("trigger_evals", help="Path to a trigger-evals.json (list of {query, should_trigger})")
    p.add_argument("--runs-per-query", type=int, default=3)
    p.add_argument(
        "--num-workers", type=int, default=4,
        help="Concurrent claude -p launches. Default 4. Before 2.12.0 this defaulted to 1: "
             "every worker shared one project root, so each child saw its siblings' "
             "identically-described candidate copies, and 4 workers measured well below "
             "sequential (0%% vs. 75%% should-trigger once; 10/16 vs. 14/16 after the 2.2.3 "
             "race fix). Each run now gets a private root; re-measured on "
             "debugging-network-issues at 3 runs/query, 4 workers scored 15/16 vs. 16/16 "
             "sequential (45/48 vs. 47/48 correct runs, Fisher p=0.62), zero timeouts in "
             "either arm, about 3x faster. Drop to 1 if timeout warnings appear on a "
             "slower machine.",
    )
    p.add_argument(
        "--timeout", type=int, default=180,
        help="Per-call claude -p timeout in seconds. Default 180 — verified directly that "
             "a plain trigger-check call can take over 2 minutes in this environment; the "
             "60s this script started with silently misreported real triggers as misses "
             "(should-not-trigger queries were unaffected, masking the problem until the "
             "should-trigger numbers were checked directly).",
    )
    p.add_argument("--trigger-threshold", type=float, default=0.5)
    p.add_argument("--model", help="Model ID to pin the claude -p executor to")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of a text summary")
    args = p.parse_args()

    skill_dir = Path(args.skill_dir)
    if not (skill_dir / "SKILL.md").is_file():
        print(f"error: no SKILL.md at {skill_dir}", file=sys.stderr)
        sys.exit(1)

    eval_set = json.loads(Path(args.trigger_evals).read_text())
    if not isinstance(eval_set, list):
        print("error: trigger-evals.json must be a JSON list of {query, should_trigger}", file=sys.stderr)
        sys.exit(1)

    name, description, _ = parse_skill_md(skill_dir)
    if not description:
        print(f"error: {skill_dir}/SKILL.md has no description field", file=sys.stderr)
        sys.exit(1)

    try:
        check_isolation()
    except IsolationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        result = run_eval(
            eval_set=eval_set,
            skill_name=name,
            description=description,
            num_workers=args.num_workers,
            timeout=args.timeout,
            runs_per_query=args.runs_per_query,
            trigger_threshold=args.trigger_threshold,
            model=args.model,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(4)

    should_trigger_results = [r for r in result["results"] if r["should_trigger"]]
    should_not_results = [r for r in result["results"] if not r["should_trigger"]]
    result["summary"]["should_trigger_pass_rate"] = (
        sum(1 for r in should_trigger_results if r["pass"]) / len(should_trigger_results) if should_trigger_results else None
    )
    result["summary"]["should_not_trigger_pass_rate"] = (
        sum(1 for r in should_not_results if r["pass"]) / len(should_not_results) if should_not_results else None
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        s = result["summary"]
        print(f"Skill: {result['skill_name']}")
        print(f"Overall: {s['passed']}/{s['total']} passed")
        st = s["should_trigger_pass_rate"]
        sn = s["should_not_trigger_pass_rate"]
        print(f"  should-trigger pass rate:     {st*100:.1f}%" if st is not None else "  should-trigger: n/a")
        print(f"  should-not-trigger pass rate: {sn*100:.1f}%" if sn is not None else "  should-not-trigger: n/a")
        for r in result["results"]:
            if not r["pass"]:
                print(f"  FAIL [{'should-trigger' if r['should_trigger'] else 'should-not-trigger'}] "
                      f"({r['triggers']}/{r['runs']}): {r['query'][:80]}")


if __name__ == "__main__":
    main()
