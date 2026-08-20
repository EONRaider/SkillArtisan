# Vendored repositories

Pinned, user-confirmed clones of external codebases vendored into this project for two
distinct purposes — kept in one file since they share a directory and the same pinning
discipline, split into sections below since the purposes differ. All cloned read-only;
none are modified in place.

## Comparison-arm repositories

Run as live comparison arms (arms 3 and 4 of the Best-in-Market Scorecard's 5 arms).

### `daymade-claude-code-skills/`

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

### `tripleyak-skillforge/`

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

#### Important finding: SkillForge v6 changed its rigor model from what the master spec describes

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

### Status

Both repos cloned and pinned 2026-08-16, user-confirmed. Dependency runnability confirmed
for both. Neither has been executed yet — that's Phase 3 (cross-arm orchestration
harness), which still needs its own separate confirmation before either codebase is
actually run as a live arm, per the plan's human-confirmation strategy.

## Audit-pilot source repositories

Real, published third-party skill corpora audited by `scripts/audit.py` via
`benchmark/audit-pilot/aggregate_findings.py` — see `../audit-pilot/README.md` for the
full pilot methodology. Two sources already done and fully documented in
`../audit-pilot/RESULTS.md`: `mattpocock-skills` (audited from the locally cached plugin
install, not vendored here — see `../audit-pilot/README.md`'s own "Sources and pins")
and `daymade-claude-code-skills` above (dual-purpose: comparison arm *and* audit-pilot
source — 92 skills audited in Phase 3, on top of the 13 used as `../corpus/` seeds).
Approved roadmap for further sources: `~/.claude/plans/home-eonraider-desktop-verified-candida-imperative-thompson.md`
(Phases 4–7).

### `mukul975-anthropic-cybersecurity-skills/`

- **Repo**: `https://github.com/mukul975/Anthropic-Cybersecurity-Skills`
- **Pinned commit**: `4c0b700ac5d280ba46695062077f0fe922ce3602` (`main` HEAD,
  2026-08-08T14:55:19Z) — chosen over the latest tagged release (`v1.3.0`,
  `101ca0bd887a295e39cc20a100efa571937ca969`, 2026-06-22) because `main` had grown past
  the tag by the time of pinning and this SHA's 817-skill count was directly verified
  live (GitHub tree API) before pinning, not assumed from the tag. **User-approved
  2026-08-20** as part of the Phases 4–7 plan (research request → independent
  re-verification → plan approval), not a separate one-off confirmation.
- **License**: Apache-2.0 — confirmed via GitHub's license-detection API (parses actual
  file content) at planning time; re-confirm by reading `LICENSE` directly if this pin
  is ever revisited far from 2026-08-20.
- **Structure**: flat `skills/<skill-name>/SKILL.md`, uniform depth, 817 of 817 real
  skill directories fully discoverable by the existing `find_skill_dirs` — no code change
  needed. Single deep domain (cybersecurity) with framework-mapped frontmatter (MITRE
  ATT&CK, NIST CSF, ATLAS, D3FEND, F3).
- **Caveat carried into the audit**: README states "an independent, community-created
  project... Not affiliated with Anthropic PBC" despite the repo name, and content is
  security-education material (attack techniques, dual-use tooling described for
  defensive/educational purposes) — audited exactly like any other skill (static
  text/pattern analysis only, `audit.py` never executes a skill's own bundled scripts),
  but expect a genuinely different false-positive profile than the first two corpora (see
  `../audit-pilot/RESULTS.md`'s Phase 4 section for what that turned out to be).
- **Runnability confirmed**: same Python-only dependency chain as the rest of `scripts/`;
  no repo-specific tooling needed to audit it (this is a read-only skill corpus, not a
  comparison-arm codebase with its own pipeline to run).

### `alirezarezvani-claude-skills/`

- **Repo**: `https://github.com/alirezarezvani/claude-skills`
- **Pinned commit**: `aa8d778811a557a2c28ccadda4cf3d0bd028a4cc` (`main` HEAD,
  2026-07-17T13:02:50Z) — reconfirmed live immediately before cloning (2026-08-20); `main`
  itself hasn't advanced since, though the repo's `pushed_at` is a month later (pushes
  landed on feature branches, not `main`). The research doc's recommended pin, tag
  `v2.11.2`, doesn't exist — the repo's own `CLAUDE.md` states that version number ahead
  of what's actually tagged. Latest real tag is `v2.9.0`
  (`0d78fd835a0136988f4df2fe75d1e6295b4ef4d7`); pinned to `main` HEAD instead since it's
  the freshest content and was independently recount-verified before pinning (below), not
  because the tag was rejected for cause.
- **License**: MIT — raw `LICENSE` file read directly, "Copyright (c) 2025 Alireza
  Rezvani."
- **Structure — corrected significantly from the planning-session estimate**: the repo
  packages some skills twice — once in a flat `<domain>/skills/<skill>/SKILL.md`
  collection, again as a self-contained mini-plugin one level deeper
  (`<domain>/<plugin>/skills/<skill>/SKILL.md`) — *and* symlink-mirrors every skill into
  four cross-tool directories (`.codex/`, `.gemini/`, `.hermes/`, `.vibe/`) for
  compatibility with other agent products. Both quirks required real fixes to
  `_common.find_skill_dirs` and a new content-hash dedup step in
  `aggregate_findings.py` — see `CHANGELOG.md`'s Phase 6 entry and
  `benchmark/audit-pilot/RESULTS.md` for the full story, including how the symlink issue
  was found (a raw skill-count discrepancy this same phase's own extra verification step
  surfaced) and why the true unique-skill count (**349**) is close to the repo's own
  self-reported "362," not the "~672" this project's own git-tree-API-based
  planning-session check had (wrongly) concluded — that check counted tracked symlink
  blobs as if they were real files, since it filtered by path suffix rather than git
  object mode.
- **Runnability confirmed**: same Python-only dependency chain as the rest of `scripts/`;
  no repo-specific tooling needed to audit it.

### `glebis-claude-skills/`

- **Repo**: `https://github.com/glebis/claude-skills`
- **Pinned commit**: `52fdf242981c415a723abca8447ad08a3eb1f857` (`main` HEAD,
  2026-08-19T20:59:32Z) — no tags exist upstream, same HEAD-SHA-pin convention as
  daymade. Reconfirmed live immediately before cloning (2026-08-20); unchanged since
  planning.
- **License**: MIT — raw `LICENSE` file read directly at planning time, standard text,
  "Copyright (c) 2025-2026 Gleb Kalinin." Re-confirm by reading the file directly if this
  pin is ever revisited far from 2026-08-20.
- **Structure**: mostly root-level (`<skill-name>/SKILL.md`, one directory per skill,
  103 top-level entries plus a `BUNDLES.md`), with a handful nested one level deeper
  (`confide/skills/<name>/SKILL.md`) — both shapes already covered by the existing
  `find_skill_dirs`. 111 skill directories discovered, matching the live GitHub tree API
  count from planning (not the "~85–100" the original research estimated).
- **Distinct from the first three sources**: solo maintainer (Gleb Kalinin, Berlin),
  knowledge-work/solopreneur focus — meeting/transcript pipelines, Obsidian tooling,
  personal analytics, coaching/therapy skills, some Russian-language content. A different
  authorship model and domain from mattpocock (single-author engineering), daymade
  (large, many-contributor, heterogeneous), and mukul975 (community security corpus).
- **Runnability confirmed**: same Python-only dependency chain as the rest of `scripts/`;
  no repo-specific tooling needed to audit it.
