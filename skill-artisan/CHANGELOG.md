# Changelog

All notable changes to SkillArtisan are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [Semantic Versioning](https://semver.org/), interpreted for this project as:

- **Major version bump (1.0.0 → 2.0.0)** marks a v-stage boundary, not just a breaking change — v1 → v2 is the deliberate release split (see the master spec's "Build Stages → Plugin Files → Release Scope"), not an accident of semver discipline.
- **Minor version** for new capability within a stage that doesn't break existing usage (e.g. adding cross-agent evaluation as an opt-in mode within v1).
- **Patch version** for fixes — corrected patterns, tightened validation, documentation accuracy.

## [Unreleased]

### Planned for 2.0.0 (v2)
- Lifecycle framing: capability-uplift vs. encoded-preference classification with a scored timelessness threshold
- Audit mode: score an existing skill against the full checklist, upgrade-vs-rebuild decision, institutional-knowledge preservation, regression benchmarking
- Bulk audit mode across an entire skills directory
- Optional: contribute-back / auto-PR mode for third-party skill repositories

Ships once v1 has been used on real skills — see the master spec's "Build Stages → Plugin Files → Release Scope" for why the gap is deliberate, not a delay.

## [1.0.1] - 2026-08-16

### Fixed
- **`scripts/description_optimizer.py`: trigger-eval self-collision when testing description changes for an already-installed skill.** Found while dogfooding v1 on a real project skill (`drafting-changelog-entries`, added to this repo's own `.claude/skills/` as the v1 dogfood exercise — not part of the shipped plugin). The per-query synthetic test copy gets a randomized name specifically so it won't collide with anything real, but if the skill under test is *also* sitting at its real, natural name in the same project with a near-identical description, the model tends to reach for the naturally-named real one instead of the synthetic candidate — and the harness only counts a trigger against the synthetic name, so every one of those turns silently reads as a miss. Confirmed directly: the exact same query/description pair scored 0/3 with the real skill present, 1/3 with it hidden. `run_eval` now moves the real `.claude/skills/<name>/` aside for the duration of the run and restores it afterward (`try`/`finally`). Verified the restore fires on normal completion; the crash-safety property for an abnormal exit mid-run rests on the `try`/`finally` construct itself rather than on having reproduced an actual kill during testing — worth a closer look before relying on it for anything long-running. Only matters for improving an existing skill — a brand-new skill has nothing installed yet to collide with.

## [1.0.0] - 2026-08-15

Stages 1-4 of the master spec, built and verified against a live `claude -p` session and a real `gitleaks` install (not just documentation) — per the companion build prompt (Prompt A; kept locally rather than in this repo, not published alongside the plugin).

### Added
- **Eval engine**, ported from `skill-creator` with no loss of capability: parallel with/without-skill subagent runs from a clean context, `agents/grader.md`/`comparator.md`/`analyzer.md` subagent roles, the `evals/evals.json` test-case format, benchmark aggregation with mean/stddev/delta (`scripts/eval_loop.py`), an analyst pass flagging always-pass/always-fail assertions, blind A/B comparison, the HTML eval-viewer (`eval-viewer/generate_review.py` + `viewer.html`, Outputs/Benchmark tabs, `--static` mode, `--previous-workspace` diffing), and the trigger-eval review template (`assets/eval_review.html`).
- **Description optimizer** (`scripts/description_optimizer.py`): 60/40 train/validation split (shuffled once, fixed across iterations), 3x runs per query against a 0.5 trigger-rate threshold, up to 5 iterations, selection by validation pass rate. Fixed two real bugs found while verifying this against a live session: the trigger-registration path (`.claude/skills/<name>/SKILL.md`, not `.claude/commands/` — the latter registers as a slash command and never appears in `available_skills`) and a concurrency race between simultaneously-launched `claude -p` subprocesses sharing one project root (fixed with a small launch stagger).
- **Named trial-count presets** (`--smoke`/`--reliable`/`--regression`) and **CI gating** (`--ci --threshold`) in `scripts/eval_loop.py`.
- **The Decision Gate**, in `creating-skills/SKILL.md`: artifact-type routing (skill vs. CLAUDE.md vs. AGENTS.md vs. MCP vs. subagent vs. plugin vs. DESIGN.md), a dedup check with match-confidence routing (`scripts/dedup_search.py` — ≥80% use-existing / 50-79% improve-existing / <50% create-new / compose), and an inline-vs-fork architecture guide with worked examples.
- **`scripts/validate.py`**: wraps the official `skills-ref` validator (verified directly against the real tool) plus a Claude-specific layer — reserved-word check, gerund-naming suggestion, extended-field classification, and path-reference existence checking. `--suggest-compatibility` auto-populates the `compatibility` field per target surface.
- **`references/surface-matrix.md`**: all five surfaces (Claude Code, Claude.ai, Cowork, Claude Tag, Messages API) plus the generic cross-vendor default, extended Claude Code frontmatter fields, and the plugins-cache-vs-source-path gotcha.
- **`scripts/security_scan.py`**: two-tier gitleaks (default gate) + pattern-checks (`--verbose`, educational layer) scanner, verified against a real gitleaks install — including the unsafe-command-interpolation check (row 38) and the blocking-interactive-input / no-documented-cli script-design checks. SHA256 content-hash tamper detection (`.security-scan-passed`, atomic write) blocks packaging on any post-scan edit. `.skillignore`-based packaging exclusion, enforced (not just documented) by `--package`.
- **`references/security-checklist.md`**, **`references/sanitization-checklist.md`** (the AI semantic read-through step, required of the author before publishing their own skill), and **`references/script-design.md`**.
- **`references/writing-philosophy.md`** and **`references/frontmatter-spec.md`**: imperative voice, explain-the-why, coherent-unit scoping, the three-tier degrees-of-freedom heuristic, content hygiene, and the canonical six-field frontmatter spec with the pushy+imperative description technique.
- Plugin manifest (`.claude-plugin/plugin.json`), plugin-root `.skillignore` and `.gitignore`. Verified against `claude plugin validate --strict`, which caught two real issues fixed before release: the `skills` field needed `"./"` (skill directories sit directly at plugin root, not nested under a `skills/` folder) rather than pointing at `creating-skills` itself, and `agents/*.md` needed proper `name`/`description` frontmatter — Claude Code auto-discovers a plugin's `agents/` directory as real invokable subagent definitions, not just reference prose, so `grader`/`comparator`/`analyzer` are now genuinely invocable via the Task tool's `subagent_type`, not only readable as instructions.

### Deliberately out of scope for v1 (not missed — see the master spec's release-split rationale)
- Row 14: lifecycle framing (capability-uplift vs. encoded-preference, timelessness scoring)
- Row 31: bulk/whole-library audit mode
- Row 32: contribute-back / auto-PR mode

All three ship in v2 (Stage 5-6, Prompt B), after v1 has been dogfooded on real skills.
