#!/usr/bin/env python3
"""Optimize a skill's frontmatter description for trigger accuracy.

Ported from skill-creator's scripts/run_eval.py + run_loop.py +
improve_description.py + generate_report.py (row 15), consolidated into one
CLI per the scripts/ discipline (row 34) rather than four cooperating files.
No loss of capability: same 60/40 train/validation split (shuffled once,
fixed across iterations), same 3x-runs-per-query trigger rate against a 0.5
threshold, same up-to-5-iteration loop, same selection-by-validation-score
(not last-iteration) logic, same live-refreshing HTML report.

Claude Code only — this script shells out to `claude -p`, which doesn't
exist on Claude.ai or Cowork. Skip description optimization entirely on
those surfaces (see creating-skills/references/surface-matrix.md); there is
no fallback path, since the CLI is the only way to run a query against the
model that's actually powering the current session.

Usage:
    python scripts/description_optimizer.py run \\
        --eval-set trigger_evals.json --skill-path ./my-skill \\
        --model <model-id-powering-this-session>

    python scripts/description_optimizer.py report results.json -o report.html
"""

from __future__ import annotations

import argparse
import html
import json
import os
import random
import re
import select
import shutil
import subprocess
import sys
import tempfile
import time
import webbrowser
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from _common import parse_skill_md

# ---------------------------------------------------------------------------
# Project root discovery (mirrors how Claude Code finds .claude/)
# ---------------------------------------------------------------------------


def find_project_root() -> Path:
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
    return current


# ---------------------------------------------------------------------------
# Trigger evaluation: does a query actually cause the skill to load?
# ---------------------------------------------------------------------------


def run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    project_root: str,
    model: str | None = None,
    start_delay: float = 0.0,
) -> bool:
    """Run one query against `claude -p` and report whether the skill triggered.

    Registers a uniquely-named skill directory at .claude/skills/<name>/SKILL.md
    so it shows up in Claude's available_skills list under a name we can grep
    for in the tool-use stream, then cleans it up unconditionally.

    Deliberately NOT .claude/commands/<name>.md: that registers as a slash
    command, not as a skill, so it never appears in available_skills and the
    Skill tool never fires on it — verified directly against a live Claude
    Code session while porting this script (skill-creator's shipped version
    uses .claude/commands/, which no longer round-trips; .claude/skills/ is
    the path Claude Tag's discovery convention already documents, and it's
    the one that actually surfaces here).
    """
    if start_delay > 0:
        # Kept as defense in depth alongside the atomic publish below —
        # concurrent claude -p startups scanning .claude/skills/ still
        # benefit from not all landing in the same instant.
        time.sleep(start_delay)

    unique_id = os.urandom(4).hex()
    clean_name = f"{skill_name}-skill-{unique_id}"
    skills_root = Path(project_root) / ".claude" / "skills"
    project_skills_dir = skills_root / clean_name
    skill_file = project_skills_dir / "SKILL.md"

    try:
        # Build the entry under a hidden staging name first, then publish it
        # with a single os.rename() into its real name. mkdir() followed by
        # a separate write_text() (the previous approach) leaves a window
        # where a concurrent claude -p process's startup skill-discovery
        # scan of this same shared .claude/skills/ directory can observe the
        # directory with no SKILL.md yet, or a partially-flushed one — a real
        # race, confirmed via a dedicated filesystem-only stress test (old
        # approach: ~99% of concurrent scans caught a broken entry; this
        # approach: 0%), even with the start_delay stagger above, since that
        # only reduces the odds of landing in the window rather than closing
        # it. Note this fix on its own did NOT resolve the 0%-at-4-workers-
        # vs-75%-at-1-worker collapse documented in axis2_trigger_scorer.py —
        # a live post-fix re-check still showed that drop, traced to raw
        # resource contention (concurrent claude -p processes starving each
        # other of CPU/network/API throughput on one machine) rather than
        # this race. Worth fixing regardless — os.rename() within the same
        # filesystem is atomic, so any directory listing of .claude/skills/
        # during this call only ever sees the complete final entry or
        # nothing — never a partial one. skills_root and its parents must
        # exist before the rename target's parent does, so create those (but
        # not the final dir).
        skills_root.mkdir(parents=True, exist_ok=True)
        staging_dir = skills_root / f".{clean_name}.staging-{os.getpid()}"
        staging_dir.mkdir(parents=True, exist_ok=True)
        indented_desc = "\n  ".join(skill_description.split("\n"))
        (staging_dir / "SKILL.md").write_text(
            f"---\nname: {clean_name}\ndescription: |\n  {indented_desc}\n---\n\n"
            f"# {clean_name}\n\nThis skill handles: {skill_description}\n"
        )
        os.rename(staging_dir, project_skills_dir)

        cmd = ["claude", "-p", query, "--output-format", "stream-json", "--verbose", "--include-partial-messages"]
        if model:
            cmd.extend(["--model", model])

        # Drop CLAUDECODE so nesting `claude -p` inside a Claude Code session
        # doesn't trip the interactive-terminal guard (safe for subprocess use).
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        # stdin=DEVNULL: without it, worker processes can inherit a stdin
        # that neither closes nor produces data, so `claude -p` stalls for
        # several seconds probing for piped input before proceeding. Found
        # while verifying this port end-to-end; the original skill-creator
        # script leaves stdin unset and eats that stall on every call.
        process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=project_root, env=env)

        triggered = False
        start_time = time.time()
        buffer = ""
        pending_tool_name = None
        accumulated_json = ""

        try:
            while time.time() - start_time < timeout:
                if process.poll() is not None:
                    remaining = process.stdout.read()
                    if remaining:
                        buffer += remaining.decode("utf-8", errors="replace")
                    break

                ready, _, _ = select.select([process.stdout], [], [], 1.0)
                if not ready:
                    continue
                chunk = os.read(process.stdout.fileno(), 8192)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if event.get("type") == "stream_event":
                        # A turn's FIRST tool call is not necessarily the
                        # diagnostic one — the model may look around (Bash,
                        # Read a data file, etc.) before invoking the skill
                        # under test, and multi-turn responses can have
                        # several assistant turns before that happens. Bailing
                        # out on the first non-Skill/Read tool_use (the
                        # previous version of this loop did exactly that)
                        # silently misreports "did not trigger" for any
                        # response that doesn't call the skill as its literal
                        # first action — confirmed directly: a manual
                        # `claude -p` run against this exact mechanism showed
                        # the model call Bash first, Skill second, on a query
                        # that should obviously trigger. Keep watching across
                        # every tool call and every turn instead, and only
                        # conclude "did not trigger" when the process's own
                        # `result` event (or the process exiting/timing out)
                        # says the turn is actually over.
                        se = event.get("event", {})
                        se_type = se.get("type", "")
                        if se_type == "content_block_start":
                            cb = se.get("content_block", {})
                            if cb.get("type") == "tool_use":
                                tool_name = cb.get("name", "")
                                if tool_name in ("Skill", "Read"):
                                    pending_tool_name = tool_name
                                    accumulated_json = ""
                                else:
                                    pending_tool_name = None
                        elif se_type == "content_block_delta" and pending_tool_name:
                            delta = se.get("delta", {})
                            if delta.get("type") == "input_json_delta":
                                accumulated_json += delta.get("partial_json", "")
                                if clean_name in accumulated_json:
                                    triggered = True
                        elif se_type in ("content_block_stop", "message_stop"):
                            if pending_tool_name and clean_name in accumulated_json:
                                triggered = True
                            pending_tool_name = None
                    elif event.get("type") == "assistant":
                        # Same fix as above: scan every tool_use in this
                        # message rather than returning on the first one, and
                        # don't return from the function at all here — later
                        # assistant turns in the same response may still call
                        # the skill under test.
                        message = event.get("message", {})
                        for content_item in message.get("content", []):
                            if content_item.get("type") != "tool_use":
                                continue
                            tool_name = content_item.get("name", "")
                            tool_input = content_item.get("input", {})
                            if tool_name == "Skill" and clean_name in tool_input.get("skill", ""):
                                triggered = True
                            elif tool_name == "Read" and clean_name in tool_input.get("file_path", ""):
                                triggered = True
                    elif event.get("type") == "result":
                        return triggered
        finally:
            if process.poll() is None:
                # Loop exited via the timeout condition, not a clean `result`
                # event or process exit — this run never got a real answer,
                # and silently returning `triggered` (False, almost always,
                # since triggering the skill tends to take longer than
                # answering "no") misreports "did not trigger" for a call
                # that simply didn't finish in time. Confirmed directly: a
                # manual claude -p run against this exact mechanism took over
                # two minutes on a plain query with the default 60s timeout
                # this script shipped with — every should-trigger query in an
                # affected run reads as a false negative, while should-not-
                # trigger queries are unaffected (their correct answer is
                # also `False`, so a timeout and a genuine non-trigger are
                # indistinguishable for them). Surface this on stderr since
                # the return type here is a plain bool used elsewhere
                # (run_eval, run_loop) and changing it would ripple out;
                # a caller aggregating many runs can grep for this to catch
                # a too-short --timeout before trusting the trigger rate.
                print(
                    f"WARNING: run_single_query timed out after {timeout}s before the "
                    f"process finished (query: {query[:60]!r}) — counted as not-triggered, "
                    f"which may be wrong. Consider a longer --timeout.",
                    file=sys.stderr,
                )
                process.kill()
                process.wait()

        return triggered
    finally:
        # Same atomicity concern as the publish above, mirrored for teardown:
        # unlink() then rmdir() are two separate calls, so a concurrent
        # discovery scan can catch the directory between them — SKILL.md
        # already gone, directory still present and still named clean_name.
        # Rename it out of .claude/skills/ first (atomic, and the destination
        # name is unique per call so it can't collide) so any listing of
        # .claude/skills/ during teardown sees either the complete entry or
        # nothing, never a mid-deletion one — then remove the detached copy.
        if project_skills_dir.exists():
            torn_down = skills_root / f".{clean_name}.torndown-{os.getpid()}"
            try:
                os.rename(project_skills_dir, torn_down)
                shutil.rmtree(torn_down, ignore_errors=True)
            except OSError:
                pass  # already gone; leave it rather than risk deleting real content


def _hide_real_skill(project_root: Path, skill_name: str) -> Path | None:
    """If the skill under test is already installed for real at
    .claude/skills/<skill_name>/ in the same project root used for testing,
    move it aside for the duration of the eval and return the path it was
    moved to (None if there was nothing to hide).

    Found while dogfooding this exact script on a real, already-installed
    project skill: the synthetic per-query test copy gets a randomized name
    specifically so it doesn't collide with anything — but if the real skill
    is *also* sitting right there under its natural name with a near-identical
    description, the model tends to reach for the naturally-named real one
    instead of the synthetic candidate. The harness only counts a trigger on
    the synthetic name, so every one of those turns reads as a silent miss —
    trigger rate looks wrong for reasons that have nothing to do with the
    description being tested. This only matters for "improving an existing
    skill" (a brand-new skill has nothing installed yet to collide with).
    """
    real_path = project_root / ".claude" / "skills" / skill_name
    if not real_path.is_dir():
        return None
    hidden_path = real_path.with_name(f"{skill_name}.eval-hidden")
    real_path.rename(hidden_path)
    return hidden_path


def _restore_real_skill(hidden_path: Path | None, skill_name: str) -> None:
    if hidden_path is None or not hidden_path.exists():
        return
    hidden_path.rename(hidden_path.with_name(skill_name))


def run_eval(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    project_root: Path,
    runs_per_query: int = 3,
    trigger_threshold: float = 0.5,
    model: str | None = None,
) -> dict:
    """Run every query runs_per_query times and grade against trigger_threshold."""
    hidden_path = _hide_real_skill(project_root, skill_name)
    try:
        return _run_eval_inner(eval_set, skill_name, description, num_workers, timeout, project_root, runs_per_query, trigger_threshold, model)
    finally:
        _restore_real_skill(hidden_path, skill_name)


def _run_eval_inner(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    project_root: Path,
    runs_per_query: int,
    trigger_threshold: float,
    model: str | None,
) -> dict:
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_info = {}
        task_index = 0
        for item in eval_set:
            for run_idx in range(runs_per_query):
                # Stagger launches within each wave of `num_workers` concurrent
                # tasks (see run_single_query's start_delay docstring note).
                start_delay = (task_index % num_workers) * 0.5
                future = executor.submit(
                    run_single_query, item["query"], skill_name, description, timeout, str(project_root), model, start_delay
                )
                future_to_info[future] = (item, run_idx)
                task_index += 1

        query_triggers: dict[str, list[bool]] = {}
        query_items: dict[str, dict] = {}
        for future in as_completed(future_to_info):
            item, _ = future_to_info[future]
            query = item["query"]
            query_items[query] = item
            query_triggers.setdefault(query, [])
            try:
                query_triggers[query].append(future.result())
            except Exception as e:
                print(f"Warning: query failed: {e}", file=sys.stderr)
                query_triggers[query].append(False)

    results = []
    for query, triggers in query_triggers.items():
        item = query_items[query]
        trigger_rate = sum(triggers) / len(triggers)
        should_trigger = item["should_trigger"]
        did_pass = trigger_rate >= trigger_threshold if should_trigger else trigger_rate < trigger_threshold
        results.append({
            "query": query, "should_trigger": should_trigger, "trigger_rate": trigger_rate,
            "triggers": sum(triggers), "runs": len(triggers), "pass": did_pass,
        })

    passed = sum(1 for r in results if r["pass"])
    return {
        "skill_name": skill_name, "description": description, "results": results,
        "summary": {"total": len(results), "passed": passed, "failed": len(results) - passed},
    }


# ---------------------------------------------------------------------------
# Description improvement via `claude -p`
# ---------------------------------------------------------------------------


def _call_claude(prompt: str, model: str | None, timeout: int = 300) -> str:
    cmd = ["claude", "-p", "--output-format", "text"]
    if model:
        cmd.extend(["--model", model])
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    result = subprocess.run(cmd, input=prompt, capture_output=True, text=True, env=env, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"claude -p exited {result.returncode}\nstderr: {result.stderr}")
    return result.stdout


def improve_description(
    skill_name: str,
    skill_content: str,
    current_description: str,
    eval_results: dict,
    history: list[dict],
    model: str,
    log_dir: Path | None = None,
    iteration: int | None = None,
) -> str:
    failed_triggers = [r for r in eval_results["results"] if r["should_trigger"] and not r["pass"]]
    false_triggers = [r for r in eval_results["results"] if not r["should_trigger"] and not r["pass"]]
    train_score = f"{eval_results['summary']['passed']}/{eval_results['summary']['total']}"

    prompt = f"""You are optimizing a skill description for a Claude Code skill called "{skill_name}". A "skill" has a title and description Claude sees when deciding whether to use it, and a body it reads if it does.

The description appears in Claude's "available_skills" list. Claude decides whether to invoke the skill based solely on the title and this description. Your goal is a description that triggers for relevant queries and doesn't trigger for irrelevant ones.

Current description:
<current_description>
"{current_description}"
</current_description>

Current scores (Train: {train_score}):
<scores_summary>
"""
    if failed_triggers:
        prompt += "FAILED TO TRIGGER (should have triggered but didn't):\n"
        for r in failed_triggers:
            prompt += f'  - "{r["query"]}" (triggered {r["triggers"]}/{r["runs"]} times)\n'
        prompt += "\n"
    if false_triggers:
        prompt += "FALSE TRIGGERS (triggered but shouldn't have):\n"
        for r in false_triggers:
            prompt += f'  - "{r["query"]}" (triggered {r["triggers"]}/{r["runs"]} times)\n'
        prompt += "\n"
    if history:
        prompt += "PREVIOUS ATTEMPTS (do NOT repeat these — try something structurally different):\n\n"
        for h in history:
            train_s = f"{h.get('train_passed', h.get('passed', 0))}/{h.get('train_total', h.get('total', 0))}"
            prompt += f'<attempt train={train_s}>\nDescription: "{h["description"]}"\n'
            if "results" in h:
                prompt += "Train results:\n"
                for r in h["results"]:
                    status = "PASS" if r["pass"] else "FAIL"
                    prompt += f'  [{status}] "{r["query"][:80]}" (triggered {r["triggers"]}/{r["runs"]})\n'
            prompt += "</attempt>\n\n"

    prompt += f"""</scores_summary>

Skill content (for context on what the skill does):
<skill_content>
{skill_content}
</skill_content>

Based on the failures, write a new and improved description more likely to trigger correctly. Generalize from the failures to broader categories of user intent rather than producing an ever-expanding list of specific queries — that overfits, and the description gets injected into every query alongside every other skill's description, so it needs to stay compact.

Keep it under about 100-200 words; there is a hard 1024-character limit (over that gets truncated, so stay comfortably under it).

Tips that work well:
- Imperative voice: "Use this skill for..." rather than "this skill does..."
- Focus on the user's intent, not the skill's implementation details.
- Make it distinctive — it competes with other skills' descriptions for Claude's attention.
- If repeated attempts keep failing, change sentence structure, not just wording.

Respond with only the new description text in <new_description> tags, nothing else."""

    text = _call_claude(prompt, model)
    match = re.search(r"<new_description>(.*?)</new_description>", text, re.DOTALL)
    description = match.group(1).strip().strip('"') if match else text.strip().strip('"')

    transcript = {
        "iteration": iteration, "prompt": prompt, "response": text,
        "parsed_description": description, "char_count": len(description), "over_limit": len(description) > 1024,
    }

    if len(description) > 1024:
        shorten_prompt = (
            f"{prompt}\n\n---\n\nA previous attempt produced this description, which at {len(description)} "
            f"characters is over the 1024-character hard limit:\n\n\"{description}\"\n\n"
            f"Rewrite it to be under 1024 characters while keeping the most important trigger words and intent "
            f"coverage. Respond with only the new description in <new_description> tags."
        )
        shorten_text = _call_claude(shorten_prompt, model)
        match = re.search(r"<new_description>(.*?)</new_description>", shorten_text, re.DOTALL)
        description = match.group(1).strip().strip('"') if match else shorten_text.strip().strip('"')
        transcript["rewrite_description"] = description

    transcript["final_description"] = description
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / f"improve_iter_{iteration or 'unknown'}.json").write_text(json.dumps(transcript, indent=2))

    return description


# ---------------------------------------------------------------------------
# Train/validation split + the iteration loop
# ---------------------------------------------------------------------------


MIN_MEANINGFUL_VAL_PER_CLASS = 5
# improve_description() is deliberately never shown which validation queries
# fail (blinded_history strips every test_-prefixed key) — that's correct
# anti-overfitting design. But the split itself is computed once, with a
# fixed seed, and never rotates. Confirmed directly on a real corpus
# (bilibili-source, 9 should-trigger examples, default holdout=0.4): the
# 3 should-trigger queries that landed in validation failed identically
# across all 5 iterations, completely unmoved by materially different
# description rewrites, because the optimizer had zero visibility into them
# from iteration 1 onward. Below this many examples per class, a single
# query flipping swings the reported validation score by 20+ percentage
# points, and there's no mechanism in this tool to recover if the one-time
# split happens to isolate a hard case — see split_validation_warning().


def split_validation_warning(val_set: list[dict], eval_set_size: int, holdout: float) -> str | None:
    """None if the validation split has enough examples per class to be a
    meaningful generalization check; otherwise a message explaining why
    best_test_score from this run should be treated as low-confidence."""
    n_trigger_val = sum(1 for e in val_set if e["should_trigger"])
    n_no_trigger_val = len(val_set) - n_trigger_val
    thin = [n for n in (n_trigger_val, n_no_trigger_val) if 0 < n < MIN_MEANINGFUL_VAL_PER_CLASS]
    if not thin:
        return None
    worst_swing = 100 / min(thin)
    return (
        f"validation set has only {n_trigger_val} should-trigger and {n_no_trigger_val} "
        f"should-not-trigger example(s) (holdout={holdout} on {eval_set_size} total queries). "
        f"With this few, a single query flipping changes the validation score by "
        f"{worst_swing:.0f}+ percentage points. improve_description() never sees which "
        f"validation queries are failing (by design, to avoid overfitting the description to "
        f"visible examples) and the train/validation split is fixed for the whole run, so a "
        f"query that lands in this small a holdout may be structurally unfixable within this "
        f"run regardless of --max-iterations. Treat best_test_score as low-confidence; consider "
        f"a larger eval set or a lower --holdout."
    )


def split_eval_set(eval_set: list[dict], holdout: float, seed: int = 42) -> tuple[list[dict], list[dict]]:
    """Stratified train/validation split, shuffled once with a fixed seed so
    the split stays identical across every iteration of a given run."""
    random.seed(seed)
    trigger = [e for e in eval_set if e["should_trigger"]]
    no_trigger = [e for e in eval_set if not e["should_trigger"]]
    random.shuffle(trigger)
    random.shuffle(no_trigger)

    n_trigger_val = max(1, int(len(trigger) * holdout))
    n_no_trigger_val = max(1, int(len(no_trigger) * holdout))

    val_set = trigger[:n_trigger_val] + no_trigger[:n_no_trigger_val]
    train_set = trigger[n_trigger_val:] + no_trigger[n_no_trigger_val:]
    return train_set, val_set


def run_loop(
    eval_set: list[dict],
    skill_path: Path,
    description_override: str | None,
    num_workers: int,
    timeout: int,
    max_iterations: int,
    runs_per_query: int,
    trigger_threshold: float,
    holdout: float,
    model: str,
    verbose: bool,
    live_report_path: Path | None = None,
    log_dir: Path | None = None,
) -> dict:
    project_root = find_project_root()
    name, original_description, content = parse_skill_md(skill_path)
    current_description = description_override or original_description

    validation_warning = None
    if holdout > 0:
        train_set, val_set = split_eval_set(eval_set, holdout)
        if verbose:
            print(f"Split: {len(train_set)} train, {len(val_set)} validation (holdout={holdout})", file=sys.stderr)
        validation_warning = split_validation_warning(val_set, len(eval_set), holdout)
        if validation_warning:
            print(f"WARNING: {validation_warning}", file=sys.stderr)
    else:
        train_set, val_set = eval_set, []

    history: list[dict] = []
    exit_reason = "unknown"

    for iteration in range(1, max_iterations + 1):
        if verbose:
            print(f"\n{'='*60}\nIteration {iteration}/{max_iterations}\nDescription: {current_description}\n{'='*60}", file=sys.stderr)

        all_queries = train_set + val_set
        all_results = run_eval(all_queries, name, current_description, num_workers, timeout, project_root, runs_per_query, trigger_threshold, model)

        train_query_set = {q["query"] for q in train_set}
        train_result_list = [r for r in all_results["results"] if r["query"] in train_query_set]
        val_result_list = [r for r in all_results["results"] if r["query"] not in train_query_set]

        train_passed = sum(1 for r in train_result_list if r["pass"])
        train_summary = {"passed": train_passed, "failed": len(train_result_list) - train_passed, "total": len(train_result_list)}

        if val_set:
            val_passed = sum(1 for r in val_result_list if r["pass"])
            val_summary = {"passed": val_passed, "failed": len(val_result_list) - val_passed, "total": len(val_result_list)}
        else:
            val_summary = None

        history.append({
            "iteration": iteration, "description": current_description,
            "train_passed": train_summary["passed"], "train_failed": train_summary["failed"], "train_total": train_summary["total"],
            "train_results": train_result_list,
            "test_passed": val_summary["passed"] if val_summary else None,
            "test_failed": val_summary["failed"] if val_summary else None,
            "test_total": val_summary["total"] if val_summary else None,
            "test_results": val_result_list if val_summary else None,
            "passed": train_summary["passed"], "failed": train_summary["failed"], "total": train_summary["total"], "results": train_result_list,
        })

        if live_report_path:
            partial = {
                "original_description": original_description, "best_description": current_description,
                "best_score": "in progress", "iterations_run": len(history), "holdout": holdout,
                "train_size": len(train_set), "test_size": len(val_set), "history": history,
            }
            live_report_path.write_text(generate_html(partial, auto_refresh=True, skill_name=name))

        if verbose:
            print(f"Train: {train_summary['passed']}/{train_summary['total']} passed", file=sys.stderr)
            if val_summary:
                print(f"Validation: {val_summary['passed']}/{val_summary['total']} passed", file=sys.stderr)

        if train_summary["failed"] == 0:
            exit_reason = f"all_passed (iteration {iteration})"
            break
        if iteration == max_iterations:
            exit_reason = f"max_iterations ({max_iterations})"
            break

        train_results_dict = {"summary": train_summary, "results": train_result_list}
        blinded_history = [{k: v for k, v in h.items() if not k.startswith("test_")} for h in history]
        current_description = improve_description(
            name, content, current_description, train_results_dict, blinded_history, model, log_dir, iteration
        )

    # Select by VALIDATION pass rate, not train — the whole point of the
    # split is to avoid picking an iteration that overfit the train queries.
    if val_set:
        best = max(history, key=lambda h: h["test_passed"] or 0)
        best_score = f"{best['test_passed']}/{best['test_total']}"
    else:
        best = max(history, key=lambda h: h["train_passed"])
        best_score = f"{best['train_passed']}/{best['train_total']}"

    if verbose:
        print(f"\nExit reason: {exit_reason}\nBest score: {best_score} (iteration {best['iteration']})", file=sys.stderr)

    return {
        "exit_reason": exit_reason, "original_description": original_description,
        "best_description": best["description"], "best_score": best_score,
        "best_train_score": f"{best['train_passed']}/{best['train_total']}",
        "best_test_score": f"{best['test_passed']}/{best['test_total']}" if val_set else None,
        "final_description": current_description, "iterations_run": len(history),
        "holdout": holdout, "train_size": len(train_set), "test_size": len(val_set), "history": history,
        "validation_warning": validation_warning,
    }


# ---------------------------------------------------------------------------
# HTML report (train/validation columns, refreshes live during the run)
# ---------------------------------------------------------------------------


def generate_html(data: dict, auto_refresh: bool = False, skill_name: str = "") -> str:
    history = data.get("history", [])
    title_prefix = html.escape(skill_name + " — ") if skill_name else ""

    train_queries: list[dict] = []
    test_queries: list[dict] = []
    if history:
        for r in history[0].get("train_results", history[0].get("results", [])):
            train_queries.append({"query": r["query"], "should_trigger": r.get("should_trigger", True)})
        if history[0].get("test_results"):
            for r in history[0]["test_results"]:
                test_queries.append({"query": r["query"], "should_trigger": r.get("should_trigger", True)})

    refresh_tag = '    <meta http-equiv="refresh" content="5">\n' if auto_refresh else ""

    parts = [f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
{refresh_tag}    <title>{title_prefix}Skill Description Optimization</title>
    <style>
        body {{ font-family: Georgia, serif; max-width: 100%; margin: 0 auto; padding: 20px; background: #faf9f5; color: #141413; }}
        h1 {{ font-family: sans-serif; }}
        .explainer, .summary {{ background: white; padding: 15px; border-radius: 6px; margin-bottom: 20px; border: 1px solid #e8e6dc; }}
        .explainer {{ color: #6b6a63; font-size: 0.875rem; line-height: 1.6; }}
        .best {{ color: #4a7a3a; font-weight: bold; }}
        .table-container {{ overflow-x: auto; width: 100%; }}
        table {{ border-collapse: collapse; background: white; border: 1px solid #e8e6dc; border-radius: 6px; font-size: 12px; min-width: 100%; }}
        th, td {{ padding: 8px; text-align: left; border: 1px solid #e8e6dc; white-space: normal; word-wrap: break-word; }}
        th {{ font-family: sans-serif; background: #141413; color: #faf9f5; }}
        th.test-col {{ background: #4a7ab0; }}
        th.query-col {{ min-width: 200px; }}
        td.description {{ font-family: monospace; font-size: 11px; max-width: 400px; }}
        td.result {{ text-align: center; font-size: 16px; min-width: 40px; }}
        .pass {{ color: #4a7a3a; }}
        .fail {{ color: #c44; }}
        .rate {{ font-size: 9px; color: #6b6a63; display: block; }}
        .score {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px; }}
        .score-good {{ background: #eef2e8; color: #4a7a3a; }}
        .score-ok {{ background: #fef3c7; color: #a05a00; }}
        .score-bad {{ background: #fceaea; color: #c44; }}
        .best-row {{ background: #f5f8f2; }}
        th.positive-col {{ border-bottom: 3px solid #4a7a3a; }}
        th.negative-col {{ border-bottom: 3px solid #c44; }}
        .legend {{ display: flex; gap: 20px; margin-bottom: 10px; font-size: 13px; align-items: center; font-family: sans-serif; }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; }}
        .legend-swatch {{ width: 16px; height: 16px; border-radius: 3px; display: inline-block; }}
        .swatch-positive {{ background: #141413; border-bottom: 3px solid #4a7a3a; }}
        .swatch-negative {{ background: #141413; border-bottom: 3px solid #c44; }}
        .swatch-test {{ background: #4a7ab0; }}
        .swatch-train {{ background: #141413; }}
    </style>
</head>
<body>
    <h1>{title_prefix}Skill Description Optimization</h1>
    <div class="explainer">
        <strong>Optimizing your skill's description.</strong> Each row is an iteration. Columns are test queries:
        green check = triggered correctly (or correctly didn't); red cross = wrong. "Train" is the score on queries
        used to improve the description; "Validation" is held-out queries the optimizer never sees during improvement.
        The best-scoring iteration by validation score gets applied at the end.
    </div>
"""]

    best_test_score = data.get("best_test_score")
    validation_warning = data.get("validation_warning")
    warning_html = (
        f'<p class="score-bad" style="padding:8px;border-radius:4px;background:#fceaea;">'
        f'<strong>⚠ Low-confidence validation:</strong> {html.escape(validation_warning)}</p>'
        if validation_warning else ""
    )
    parts.append(f"""
    <div class="summary">
        <p><strong>Original:</strong> {html.escape(data.get('original_description', 'N/A'))}</p>
        <p class="best"><strong>Best:</strong> {html.escape(data.get('best_description', 'N/A'))}</p>
        <p><strong>Best Score:</strong> {data.get('best_score', 'N/A')} {'(validation)' if best_test_score else '(train)'}</p>
        <p><strong>Iterations:</strong> {data.get('iterations_run', 0)} | <strong>Train:</strong> {data.get('train_size', '?')} | <strong>Validation:</strong> {data.get('test_size', '?')}</p>
        {warning_html}
    </div>
    <div class="legend">
        <span style="font-weight:600">Query columns:</span>
        <span class="legend-item"><span class="legend-swatch swatch-positive"></span> Should trigger</span>
        <span class="legend-item"><span class="legend-swatch swatch-negative"></span> Should NOT trigger</span>
        <span class="legend-item"><span class="legend-swatch swatch-train"></span> Train</span>
        <span class="legend-item"><span class="legend-swatch swatch-test"></span> Validation</span>
    </div>
    <div class="table-container">
    <table>
        <thead>
            <tr>
                <th>Iter</th><th>Train</th><th>Validation</th><th class="query-col">Description</th>
""")

    for qinfo in train_queries:
        polarity = "positive-col" if qinfo["should_trigger"] else "negative-col"
        parts.append(f'                <th class="{polarity}">{html.escape(qinfo["query"])}</th>\n')
    for qinfo in test_queries:
        polarity = "positive-col" if qinfo["should_trigger"] else "negative-col"
        parts.append(f'                <th class="test-col {polarity}">{html.escape(qinfo["query"])}</th>\n')
    parts.append("            </tr>\n        </thead>\n        <tbody>\n")

    if not history:
        parts.append("        </tbody></table></div></body></html>")
        return "".join(parts)

    best_iter = (max(history, key=lambda h: h.get("test_passed") or 0) if test_queries
                 else max(history, key=lambda h: h.get("train_passed", h.get("passed", 0))))["iteration"]

    def aggregate_runs(results: list[dict]) -> tuple[int, int]:
        correct = total = 0
        for r in results:
            runs, triggers = r.get("runs", 0), r.get("triggers", 0)
            total += runs
            correct += triggers if r.get("should_trigger", True) else runs - triggers
        return correct, total

    def score_class(correct: int, total: int) -> str:
        if total > 0:
            ratio = correct / total
            return "score-good" if ratio >= 0.8 else "score-ok" if ratio >= 0.5 else "score-bad"
        return "score-bad"

    for h in history:
        train_results = h.get("train_results", h.get("results", []))
        test_results = h.get("test_results") or []
        train_by_query = {r["query"]: r for r in train_results}
        test_by_query = {r["query"]: r for r in test_results}
        train_correct, train_runs = aggregate_runs(train_results)
        test_correct, test_runs = aggregate_runs(test_results)
        row_class = "best-row" if h.get("iteration") == best_iter else ""

        parts.append(f"""            <tr class="{row_class}">
                <td>{h.get('iteration', '?')}</td>
                <td><span class="score {score_class(train_correct, train_runs)}">{train_correct}/{train_runs}</span></td>
                <td><span class="score {score_class(test_correct, test_runs)}">{test_correct}/{test_runs}</span></td>
                <td class="description">{html.escape(h.get('description', ''))}</td>
""")
        for qinfo in train_queries:
            r = train_by_query.get(qinfo["query"], {})
            icon, css = ("✓", "pass") if r.get("pass") else ("✗", "fail")
            parts.append(f'                <td class="result {css}">{icon}<span class="rate">{r.get("triggers", 0)}/{r.get("runs", 0)}</span></td>\n')
        for qinfo in test_queries:
            r = test_by_query.get(qinfo["query"], {})
            icon, css = ("✓", "pass") if r.get("pass") else ("✗", "fail")
            parts.append(f'                <td class="result {css}">{icon}<span class="rate">{r.get("triggers", 0)}/{r.get("runs", 0)}</span></td>\n')
        parts.append("            </tr>\n")

    parts.append("        </tbody>\n    </table>\n    </div>\n</body>\n</html>\n")
    return "".join(parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    eval_set = json.loads(Path(args.eval_set).read_text())
    skill_path = Path(args.skill_path)
    if not (skill_path / "SKILL.md").exists():
        print(f"Error: no SKILL.md found at {skill_path}", file=sys.stderr)
        return 1

    name, _, _ = parse_skill_md(skill_path)

    if args.report != "none":
        if args.report == "auto":
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            live_report_path = Path(tempfile.gettempdir()) / f"skill_description_report_{skill_path.name}_{timestamp}.html"
        else:
            live_report_path = Path(args.report)
        live_report_path.write_text("<html><body><h1>Starting optimization loop...</h1><meta http-equiv='refresh' content='5'></body></html>")
        if not args.no_browser:
            webbrowser.open(str(live_report_path))
    else:
        live_report_path = None

    results_dir = None
    if args.results_dir:
        timestamp = time.strftime("%Y-%m-%d_%H%M%S")
        results_dir = Path(args.results_dir) / timestamp
        results_dir.mkdir(parents=True, exist_ok=True)
    log_dir = results_dir / "logs" if results_dir else None

    output = run_loop(
        eval_set=eval_set, skill_path=skill_path, description_override=args.description,
        num_workers=args.num_workers, timeout=args.timeout, max_iterations=args.max_iterations,
        runs_per_query=args.runs_per_query, trigger_threshold=args.trigger_threshold, holdout=args.holdout,
        model=args.model, verbose=args.verbose, live_report_path=live_report_path, log_dir=log_dir,
    )

    json_output = json.dumps(output, indent=2)
    print(json_output)
    if results_dir:
        (results_dir / "results.json").write_text(json_output)

    if live_report_path:
        live_report_path.write_text(generate_html(output, auto_refresh=False, skill_name=name))
        print(f"\nReport: {live_report_path}", file=sys.stderr)
        if results_dir:
            (results_dir / "report.html").write_text(generate_html(output, auto_refresh=False, skill_name=name))
    if results_dir:
        print(f"Results saved to: {results_dir}", file=sys.stderr)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    data = json.load(sys.stdin) if args.input == "-" else json.loads(Path(args.input).read_text())
    output_html = generate_html(data, skill_name=args.skill_name)
    if args.output:
        Path(args.output).write_text(output_html)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output_html)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize a skill's frontmatter description for trigger accuracy")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run the eval + improve loop")
    p_run.add_argument("--eval-set", required=True, help="Path to eval set JSON (list of {query, should_trigger})")
    p_run.add_argument("--skill-path", required=True, help="Path to skill directory")
    p_run.add_argument("--description", default=None, help="Override starting description")
    p_run.add_argument("--num-workers", type=int, default=10)
    p_run.add_argument("--timeout", type=int, default=30, help="Timeout per query, seconds")
    p_run.add_argument("--max-iterations", type=int, default=5)
    p_run.add_argument("--runs-per-query", type=int, default=3)
    p_run.add_argument("--trigger-threshold", type=float, default=0.5)
    p_run.add_argument("--holdout", type=float, default=0.4, help="Fraction held out for validation (0 disables the split)")
    p_run.add_argument("--model", required=True, help="Model ID powering the current session")
    p_run.add_argument("--verbose", action="store_true")
    p_run.add_argument("--report", default="auto", help="HTML report path ('auto' for temp file, 'none' to disable)")
    p_run.add_argument("--no-browser", action="store_true", help="Don't auto-open the report (Cowork/headless)")
    p_run.add_argument("--results-dir", default=None, help="Save results.json/report.html/logs under a timestamped subdirectory here")
    p_run.set_defaults(func=cmd_run)

    p_report = sub.add_parser("report", help="Regenerate the HTML report from a saved results.json")
    p_report.add_argument("input", help="Path to results.json, or - for stdin")
    p_report.add_argument("-o", "--output", default=None)
    p_report.add_argument("--skill-name", default="")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
