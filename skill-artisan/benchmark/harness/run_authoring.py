#!/usr/bin/env python3
"""Manage the workspace layout for the Best-in-Market Scorecard's authoring runs.

Does NOT spawn the authoring subagents itself — same division of labor as
scripts/eval_loop.py: that orchestration (parallel Task-tool runs, one per
arm x corpus-skill pair) is the orchestrating chat session's job, since a
standalone script can't invoke the Task tool. This script creates the
per-run directory a subagent should write its output into, and reports
status across the whole workspace afterward.

Directory layout:
    <workspace>/<corpus-skill>/<arm>/
        seed.md          # copy of corpus/<corpus-skill>/seed.md, the subagent's input
        prompt.md         # the exact prompt given to the authoring subagent
        output/           # the subagent writes the resulting skill directory here
        status.json       # {"state": "pending|running|complete|failed", "started_at",
                           #  "completed_at", "total_tokens", "duration_ms"}

Usage:
    python run_authoring.py init <corpus-skill> <arm> [--workspace DIR]
    python run_authoring.py init-all [--workspace DIR] [--corpus-skills a,b,c]
    python run_authoring.py mark-complete <corpus-skill> <arm> [--workspace DIR] \\
        [--total-tokens N] [--duration-ms N]
    python run_authoring.py mark-failed <corpus-skill> <arm> --reason TEXT [--workspace DIR]
    python run_authoring.py status [--workspace DIR]

Exit codes: 0 success, 1 invalid arm/corpus-skill, 2 workspace/run not found,
4 unexpected error.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from arms import ARMS, AUTHORING_ARMS, REPO_ROOT

CORPUS_DIR = REPO_ROOT / "benchmark/corpus"
DEFAULT_WORKSPACE = REPO_ROOT / "benchmark/harness/workspace"

PROMPT_TEMPLATE = """\
You are authoring a Claude Skill. Follow the process documented in this file exactly, \
as if it were your own active skill guiding you:

    {entry_point}

Read that file (and anything it references under its own directory, one level deep, the \
same reference-depth convention it likely documents itself) before starting. Do not \
skip steps the file describes as required.

Your task — the user's request you are authoring a skill in response to:

---
{seed_content}
---

Produce the finished skill as a real directory at:

    {output_dir}

Write every file the process above calls for (SKILL.md at minimum; evals/, references/, \
scripts/ as the process directs) directly into that directory. When you are done, report \
back a short summary of what you produced and any step from the source process you were \
unable to complete (and why) rather than silently skipping it.
"""


def load_corpus_skills() -> list[str]:
    return sorted(p.name for p in CORPUS_DIR.iterdir() if p.is_dir())


def run_dir(workspace: Path, corpus_skill: str, arm: str) -> Path:
    return workspace / corpus_skill / arm


def cmd_init(args: argparse.Namespace) -> int:
    if args.arm not in AUTHORING_ARMS:
        print(f"error: '{args.arm}' is not an authoring arm. Choices: {AUTHORING_ARMS}", file=sys.stderr)
        return 1
    seed_path = CORPUS_DIR / args.corpus_skill / "seed.md"
    if not seed_path.is_file():
        print(f"error: no seed.md for corpus skill '{args.corpus_skill}' at {seed_path}", file=sys.stderr)
        return 1

    rd = run_dir(Path(args.workspace), args.corpus_skill, args.arm)
    (rd / "output").mkdir(parents=True, exist_ok=True)

    seed_content = seed_path.read_text()
    entry_point = ARMS[args.arm]["entry_point"]
    prompt = PROMPT_TEMPLATE.format(
        entry_point=entry_point, seed_content=seed_content, output_dir=rd / "output"
    )
    (rd / "seed.md").write_text(seed_content)
    (rd / "prompt.md").write_text(prompt)
    (rd / "status.json").write_text(json.dumps({
        "state": "pending",
        "corpus_skill": args.corpus_skill,
        "arm": args.arm,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))

    print(str(rd))
    return 0


def cmd_init_all(args: argparse.Namespace) -> int:
    corpus_skills = args.corpus_skills.split(",") if args.corpus_skills else load_corpus_skills()
    count = 0
    for cs in corpus_skills:
        for arm in AUTHORING_ARMS:
            ns = argparse.Namespace(corpus_skill=cs, arm=arm, workspace=args.workspace)
            if cmd_init(ns) == 0:
                count += 1
    print(f"initialized {count} run(s)", file=sys.stderr)
    return 0


def _update_status(workspace: Path, corpus_skill: str, arm: str, **updates) -> int:
    rd = run_dir(workspace, corpus_skill, arm)
    status_path = rd / "status.json"
    if not status_path.is_file():
        print(f"error: no run found at {rd} — did you run 'init' first?", file=sys.stderr)
        return 2
    status = json.loads(status_path.read_text())
    status.update(updates)
    status_path.write_text(json.dumps(status, indent=2))
    return 0


def cmd_mark_complete(args: argparse.Namespace) -> int:
    updates = {
        "state": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    if args.total_tokens is not None:
        updates["total_tokens"] = args.total_tokens
    if args.duration_ms is not None:
        updates["duration_ms"] = args.duration_ms
    return _update_status(Path(args.workspace), args.corpus_skill, args.arm, **updates)


def cmd_mark_failed(args: argparse.Namespace) -> int:
    return _update_status(
        Path(args.workspace), args.corpus_skill, args.arm,
        state="failed", failed_at=datetime.now(timezone.utc).isoformat(), reason=args.reason,
    )


def cmd_status(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    if not workspace.is_dir():
        print(f"error: workspace {workspace} does not exist", file=sys.stderr)
        return 2
    rows = []
    for status_path in sorted(workspace.glob("*/*/status.json")):
        status = json.loads(status_path.read_text())
        rows.append(status)
    by_state: dict[str, int] = {}
    for r in rows:
        by_state[r["state"]] = by_state.get(r["state"], 0) + 1
    print(f"{len(rows)} run(s) tracked in {workspace}")
    for state, n in sorted(by_state.items()):
        print(f"  {state}: {n}")
    for r in rows:
        if r["state"] != "complete":
            print(f"  [{r['state']}] {r['corpus_skill']} / {r['arm']}")
    return 0


def cmd_cost(args: argparse.Namespace) -> int:
    """Sum actual tokens spent so far (exact, from completed runs' recorded
    total_tokens) and project a rough remaining cost from the per-arm
    average of what's completed. Advisory only — this cannot see remaining
    session quota (no tool exposes that), it can only make the *pattern* of
    spend-so-far visible before the next batch of spawns."""
    workspace = Path(args.workspace)
    if not workspace.is_dir():
        print(f"error: workspace {workspace} does not exist", file=sys.stderr)
        return 2

    completed: list[dict] = []
    pending_by_arm: dict[str, int] = {}
    for status_path in sorted(workspace.glob("*/*/status.json")):
        status = json.loads(status_path.read_text())
        if status["state"] == "complete" and "total_tokens" in status:
            completed.append(status)
        elif status["state"] in ("pending", "running"):
            pending_by_arm[status["arm"]] = pending_by_arm.get(status["arm"], 0) + 1

    spent_total = sum(r["total_tokens"] for r in completed)
    print(f"Spent so far (exact, {len(completed)} completed run(s) with recorded tokens): {spent_total:,} tokens")

    if not completed:
        print("No completed runs with token data yet — nothing to average.", file=sys.stderr)
        return 0

    by_arm: dict[str, list[int]] = {}
    for r in completed:
        by_arm.setdefault(r["arm"], []).append(r["total_tokens"])

    print("\nPer-arm average (n completed):")
    for arm, tokens in sorted(by_arm.items()):
        avg = sum(tokens) / len(tokens)
        print(f"  {arm}: {avg:,.0f} avg over {len(tokens)} run(s)  [{min(tokens):,}-{max(tokens):,}]")

    overall_avg = spent_total / len(completed)
    if pending_by_arm:
        print(f"\nProjected cost of {sum(pending_by_arm.values())} pending/running run(s)"
              f" (per-arm average where known, else overall average of {overall_avg:,.0f}):")
        projected_total = 0.0
        for arm, n in sorted(pending_by_arm.items()):
            arm_avg = (sum(by_arm[arm]) / len(by_arm[arm])) if arm in by_arm else overall_avg
            projected = arm_avg * n
            projected_total += projected
            print(f"  {arm}: {n} run(s) x {arm_avg:,.0f} ~= {projected:,.0f}")
        print(f"  TOTAL projected additional: ~{projected_total:,.0f} tokens")
        print(f"  Grand total (spent + projected): ~{spent_total + projected_total:,.0f} tokens")
    else:
        print("\nNo pending/running runs left to project.")

    print(
        "\nNote: this is advisory only. No tool available here reports remaining session\n"
        "quota — the only signal for that is reactive (a spawn fails with a session-limit\n"
        "error that happens to include a reset timestamp). This command makes spend-so-far\n"
        "and rough forecast visible; it cannot tell you whether the next spawn will fit.",
        file=sys.stderr,
    )
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Set up one (corpus-skill, arm) run directory")
    p_init.add_argument("corpus_skill")
    p_init.add_argument("arm", choices=AUTHORING_ARMS)
    p_init.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    p_init.set_defaults(func=cmd_init)

    p_init_all = sub.add_parser("init-all", help="Set up run directories for every (corpus-skill, arm) pair")
    p_init_all.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    p_init_all.add_argument("--corpus-skills", help="Comma-separated subset; default is all 16")
    p_init_all.set_defaults(func=cmd_init_all)

    p_complete = sub.add_parser("mark-complete", help="Mark a run complete after the subagent finishes")
    p_complete.add_argument("corpus_skill")
    p_complete.add_argument("arm", choices=AUTHORING_ARMS)
    p_complete.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    p_complete.add_argument("--total-tokens", type=int)
    p_complete.add_argument("--duration-ms", type=int)
    p_complete.set_defaults(func=cmd_mark_complete)

    p_failed = sub.add_parser("mark-failed", help="Mark a run failed")
    p_failed.add_argument("corpus_skill")
    p_failed.add_argument("arm", choices=AUTHORING_ARMS)
    p_failed.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    p_failed.add_argument("--reason", required=True)
    p_failed.set_defaults(func=cmd_mark_failed)

    p_status = sub.add_parser("status", help="Summarize run states across the workspace")
    p_status.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    p_status.set_defaults(func=cmd_status)

    p_cost = sub.add_parser("cost", help="Exact spend-so-far + rough per-arm projection for remaining runs")
    p_cost.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    p_cost.set_defaults(func=cmd_cost)

    args = p.parse_args()
    try:
        sys.exit(args.func(args))
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(4)


if __name__ == "__main__":
    main()
