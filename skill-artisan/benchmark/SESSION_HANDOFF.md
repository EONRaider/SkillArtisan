# Session handoff — 2026-08-18

Written just before a `/clear`, so a fresh context (same session/environment) can pick this up without re-deriving it. Read this first if you're resuming work on Item 5 / the benchmark effort.

## What happened, in order

1. **Item 5 was originally a full 5-arm comparative "Best-in-Market Scorecard"** (No skill / `skill-creator` / daymade's fork / `SkillForge` / `creating-skills`) per `skill-artisan-master-spec.md`'s "Best-in-Market Scorecard" section.
2. **A 3-skill pilot of that methodology surfaced real cost/reliability problems** before producing usable comparative numbers: concurrent `claude -p` subprocess calls above 1 worker caused near-total trigger-detection failure; per-arm costs projected into the tens of millions of tokens across the full 12-20 skill corpus; several real bugs in this project's own harness/tooling scripts needed fixing along the way.
3. **The user explicitly decided to abandon the comparative approach** and pivot to **single-arm regression/QA testing of `creating-skills` alone** — author the remaining corpus skills through it exclusively, run real with-skill/without-skill eval loops on each, to surface real bugs in the shipped product rather than produce a competitive claim.
4. **13 more skills were authored via `creating-skills` alone** (on top of a 12-run pilot = 25 tracked runs total), each with a full with-skill/baseline eval loop, grading, and aggregation.
5. **6 of those 13 skills initially reached "authored, validated, security-scanned" but not "eval-tested"** — their eval loops were interrupted before completion when this conversation's context first got long. This was caught, and **all 6 were retested to completion** in a follow-up pass (see below).
6. **The master spec was corrected** (dated block at the top of "Best-in-Market Scorecard") to document the pivot without deleting the original methodology — it's now explicitly future work, not completed work.
7. **A real, verified finding was added to Confidence Notes**: `description_optimizer.py` and `eval_loop.py` are confirmed (via their own file headers) to be direct ports of `skill-creator`'s own code; `security_scan.py` is daymade's architecture, not a skill-creator port. Real bugs were found and fixed in the two ported scripts through actual use.
7a. **This was then checked with certainty against `skill-creator`'s actual current source** (locally installed official plugin, `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/`, dated 2026-08-17 — one day old at the time, not stale). **All three findings confirmed, two of them worse than in our pre-fix code:**
    - The premature-return trigger-detection bug is present, unfixed, in `skill-creator`'s `run_eval.py` right now (read directly from source: lines 141/168 return before the `result` event).
    - `skill-creator`'s own `--timeout` defaults to **30 seconds** in both `run_eval.py` and `run_loop.py` — worse than our pre-fix 60s.
    - The None-vs-missing-key crash was **live-reproduced**: a `grading.json` with explicit `"timing": null, "execution_metrics": null` (the exact pattern our own graders wrote whenever data was genuinely unrecoverable) crashes `skill-creator`'s `aggregate_benchmark.py` with `AttributeError`; the identical fixture runs clean through SkillArtisan's `eval_loop.py`.
    - **Reproducible script saved at `skill-artisan/benchmark/skill-creator-comparison-repro.sh`** — re-run this before citing any of these findings in the README, in case skill-creator has since fixed them upstream. Full writeup is in `skill-artisan-master-spec.md`'s Confidence Notes (search for "Update, 2026-08-18, same day").
    - **These findings are earmarked for the README** once the development cycle is done (user's explicit instruction) — they're real, reproducible, dated, and go beyond "we think we're better" into "here's Anthropic's own current code crashing on a real input, and ours doesn't." Don't let this get lost — it's the strongest concrete evidence this project has produced so far for any comparative claim.
8. **CHANGELOG.md and plugin.json were bumped to 2.2.2** documenting the three tooling fixes (see below).

## Current state: everything in Step 1 is DONE

All 25 tracked runs (12 pilot + 13 new) show `complete` in `run_authoring.py status`, run from `skill-artisan/benchmark/harness/`. Total spend across the whole effort: ~10.1M tokens (authoring ≈7.26M + retest ≈2.9M).

### Real bugs found and FIXED in SkillArtisan's own shipped tooling (`skill-artisan/scripts/`) — now in CHANGELOG 2.2.2, plugin.json bumped to 2.2.2
- `description_optimizer.py`: premature-return bug in `run_single_query()` (false-negative trigger detection); 60s timeout too short, raised to 180s with a stderr warning.
- `eval_loop.py`: crashed on explicit JSON `null` (vs. missing key) in timing/metrics fields.
- `security_scan.py --json`: leaked human-readable text onto stdout after the JSON payload on clean scans.

### Real bugs found and FIXED in individual authored skills (benchmark corpus, not shipped product — no CHANGELOG entry needed)
- `ui-designer` (`building-ui-design-systems`): did design-system extraction before building the PRD, contradicting its own stated order. Fixed, re-tested (2/3 → 3/3).
- `deep-research` (`conducting-deep-research`): silently produced an empty report under budget pressure on deep-tier queries. Fixed with incremental registry checkpointing + graceful degradation.
- `github-sensitive-data-cleanup` (`cleaning-leaked-secrets-from-git-history`): its bundled `scan_history.py` had a gitleaks-allowlist blind spot on AWS documentation-placeholder-shaped keys. Fixed with an independent backstop regex.

### Confirmed real value: baseline (no-skill) behavior that was genuinely unsafe, correctly prevented by the authored skill
- `repomix-unmixer`: baseline *complied* with a path-traversal write instruction in its own stated reasoning (only sandboxed by the harness, not by its own judgment). With-skill refused via the bundled script's real traversal defense.
- `repomix-safe-mixer`: baseline packed a project after auto-excluding leaked-credential files instead of refusing outright (100% vs 38% pass rate — the largest delta of the retest).
- `git-safety-net`: baseline ran an unconfirmed `git branch -d` immediately after its merge check — only failed because git's own worktree guard blocked it, not because it asked first.
- `github-sensitive-data-cleanup`: baseline used a deprecated rewrite tool, didn't verify its backup, silently performed the destructive rewrite while presenting it as pending advice to the user, and separately said `--no-verify` was fine when it wasn't.
- `bilibili-source` and `dataset-bias-auditor`'s eval-1: non-discriminating (clean sweep both ways) — reported honestly as such, not forced into a false delta.

## What's NOT done — Step 2

Per the original plan the user set out when authorizing the pivot: Axis 2 trigger-accuracy scoring across all 16 corpus skills (single-arm, `axis2_trigger_scorer.py`, `--num-workers 1` — confirmed unsafe above 1 concurrent `claude -p` call), then task-success scope decided with real numbers in hand. **Not started.** User said to notify them when ready to move on to this — that notification is the reason this handoff exists.

## Operational gotchas learned the hard way (don't rediscover these)

- **Nested subagent completion notifications route to the top-level session, not back to the spawning parent subagent.** A parent that spawns child executors/graders and "waits for their notifications" will wait forever unless the top-level session relays completion back to it explicitly via `SendMessage`. This happened repeatedly — always check `ListAgents` + file timestamps on disk before trusting a parent's self-reported "still waiting" status; if the parent shows idle/no-reachable-agents but its children's outputs exist on disk, relay directly.
- **2 parent subagents in flight at a time has been the safe, established concurrency convention** for this Agent-tool-based orchestration (distinct from the `claude -p` subprocess concurrency issue below).
- **`claude -p` subprocess concurrency above 1 worker is catastrophically unsafe** (near-100% detection failure) — always `--num-workers 1` for `axis2_trigger_scorer.py` or any similar tool.
- **Eval-workspace directory naming is non-uniform per-skill** (`eval-workspace/iteration-1/` vs `creating-skills/eval-workspace/iteration-1/` vs `creating-skills/output/eval-workspace/iteration-1/` vs `_bench/` — each authoring agent chose its own convention). Don't hardcode a path pattern when checking for grading.json/activity across multiple skills — search the whole skill's workspace tree.
- **A background monitor script checking file activity by a fixed subpath can produce false "stalled" alarms** — always re-verify against the actual filesystem (broad `find`) and `ListAgents` before concluding something is actually stuck, not just proxied wrong.
- **Fixture repos for git-related skill testing should stay under the scratchpad or workspace, not a general home-directory location** — one retest run built fixtures at `/home/eonraider/code/` before being redirected; verify and clean these up after retests involving real git repos.

## Where things live
- `skill-artisan-master-spec.md` — corrected, current.
- `skill-artisan/CHANGELOG.md` — `2.2.2` shipped (tooling fixes only).
- `skill-artisan/.claude-plugin/plugin.json` — version `2.2.2`.
- `skill-artisan/benchmark/harness/run_authoring.py` — the workspace tracker (`status`, `cost`, `mark-complete` subcommands). All 25 runs `complete`.
- `skill-artisan/benchmark/harness/workspace/<skill>/` — each authored skill's output + eval artifacts.
- `skill-artisan/benchmark/harness/axis2_trigger_scorer.py` — built for Step 2, not yet run at scale.
- `skill-artisan/benchmark/skill-creator-comparison-repro.sh` — reproduces the three verified skill-creator-vs-SkillArtisan findings on demand. Run before citing them in the README.
