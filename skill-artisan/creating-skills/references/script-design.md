# Script Design

Conventions for anything placed in a skill's own `scripts/` directory — including this plugin's own (`security_scan.py`, `validate.py`, `dedup_search.py`, `eval_loop.py`, `description_optimizer.py`), which follow every rule below.

## Table of Contents

- [Non-interactive only](#non-interactive-only)
- [Interface conventions](#interface-conventions)
- [Idempotent where feasible](#idempotent-where-feasible)
- [Bounded output](#bounded-output)
- [One-off commands: prefer pinned runners](#one-off-commands-prefer-pinned-runners)
- [The scripts/ discipline](#the-scripts-discipline)

## Non-interactive only

Agents operate in non-interactive shells — nothing responds to a TTY prompt. A script that blocks waiting for input (a bare `input()`, a confirmation prompt with no flag to skip it) hangs indefinitely from the agent's perspective; there's no human at the terminal to answer it. Accept every input via flags, environment variables, or stdin, never via an interactive prompt. This project's own scripts take skill paths, model IDs, and thresholds as `argparse` flags for exactly this reason — none of them ever call `input()`.

`scripts/security_scan.py --verbose` checks for this mechanically (the `blocking-interactive-input` pattern check — HIGH severity, since a hung script is a real operational failure, not just a style issue): `input(`/`raw_input(` in Python, `read -p` in bash. It also flags scripts under `scripts/` that produce output but reference no argument-parsing convention at all (`no-documented-cli`, MEDIUM — informational, since this is a quality signal rather than something that actively breaks an agent run).

## Interface conventions

- **Document the interface via `--help`.** `argparse`'s default `--help` output is sufficient — every script in this plugin relies on it rather than a separate man page or usage doc.
- **Separate structured data from diagnostics.** Machine-readable output (a JSON report, a generated file path) goes to stdout; progress messages, warnings, and human-readable narration go to stderr. `security_scan.py --json` and `validate.py --json` follow this split explicitly — piping either into `jq` without stderr noise works cleanly.
- **Meaningful, documented exit codes.** Not just 0/1 — distinguish "the check found a real problem" from "the tool itself couldn't run" (gitleaks not installed is exit 3 in `security_scan.py`, not the same 1 a real finding produces). An agent deciding how to react to a failure needs that distinction, and a human debugging a CI pipeline needs it more.

## Idempotent where feasible

Running a script twice with the same inputs should produce the same result, not accumulate state or error on a second run. `security_scan.py`'s marker write is idempotent — rerunning it after no changes overwrites the marker with the same hash. `validate.py` has no side effects at all. The place this gets harder is anything that calls out to a model (`description_optimizer.py`'s trigger evaluation) — that's inherently non-deterministic at the individual-query level, which is exactly why it runs each query multiple times against a trigger-rate threshold rather than trusting a single call.

## Bounded output

Many agent harnesses truncate tool output past 10-30K characters. A script that dumps an entire directory tree or an unbounded log to stdout risks having its most important line — the actual result — silently cut off. Default to a summary; support an explicit `--offset`/pagination flag or an `--output file|-` flag for anything that could genuinely be large. None of this plugin's own scripts currently produce output at real risk of hitting that ceiling (the largest single output, the HTML eval viewer, is written to a file rather than printed), but it's worth checking before adding new output paths to any of them.

## One-off commands: prefer pinned runners

For a dependency a script needs but that doesn't warrant becoming a project dependency itself, prefer a pinned one-off runner over assuming the environment has it pre-installed: `uvx`, `pipx`, `npx`, `bunx`, `deno run`, `go run`, each with an explicit version pin. `validate.py` does exactly this for `skills-ref` (`npx --yes skills-ref@0.1.5`) rather than requiring authors to globally install it first — falling back to a locally-installed copy first if one's on `PATH`, since a pin only matters when there isn't already a deliberate local choice to respect. State the actual runtime prerequisite (Node.js, in that case) via the skill's `compatibility` field rather than silently assuming it's there.

## The scripts/ discipline

Two rules (row 34, prior art: `mgechev/skills-best-practices`), applied to this plugin's own `scripts/` directory as well as taught to authors:

1. **Tiny, single-purpose CLIs — no bundled library code.** A script that keeps growing eventually stops being a script and starts being an undeclared library with a CLI bolted on. When shared logic is needed across more than one script, factor it into a small internal module rather than letting one script absorb everything. This plugin's `scripts/_common.py` exists for exactly this reason — `parse_skill_md`, `calculate_stats`, and the named trial-count presets are used by more than one script, so they live in one place instead of being copy-pasted or crammed into whichever script needed them first. `_common.py` has no `__main__` and isn't meant to be run directly — it's the module the "tiny CLI" rule is protecting, not an exception to it.
2. **No `README.md`/`CHANGELOG.md`/install guides inside a skill's own directory.** These are human docs, and anything inside a skill's directory is context an agent loads on activation — a README written for a human browsing the repo is pure token cost with zero behavioral benefit once it's sitting inside `creating-skills/`. This plugin's own `README.md` and `CHANGELOG.md` live at the plugin root, outside `creating-skills/`, enforced by `.skillignore` at the plugin root rather than left as an unenforced convention (see `references/security-checklist.md`'s packaging-exclusion section).
