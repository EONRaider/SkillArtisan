#!/usr/bin/env python3
"""Aggregate with/without-skill eval runs into benchmark.json + benchmark.md,
with named trial-count presets and CI pass-rate gating.

Ported from skill-creator's scripts/aggregate_benchmark.py (row 15) with no
loss of capability, plus two additions (row 35, prior art: skillgrade):
named --preset trial counts and a --ci/--threshold gate for release pipelines.

This script does NOT spawn the with-skill/without-skill subagent runs itself
— that orchestration (parallel Task-tool runs from a clean context each time)
is the main SKILL.md's job, since it requires the Task tool, which a
standalone script can't invoke. This script aggregates whatever grading.json
files that orchestration already produced.

Usage:
    python scripts/eval_loop.py aggregate <benchmark_dir> [--skill-name X] [--skill-path P]
    python scripts/eval_loop.py aggregate <benchmark_dir> --ci --threshold 0.8
    python scripts/eval_loop.py presets

Directory layout expected (workspace layout from the eval loop):
    <benchmark_dir>/
    └── eval-N/
        ├── with_skill/
        │   ├── run-1/grading.json
        │   └── run-2/grading.json
        └── without_skill/
            ├── run-1/grading.json
            └── run-2/grading.json

Exit codes: 0 success (or --ci threshold met), 1 threshold not met (--ci only),
2 no runs found, 4 unexpected error.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from _common import TRIAL_PRESETS, calculate_stats


def load_run_results(benchmark_dir: Path) -> dict:
    """Load grading.json files from every run directory in benchmark_dir.

    Returns a dict keyed by configuration name (e.g. "with_skill" /
    "without_skill", or "new_skill" / "old_skill" for audit-mode runs).
    """
    runs_dir = benchmark_dir / "runs"
    if runs_dir.exists():
        search_dir = runs_dir
    elif list(benchmark_dir.glob("eval-*")):
        search_dir = benchmark_dir
    else:
        print(f"No eval directories found in {benchmark_dir} or {benchmark_dir / 'runs'}", file=sys.stderr)
        return {}

    results: dict[str, list] = {}

    for eval_idx, eval_dir in enumerate(sorted(search_dir.glob("eval-*"))):
        metadata_path = eval_dir / "eval_metadata.json"
        eval_id = eval_idx
        if metadata_path.exists():
            try:
                eval_id = json.loads(metadata_path.read_text()).get("eval_id", eval_idx)
            except (json.JSONDecodeError, OSError):
                pass
        else:
            try:
                eval_id = int(eval_dir.name.split("-")[1])
            except (ValueError, IndexError):
                pass

        for config_dir in sorted(eval_dir.iterdir()):
            if not config_dir.is_dir() or not list(config_dir.glob("run-*")):
                continue
            config = config_dir.name
            results.setdefault(config, [])

            for run_dir in sorted(config_dir.glob("run-*")):
                try:
                    run_number = int(run_dir.name.split("-")[1])
                except (ValueError, IndexError):
                    run_number = 0
                grading_file = run_dir / "grading.json"
                if not grading_file.exists():
                    print(f"Warning: grading.json not found in {run_dir}", file=sys.stderr)
                    continue
                try:
                    grading = json.loads(grading_file.read_text())
                except json.JSONDecodeError as e:
                    print(f"Warning: invalid JSON in {grading_file}: {e}", file=sys.stderr)
                    continue

                summary = grading.get("summary", {})
                result = {
                    "eval_id": eval_id,
                    "run_number": run_number,
                    "pass_rate": summary.get("pass_rate", 0.0),
                    "passed": summary.get("passed", 0),
                    "failed": summary.get("failed", 0),
                    "total": summary.get("total", 0),
                }

                timing = grading.get("timing", {})
                result["time_seconds"] = timing.get("total_duration_seconds", 0.0)
                timing_file = run_dir / "timing.json"
                if result["time_seconds"] == 0.0 and timing_file.exists():
                    try:
                        timing_data = json.loads(timing_file.read_text())
                        result["time_seconds"] = timing_data.get("total_duration_seconds", 0.0)
                        result["tokens"] = timing_data.get("total_tokens", 0)
                    except json.JSONDecodeError:
                        pass

                metrics = grading.get("execution_metrics", {})
                result["tool_calls"] = metrics.get("total_tool_calls", 0)
                if not result.get("tokens"):
                    result["tokens"] = metrics.get("output_chars", 0)
                result["errors"] = metrics.get("errors_encountered", 0)

                expectations = grading.get("expectations", [])
                for exp in expectations:
                    if "text" not in exp or "passed" not in exp:
                        print(f"Warning: expectation in {grading_file} missing text/passed/evidence: {exp}", file=sys.stderr)
                result["expectations"] = expectations

                notes_summary = grading.get("user_notes_summary", {})
                result["notes"] = (
                    notes_summary.get("uncertainties", [])
                    + notes_summary.get("needs_review", [])
                    + notes_summary.get("workarounds", [])
                )

                results[config].append(result)

    return results


def aggregate_results(results: dict) -> dict:
    run_summary = {}
    configs = list(results.keys())

    for config in configs:
        runs = results.get(config, [])
        if not runs:
            run_summary[config] = {
                "pass_rate": {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0},
                "time_seconds": {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0},
                "tokens": {"mean": 0, "stddev": 0, "min": 0, "max": 0},
            }
            continue
        run_summary[config] = {
            "pass_rate": calculate_stats([r["pass_rate"] for r in runs]),
            "time_seconds": calculate_stats([r["time_seconds"] for r in runs]),
            "tokens": calculate_stats([r.get("tokens", 0) for r in runs]),
        }

    primary = run_summary.get(configs[0], {}) if configs else {}
    baseline = run_summary.get(configs[1], {}) if len(configs) >= 2 else {}

    delta_pass_rate = primary.get("pass_rate", {}).get("mean", 0) - baseline.get("pass_rate", {}).get("mean", 0)
    delta_time = primary.get("time_seconds", {}).get("mean", 0) - baseline.get("time_seconds", {}).get("mean", 0)
    delta_tokens = primary.get("tokens", {}).get("mean", 0) - baseline.get("tokens", {}).get("mean", 0)

    run_summary["delta"] = {
        "pass_rate": f"{delta_pass_rate:+.2f}",
        "time_seconds": f"{delta_time:+.1f}",
        "tokens": f"{delta_tokens:+.0f}",
    }
    return run_summary


def generate_benchmark(benchmark_dir: Path, skill_name: str = "", skill_path: str = "", preset: str | None = None) -> dict:
    results = load_run_results(benchmark_dir)
    run_summary = aggregate_results(results)

    runs = []
    for config, config_results in results.items():
        for result in config_results:
            runs.append({
                "eval_id": result["eval_id"],
                "configuration": config,
                "run_number": result["run_number"],
                "result": {
                    "pass_rate": result["pass_rate"],
                    "passed": result["passed"],
                    "failed": result["failed"],
                    "total": result["total"],
                    "time_seconds": result["time_seconds"],
                    "tokens": result.get("tokens", 0),
                    "tool_calls": result.get("tool_calls", 0),
                    "errors": result.get("errors", 0),
                },
                "expectations": result["expectations"],
                "notes": result["notes"],
            })

    eval_ids = sorted({r["eval_id"] for config_results in results.values() for r in config_results})
    runs_per_configuration = TRIAL_PRESETS.get(preset, 3) if preset else 3

    return {
        "metadata": {
            "skill_name": skill_name or "<skill-name>",
            "skill_path": skill_path or "<path/to/skill>",
            "executor_model": "<model-name>",
            "analyzer_model": "<model-name>",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "evals_run": eval_ids,
            "runs_per_configuration": runs_per_configuration,
            "preset": preset,
        },
        "runs": runs,
        "run_summary": run_summary,
        "notes": [],
    }


def generate_markdown(benchmark: dict) -> str:
    metadata = benchmark["metadata"]
    run_summary = benchmark["run_summary"]
    configs = [k for k in run_summary if k != "delta"]
    config_a = configs[0] if configs else "config_a"
    config_b = configs[1] if len(configs) >= 2 else "config_b"
    label_a, label_b = config_a.replace("_", " ").title(), config_b.replace("_", " ").title()

    lines = [
        f"# Skill Benchmark: {metadata['skill_name']}",
        "",
        f"**Model**: {metadata['executor_model']}",
        f"**Date**: {metadata['timestamp']}",
        f"**Evals**: {', '.join(map(str, metadata['evals_run']))} ({metadata['runs_per_configuration']} runs each per configuration"
        + (f", preset={metadata['preset']}" if metadata.get("preset") else "") + ")",
        "",
        "## Summary",
        "",
        f"| Metric | {label_a} | {label_b} | Delta |",
        "|--------|------------|---------------|-------|",
    ]

    a, b, delta = run_summary.get(config_a, {}), run_summary.get(config_b, {}), run_summary.get("delta", {})
    a_pr, b_pr = a.get("pass_rate", {}), b.get("pass_rate", {})
    lines.append(f"| Pass Rate | {a_pr.get('mean', 0)*100:.0f}% ± {a_pr.get('stddev', 0)*100:.0f}% | {b_pr.get('mean', 0)*100:.0f}% ± {b_pr.get('stddev', 0)*100:.0f}% | {delta.get('pass_rate', '—')} |")
    a_t, b_t = a.get("time_seconds", {}), b.get("time_seconds", {})
    lines.append(f"| Time | {a_t.get('mean', 0):.1f}s ± {a_t.get('stddev', 0):.1f}s | {b_t.get('mean', 0):.1f}s ± {b_t.get('stddev', 0):.1f}s | {delta.get('time_seconds', '—')}s |")
    a_tok, b_tok = a.get("tokens", {}), b.get("tokens", {})
    lines.append(f"| Tokens | {a_tok.get('mean', 0):.0f} ± {a_tok.get('stddev', 0):.0f} | {b_tok.get('mean', 0):.0f} ± {b_tok.get('stddev', 0):.0f} | {delta.get('tokens', '—')} |")

    if benchmark.get("notes"):
        lines += ["", "## Notes", ""] + [f"- {n}" for n in benchmark["notes"]]
    return "\n".join(lines)


def cmd_aggregate(args: argparse.Namespace) -> int:
    benchmark_dir = Path(args.benchmark_dir)
    if not benchmark_dir.exists():
        print(f"Directory not found: {benchmark_dir}", file=sys.stderr)
        return 4

    benchmark = generate_benchmark(benchmark_dir, args.skill_name, args.skill_path, args.preset)
    if not benchmark["runs"]:
        print(f"No runs found under {benchmark_dir}", file=sys.stderr)
        return 2

    output_json = Path(args.output) if args.output else benchmark_dir / "benchmark.json"
    output_json.write_text(json.dumps(benchmark, indent=2))
    output_json.with_suffix(".md").write_text(generate_markdown(benchmark))
    print(f"Generated: {output_json}")
    print(f"Generated: {output_json.with_suffix('.md')}")

    run_summary = benchmark["run_summary"]
    configs = [k for k in run_summary if k != "delta"]
    print("\nSummary:")
    primary_pass_rate = None
    for config in configs:
        pr = run_summary[config]["pass_rate"]["mean"]
        print(f"  {config.replace('_', ' ').title()}: {pr*100:.1f}% pass rate")
        if config == "with_skill" or (primary_pass_rate is None and config != "without_skill"):
            primary_pass_rate = pr
    print(f"  Delta: {run_summary.get('delta', {}).get('pass_rate', '—')}")

    if args.ci:
        if primary_pass_rate is None:
            print(f"\nCI: no with_skill/primary configuration found — cannot evaluate threshold", file=sys.stderr)
            return 4
        if primary_pass_rate < args.threshold:
            print(f"\nCI: FAIL — pass rate {primary_pass_rate:.2f} below threshold {args.threshold:.2f}", file=sys.stderr)
            return 1
        print(f"\nCI: PASS — pass rate {primary_pass_rate:.2f} meets threshold {args.threshold:.2f}")

    return 0


def cmd_presets(_args: argparse.Namespace) -> int:
    print("Named trial-count presets (use with the eval orchestration in SKILL.md,")
    print("not this script directly — this script only aggregates results):\n")
    for name, count in TRIAL_PRESETS.items():
        print(f"  --preset {name:<10} {count:>3} runs per configuration")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate eval runs into benchmark.json/.md, with CI gating")
    sub = parser.add_subparsers(dest="command", required=True)

    p_agg = sub.add_parser("aggregate", help="Aggregate grading.json files into benchmark.json/.md")
    p_agg.add_argument("benchmark_dir", help="Path to the benchmark/workspace iteration directory")
    p_agg.add_argument("--skill-name", default="", help="Name of the skill being benchmarked")
    p_agg.add_argument("--skill-path", default="", help="Path to the skill being benchmarked")
    p_agg.add_argument("--preset", choices=list(TRIAL_PRESETS), default=None, help="Named trial-count preset used for this run (recorded in metadata)")
    p_agg.add_argument("--output", "-o", default=None, help="Output path for benchmark.json (default: <benchmark_dir>/benchmark.json)")
    p_agg.add_argument("--ci", action="store_true", help="Exit non-zero if the primary configuration's pass rate is below --threshold")
    p_agg.add_argument("--threshold", type=float, default=0.8, help="Pass-rate threshold for --ci (default: 0.8)")
    p_agg.set_defaults(func=cmd_aggregate)

    p_presets = sub.add_parser("presets", help="List named trial-count presets")
    p_presets.set_defaults(func=cmd_presets)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
