# SkillArtisan

A plugin for Claude Code that builds, validates, secures, and maintains Claude Skills — superseding Anthropic's shipped `skill-creator` with a spec-compliant, cross-vendor, security-hardened successor.

SkillArtisan bundles a main skill named **`creating-skills`** along with an evaluation engine, a security scanner, a dedup/decision gate, and an audit mode for existing skills. It is not a single SKILL.md file — see [Architecture](#architecture) below.

## Why this exists

Anthropic's own `skill-creator` is a good starting point, but has real gaps: no frontmatter validation, no gerund-naming guidance, no multi-model testing, no security scanning beyond a one-line "don't build malware" principle, and no way to audit or upgrade an existing skill. SkillArtisan closes all of these, while keeping the one thing `skill-creator` already does well — its evaluation and description-optimization engine — fully intact.

The design is grounded in the canonical, cross-vendor [agentskills.io](https://agentskills.io) specification (not just Claude-specific conventions), so skills built with SkillArtisan are portable across Claude Code, Cursor, GitHub Copilot, Codex, Gemini CLI, and 40+ other agent products by default.

## Install

```
claude plugin marketplace add <owner>/skill-artisan
claude plugin install skill-artisan
```

Requirements: Python 3.8+, [gitleaks](https://github.com/gitleaks/gitleaks) (for security scanning), `claude` CLI (for evaluation runs and description optimization).

**Developing SkillArtisan itself, rather than installing it?** The eval engine's `grader`/`comparator`/`analyzer` subagents (`agents/*.md`) are only invocable via `Task(subagent_type: ...)` once the plugin is genuinely installed — confirmed directly: installing it locally mid-session does not make them available in that same session, since Claude Code's subagent-type registry is fixed at session start. A repo-context session (this repo open directly, not installed) should follow each agent's documented process by hand instead — see `creating-skills/SKILL.md`'s "Testing and evaluating" section for the proven fallback.

## Quick start

Once installed, just ask Claude naturally:

```
"Create a skill that reviews pull requests for our team's style guide"
"Audit my existing invoice-parser skill against best practices"
"Benchmark this skill's trigger accuracy"
```

SkillArtisan's decision gate will first confirm a skill is actually the right tool (as opposed to CLAUDE.md, AGENTS.md, an MCP server, a subagent, or a plugin), check whether something already solves the request, then walk through authoring, validation, security scanning, and evaluation.

## What's different from `skill-creator`

| | `skill-creator` (Anthropic) | SkillArtisan |
|---|---|---|
| Frontmatter validation | `scripts/quick_validate.py` exists (kebab-case, length limits, required fields) but is never referenced by `SKILL.md`'s own documented process — unused in practice | Wraps the official `skills-ref` validator + Claude-specific checks |
| Naming guidance | Same unused script covers kebab-case/hyphen rules; no gerund-form guidance anywhere | Gerund-form enforcement (warning, not a hard fail — `skills-ref` itself accepts non-gerund names), parent-directory matching |
| Decision gate | None — jumps straight to authoring | Skill vs. CLAUDE.md vs. AGENTS.md vs. MCP vs. subagent vs. plugin, plus a dedup/compose check |
| Security | "Don't build malware" (one line) | Gitleaks-based scan, pattern checks, content-hash tamper detection, AI semantic read-through |
| Surfaces covered | Claude Code, Claude.ai, Cowork | + Claude Tag, Messages API, generic cross-vendor |
| Multi-model testing | Not mentioned | Explicit Haiku/Sonnet/Opus pass |
| Existing-skill audit | Path-handling advice only | Full audit mode (`scripts/audit.py`): checklist scoring, upgrade-vs-rebuild decision, institutional-knowledge preservation, regression benchmarking, bulk mode |
| Lifecycle tracking | Not mentioned | Capability-uplift vs. encoded-preference classification with a scored timelessness threshold (`references/lifecycle.md`) |
| Eval engine | Strong — with/without-skill runs, description optimizer | Same engine, ported intact — this is the one thing kept unchanged |

See the full [Gap Table](../skill-artisan-master-spec.md#gap-table) (40 rows) for the complete comparison, including against other community tools (`daymade/claude-code-skills`, `tripleyak/SkillForge`).

## Verified against `skill-creator`'s current source

This isn't a "best in market" claim — that requires the full Best-in-Market Scorecard (see Release scope below), which hasn't run. It's narrower and more concrete: the one piece of `skill-creator` this project explicitly kept "fully intact" — its evaluation/description-optimization engine, ported wholesale rather than rebuilt — turned out to need five real fixes that actual regression testing caught, not code review. All five were checked directly against Anthropic's own currently-shipped `skill-creator` source (not a stale snapshot); **all five are present and unfixed there today**, two of them worse than SkillArtisan's own pre-fix versions were.

1. **Premature-return trigger-detection bug.** `run_eval.py`'s `run_single_query()` returns on the first non-Skill/Read tool call, before the conversation reaches its final `result` event — a false-negative trigger-detection bug. Confirmed still present, unfixed, in `skill-creator`'s current source (`run_eval.py` lines 141/168). Fixed in SkillArtisan's `description_optimizer.py`, `[2.2.2]`.
2. **Timeout too short for real `claude -p` calls.** `skill-creator`'s `--timeout` defaults to 30 seconds in both `run_eval.py` and `run_loop.py` — confirmed unchanged, and worse than SkillArtisan's own pre-fix 60s. Raised to 180s in `[2.2.2]`, based on directly observed real call durations.
3. **Crash on explicit JSON `null` (not just a missing key).** `aggregate_benchmark.py` crashes with `AttributeError` on a `grading.json` containing explicit `"timing": null` — exactly the pattern SkillArtisan's own graders wrote whenever timing data was genuinely unrecoverable. Live-reproduced against skill-creator's actual current source; the identical fixture runs clean through SkillArtisan's `eval_loop.py`. Fixed in `[2.2.2]`.
4. **Non-atomic skill-directory publish race.** `run_eval.py`'s `run_single_query()` publishes its synthetic test-skill directory via `mkdir()` then a separate `write_text()` — a real window where a concurrent `claude -p` process's discovery scan can observe a broken entry. Confirmed present in skill-creator's current source, with a wider vulnerable window than SkillArtisan had even before its own fix. A dedicated concurrency stress test found the old approach exposed a broken entry in ~99% of concurrent scans; SkillArtisan's atomic `os.rename()`-based fix (`[2.2.3]`) brought that to 0%.
5. **No warning when the description-optimizer's validation set is too small to mean anything.** `split_eval_set()` computes a single train/validation split once, with a hardcoded `seed=42`; `improve_description()` is deliberately never shown which validation queries fail (correct anti-overfitting design), but for a small eval corpus that one-time holdout can be tiny enough that a single query flipping swings the reported score by 20+ points, with zero mechanism to ever fix a query that lands there. Confirmed directly on a real run: 3 validation queries stuck failing identically across 5 iterations of materially different description rewrites. Confirmed present, unfixed, in `skill-creator`'s current `run_loop.py` too — identical split logic and identical blinding mechanism, down to the same code comment. Fixed in `[2.2.4]` by warning (stderr, JSON output, and the HTML report) whenever a validation class has fewer than 5 examples.

Reproduce all five yourself: `bash benchmark/skill-creator-comparison-repro.sh` (requires the official `skill-creator` plugin installed locally). Re-run it before trusting these as current — `skill-creator` may have fixed some of them upstream since.

## Architecture

SkillArtisan ships as a plugin, not a single skill, because its infrastructure genuinely needs more than one file:

```
skill-artisan/
├── .claude-plugin/plugin.json
├── creating-skills/          # the main skill — entry point, decision gate
│   ├── SKILL.md
│   └── references/
├── agents/                   # eval subagents (grader, comparator, analyzer)
├── eval-viewer/               # HTML review UI for benchmark results
├── assets/
├── scripts/                  # validation, security scanning, dedup search, eval loop, audit
├── benchmark/                 # regression/QA harness + corpus for testing creating-skills
│                              #   itself — development tooling, not part of the installed skill
├── LICENSE
├── CHANGELOG.md
├── .skillignore
└── README.md
```

Full rationale in the project's [master specification](../skill-artisan-master-spec.md).

## Release scope

SkillArtisan shipped in two deliberate stages, both now released:

- **v1** (`1.0.0`) — eval engine, decision gate, surface matrix, security scanning. A complete, usable tool on its own.
- **v2** (`2.0.0`) — lifecycle framing (capability-uplift vs. encoded-preference classification, `creating-skills/references/lifecycle.md`) and audit mode (`scripts/audit.py`: upgrade/rebuild existing skills, bulk mode across a whole skills directory, an optional additive-only contribution-plan mode for third-party repos). Shipped after v1 had been dogfooded on a real project skill, so the audit heuristics were informed by real usage (see `[1.0.1]` in the changelog) rather than designed in a vacuum.

These two stages mark deliberate scope boundaries, not the current version — seven patch/minor releases (`2.0.1` through `2.2.4`) have shipped since v2.0.0, including a single-arm regression/QA effort (`benchmark/`) that found and fixed five real bugs in the eval engine itself (see "Verified against `skill-creator`'s current source" above). See [CHANGELOG.md](./CHANGELOG.md) for the current version and the full list.

The one thing none of these releases did: claim "best in market." That requires the master spec's full Best-in-Market Scorecard — a 12-20 skill benchmark corpus, four other comparison arms actually run, three axes scored separately — and that hasn't been run yet. See [CHANGELOG.md](./CHANGELOG.md) for what's shipped, what's deferred, and why.

## Security

Every skill produced or audited by SkillArtisan is scanned with [gitleaks](https://github.com/gitleaks/gitleaks) before packaging, plus pattern-based checks for absolute paths, exposed emails, insecure URLs, and dangerous code patterns (available via `--verbose`). A content-hash tamper-detection marker prevents shipping a skill that was edited after its last clean scan.

**Automated scanning has a ceiling.** Pattern-based tools cannot see everything — they're blind to non-English content, real names embedded in examples, or lines lifted from real transcripts, since none of that has a keyword to trigger on. Before publishing any skill publicly, read it yourself. A clean scan is a gate, not a guarantee. See `references/sanitization-checklist.md`.

## Credits

SkillArtisan's evaluation engine is ported from Anthropic's `skill-creator`. Its security scanning architecture, dedup/decision gate refinements, and several structural conventions are adapted from real prior art in this space — particularly [`daymade/claude-code-skills`](https://github.com/daymade/claude-code-skills) and [`tripleyak/SkillForge`](https://github.com/tripleyak/SkillForge) — with attribution preserved in the [Gap Table](../skill-artisan-master-spec.md#gap-table) row by row. This project exists because that prior art already fought many of these battles well; the goal was to synthesize the best of it against the canonical spec, not to claim originality it doesn't have.

## License

MIT — see [LICENSE](./LICENSE).
