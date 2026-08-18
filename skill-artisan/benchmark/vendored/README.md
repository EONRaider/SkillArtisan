# Vendored comparison-arm repositories

Pinned, user-confirmed clones of the two external codebases run as live comparison arms
(arms 3 and 4 of the Best-in-Market Scorecard's 5 arms). Both cloned read-only for local
execution during the benchmark; neither is modified in place.

## `daymade-claude-code-skills/`

- **Repo**: `https://github.com/daymade/claude-code-skills`
- **Pinned commit**: `d24f6d13f57688d8436b78647519f0ae49b37adf` ("chore(ci): upgrade GitHub
  Actions to Node 24 (#300)", 2026-08-17 01:59:05 +0800) — no tags exist upstream, so this
  is a HEAD-SHA pin. **User-confirmed 2026-08-16**, same commit already used to source 13
  of the 16 benchmark corpus entries (see `../corpus/README.md`).
- **Arm entry point**: `daymade-skill/skill-creator/` — daymade's own fork of Anthropic's
  `skill-creator`, explicitly stated in its frontmatter to supersede the official plugin.
  Ships its own full pipeline: `run_eval.py`, `aggregate_benchmark.py`,
  `improve_description.py`, `audit_skill_regression.py`, `package_skill.py`,
  `security_scan.py`. This is what Phase 3's harness should invoke to author/improve a
  skill from each corpus entry's `seed.md`, not the repo's other 68 pre-built skills
  (those were only a sourcing pool for the corpus itself).
- **Runnability confirmed**: its own documented blockers (`SKILL.md` line ~1202) are
  Python 3, `uv`, PyYAML, and gitleaks — all present on this machine (`uv` 0.9.7,
  `gitleaks` 8.21.2, Python 3.10.12, PyYAML importable). The `claude` CLI is only
  blocking when a verification tier runs live agent evals; also present.

## `tripleyak-skillforge/`

- **Repo**: `https://github.com/tripleyak/SkillForge`
- **Pinned tag**: `v6.0.0` — an annotated tag; the tag object's own SHA is
  `e1c99193158c188a96eb9b1d7139401a705bb5b7`, but the commit it actually points to is
  `ce70b56f77797ca288299b52ed7d487e6e195cbc` ("Merge skillforge-v6-roadmap: v6 rework").
  **Always check out by tag name (`git checkout v6.0.0`)**, not by the tag object's SHA,
  to avoid this ambiguity. **User-confirmed 2026-08-16** — `HEAD` was one commit ahead at
  survey time (README-only: adds release-history/audit links), so `v6.0.0` was chosen
  specifically as the actual tagged release surveyed, not latest `main`.
- **Arm entry point**: repo root `SKILL.md` (1,158 words) — SkillForge's own
  triage→analysis→spec→generate→review→ship pipeline (`scripts/*.py`).
- **Runnability confirmed**: README states Python 3.8+, stdlib only, PyYAML used if
  present. Python 3.10.12 present; PyYAML importable.

### Important finding: SkillForge v6 changed its rigor model from what the master spec describes

The master spec's Comparison Arms section frames SkillForge as *review-based* — "a panel
of subagents evaluates a generated skill against distinct criteria and must unanimously
approve it" — in contrast to `creating-skills`' *execution-based* with/without-skill delta.
That description matches SkillForge **v5** ("4-agent unanimous synthesis panel"). **v6
(2026-07-29, this pin) replaced the panel entirely** with the same RED-gate/GREEN-gate
structure `creating-skills` and `skill-creator` already use: a baseline (no-skill) run
before writing, a with-skill run after, and the behavioral delta between them is the
actual gate — backed by lint (`validate_skill.py`) plus **one** adversarial reviewer, not
a panel. Confirmed directly from the repo's own README changelog table, not inferred.

**Consequence for Phase 8's reporting**: the master spec's target-bar note — "report
SkillForge's panel-approval rate alongside this rather than treating it as directly
comparable" — was written against v5's architecture. v6 may now produce a genuinely
comparable task-success delta rather than a separately-reported panel-approval rate. This
needs to be verified directly against what v6's `run_skill_evals.py` actually outputs
before Phase 5/8, and the master spec's Comparison Arms section likely needs a dated
correction note once that's confirmed (matching this document's own pattern of correcting
earlier passes when a primary source is actually read) — flagged here so it isn't lost
before Phase 8.

## Status

Both repos cloned and pinned 2026-08-16, user-confirmed. Dependency runnability confirmed
for both. Neither has been executed yet — that's Phase 3 (cross-arm orchestration
harness), which still needs its own separate confirmation before either codebase is
actually run as a live arm, per the plan's human-confirmation strategy.
