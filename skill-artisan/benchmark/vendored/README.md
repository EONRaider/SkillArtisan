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

Approved Phase 8–14 roadmap for the skills.sh-sourced expansion:
`~/.claude/plans/i-maintain-skillartisan-a-velvety-possum.md`. First entries below.

### `anthropics-knowledge-work-plugins/`

- **Repo**: `https://github.com/anthropics/knowledge-work-plugins`
- **Pinned commit**: `6e2cf60a525763fcf54dfb4ce704a989f2b722c7` (`main` HEAD,
  2026-08-19T18:32:38Z) — fetched live immediately before cloning (2026-08-20).
- **License**: Apache-2.0 — raw `LICENSE` file read directly, standard text.
- **Structure — found a genuine `find_skill_dirs` coverage gap, fixed**: raw git-tree
  count (212) matched the candidates doc exactly, but local discovery initially found
  only 185. Root cause: `zoom-plugin`'s partner-built plugin nests platform/surface
  *sub-skills* one or two levels beneath an already-discovered skill directory
  (`.../skills/contact-center/android/SKILL.md`, `.../skills/meeting-sdk/web/client-view/SKILL.md`)
  — each a real, independently-frontmattered skill, explicitly routed to from the
  parent skill's own body text (`contact-center/SKILL.md` literally links
  `[android/SKILL.md](android/SKILL.md)`), not example or test content. Confirmed this
  pattern doesn't collide with two known false-positive shapes already present in
  other vendored corpora (`alirezarezvani`'s `assets/sample-skill/`, `skillforge`'s
  `tests/fixtures/sample-skill/`) before adding two new discovery patterns to
  `_common.find_skill_dirs`; regression tests in
  `tests/test_common_find_skill_dirs.py`. All 212 now discovered, 0 content-duplicate
  groups.
- **Also found via this repo, fixed in `validate.py`**: `check_path_references` had a
  fifth false-positive mechanism — link-syntax placeholders inside HTML comments
  (`<!-- ... "Watch the [intro](URL)..." -->`), a real authoring-note pattern found in
  a sibling repo, `anthropics-claude-for-legal` (see below), not this one. Documented
  here since the fix lives in the same shared check this repo's structural gap also
  touched.
- **Distinct from all prior sources**: first-party Anthropic content (specifically a
  named partner integration, Zoom), the first vendored corpus with a genuinely new
  metadata field — `triggers:` — used by every zoom-plugin skill and explicitly
  documented in the plugin's own `CONTRIBUTING.md` alongside two fields
  SkillArtisan's `validate.py` already recognizes (`argument-hint`,
  `user-invocable`) as equivalent-status optional frontmatter. Stronger evidence than
  the Phase 5/6 "bespoke one-off convention" characterization that originally kept
  `triggers` off `THIRD_PARTY_FIELD_FAMILIES` — not yet acted on, see `RESULTS.md`'s
  Phase 8 section and the tracked issue.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `anthropics-claude-for-legal/`

- **Repo**: `https://github.com/anthropics/claude-for-legal`
- **Pinned commit**: `4a6c651889c97cc9140580363c73e0eb17379c2b` (`main` HEAD,
  2026-07-23T00:46:01Z) — fetched live immediately before cloning (2026-08-20).
- **License**: Apache-2.0 — raw `LICENSE` file read directly, standard text.
- **Structure**: 151 skill directories discovered, exactly matching the candidates
  doc's raw git-tree count — no correction needed, one of the two Phase 8 repos where
  planning-session figures held exactly.
- **Distinct**: first-party Anthropic content, legal-workflow domain (litigation,
  commercial, AI-governance, regulatory, corporate, employment sub-domains). One
  colon-namespaced skill name found (`cocounsel-legal:deep-research`, under
  `external_plugins/` — a vendored third-party partner integration inside this repo,
  not this repo's own convention), flagged by `skills-ref` for invalid characters —
  real, low-volume (1 of 151), not escalated to a field-family decision.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `anthropics-financial-services/`

- **Repo**: `https://github.com/anthropics/financial-services`
- **Pinned commit**: `38652224c10610fa52eee2acee3ac712dcff01f2` (`main` HEAD,
  2026-08-04T14:41:29Z) — fetched live immediately before cloning (2026-08-20).
- **License**: Apache-2.0 — raw `LICENSE` file read directly, standard text.
- **Structure — a second genuine `find_skill_dirs` gap, fixed**: raw git-tree count
  (118) matched the candidates doc, but local discovery initially found only 1. Root
  cause: this repo wraps the already-supported `category/plugin/skills/<skill>`
  convention in one more top-level `plugins/` directory
  (`plugins/partner-built/spglobal/skills/earnings-preview/SKILL.md`) — 117 of 118
  skills live at exactly this depth. Fixed alongside the sub-skill gap above (same
  commit, same regression-test file). All 118 now structurally discovered.
- **Content-level dedup**: 51 of the 118 are byte-identical to another already-kept
  skill (31 duplicate-content groups) — this repo bundles shared utility skills
  (`audit-xls`, `xlsx-author`, `break-trace`, `gl-recon`, etc.) by value into
  multiple independently-installable plugins (e.g. `audit-xls` appears verbatim in 7
  separate plugins) so each plugin works standalone without depending on another
  being installed — a different provenance from `alirezarezvani`'s
  flat-vs-nested-install duplication, but the same *outcome* `dedup_by_content`
  (Phase 6) already handles correctly with no code change needed. **67 unique
  auditable skills** after dedup.
- **Distinct**: first-party Anthropic content, financial-services domain (equity
  research, IB, PE, wealth management, fund admin — vertical- and agent-plugin
  shaped). 4 of the audit pilot's `rebuild`-decision skills across this Phase 8 batch
  are technical SDK/model-reference docs from this repo and its sibling
  (`dcf-model` here; three Zoom platform-SDK docs in `knowledge-work-plugins`).
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `obra-superpowers/`

- **Repo**: `https://github.com/obra/superpowers`
- **Pinned tag**: `v6.3.0` (`b36e0829c6d0140e93cfef2ca599b1b07d4a7797`) — reconfirmed live
  immediately before cloning (2026-08-20); unchanged since planning.
- **License**: MIT — raw `LICENSE` file read directly, "Copyright (c) 2025 Jesse Vincent."
- **Structure**: uniform `skills/<name>/SKILL.md`, one repo-wide `skills/` collection, no
  nesting or dual-packaging quirks. 14 skill directories discovered locally, exactly
  matching both the planning-session figure and the live GitHub tree API count — the one
  source in this whole roadmap where the planning-session number needed no correction
  once actually checked against the clone (per the standing rule Phase 6 established: 1
  harmless symlink exists in the repo, `AGENTS.md -> CLAUDE.md`, unrelated to skill
  discovery).
- **Distinct from the other four sources**: company-backed (Jesse Vincent, Prime
  Radiant), the most-starred and most externally-contributed-to of any source in this
  roadmap, a mandatory-workflow-methodology framing rather than a reference/how-to one.
  Smallest and lowest-priority by design (14 skills, some overlap with mattpocock's
  engineering-workflow focus) — included for completeness of the approved roadmap, not
  because it was expected to be a major source of new findings.
- **Runnability confirmed**: same Python-only dependency chain as the rest of `scripts/`;
  no repo-specific tooling needed to audit it.

### `nvidia-skills/`

- **Repo**: `https://github.com/NVIDIA/skills`
- **Pinned commit**: `04bc65e17242d305ffb09c18d0ef0817505cc2c3` (`main` HEAD,
  2026-08-20T16:26:58Z) — fetched live immediately before cloning (2026-08-20).
- **License — dual, corrected from the candidates doc's single-label read**: source
  code under `LICENSE-APACHE` (Apache-2.0); **skill/documentation content itself
  under `LICENSE-CC-BY-4.0`** (permissive, attribution-only, no share-alike) — the
  repo's own README states this explicitly (`SPDX-License-Identifier: Apache-2.0 AND
  CC-BY-4.0`). The candidates doc's GitHub-API single-label check only surfaced
  Apache-2.0; both raw license files were read directly here. CC-BY-4.0 is
  meaningfully more permissive than `trailofbits/skills`' CC-BY-SA-4.0 (no
  copyleft/share-alike clause) — no policy carve-out needed for this repo the way one
  was recorded for trailofbits.
- **Structure**: 344 skill directories discovered, exactly matching the candidates
  doc's raw git-tree count — no correction needed. 1 content-duplicate group.
- **Distinct**: corporate-DevRel/product-sync authorship — the README states skills
  are "maintained in their respective product repos... and synced to this repo
  daily," a genuinely different maintenance model from every other source in this
  pilot (single-repo-authored, even when multi-contributor). Broad technical/hardware
  domain (Bedrock, DOCA/BlueField DPU, DeepStream, Omniverse, digital health,
  quantum computing). Surfaced two new coherent frontmatter field families
  (`owner`/`service`/`reviewed`, `tools`) and a genuine, reproducible authoring
  defect in the `doca-*` skill family's cross-references — see
  `../audit-pilot/RESULTS.md`'s Phase 9 section for both.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `forcedotcom-sf-skills/`

- **Repo**: `https://github.com/forcedotcom/sf-skills`
- **Pinned commit**: `94f1dbdb643245745ba2e5d5cd1b546514b780a7` (`main` HEAD,
  2026-08-18T17:18:08Z) — fetched live immediately before cloning (2026-08-20).
- **License**: Apache-2.0 — raw `LICENSE.txt` file read directly (non-standard
  filename, `.txt` suffix; content confirmed standard Apache-2.0 text,
  "Copyright (c) 2026 Salesforce, Inc.").
- **Structure**: 179 skill directories discovered, exactly matching the candidates
  doc's raw git-tree count — no correction needed. 29 content-duplicate groups (58 of
  179 skills) — the same flat-`skills/`-plus-self-contained-mini-plugin
  dual-packaging pattern first found in `alirezarezvani` (Phase 6), handled by the
  existing `dedup_by_content` with no code change. **150 unique auditable skills**
  after dedup.
- **Distinct**: first-party Salesforce content, Salesforce/OmniStudio/Agentforce
  platform domain. One notable finding: a 384-instance `security-gitleaks-clean`
  outlier (`omnistudio-epc-catalog-generate`) — confirmed as UUIDs used as Salesforce
  Vlocity record identifiers in a large product-catalog example dataset, not real
  secrets, the same confirmed-but-unfixable class from Phase 4/5 at unprecedented
  volume.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `aws-agent-toolkit-for-aws/`

- **Repo**: `https://github.com/aws/agent-toolkit-for-aws`
- **Pinned commit**: `4b8f1820ef4efa55bf3941191beec031f2681ae4` (`main` HEAD,
  2026-08-20T12:41:44Z) — fetched live immediately before cloning (2026-08-20).
- **License**: Apache-2.0 — raw `LICENSE` file read directly, standard text.
- **Structure — a third genuine `find_skill_dirs` gap, fixed**: raw git-tree count
  (151) matched the candidates doc, but local discovery initially found only 49. Root
  cause: a literal top-level `skills/` collection directory (not preceded by any
  wildcard, unlike every other pattern in `find_skill_dirs`) with two or three
  category levels of nesting beneath it before the skill's own directory
  (`skills/core-skills/amazon-bedrock/SKILL.md`,
  `skills/specialized-skills/database-skills/rds-db2/SKILL.md`) — 101 of the 102
  missing skills live at these two depths. Checked for collisions against every other
  vendored corpus before adding the two new patterns: zero matches anywhere else.
  Fixed; **150 of 151 now discovered**. The last skill
  (`plugins/aws-agents/skills/agents-pay/packages/openclaw/skills/agents-pay/SKILL.md`
  — a doubly-nested sub-package shape) is real content left as a documented, known
  gap rather than a fifth pattern justified by one example. Regression tests in
  `tests/test_common_find_skill_dirs.py`. 27 content-duplicate groups (54 of 150) —
  the same flat-`skills/`-plus-mini-plugin dual-packaging pattern as
  `forcedotcom-sf-skills` above and `alirezarezvani` (Phase 6): e.g.
  `plugins/aws-core/skills/amazon-bedrock` mirrors
  `skills/core-skills/amazon-bedrock` byte-for-byte. Handled by the existing
  `dedup_by_content` with no code change. **123 unique auditable skills** after
  dedup.
- **Distinct**: first-party AWS content, broad cloud-infrastructure domain across
  core and specialized categories (databases, networking, serverless, analytics,
  resilience, security). One `rebuild`-decision skill (`amazon-dynamodb`, 631 lines).
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `mims-harvard-tooluniverse/`

- **Repo**: `https://github.com/mims-harvard/ToolUniverse`
- **Pinned commit**: `1aaaf00d1a9a91c21ae09d014fe19bf46fa82917` (`main` HEAD,
  2026-08-20T03:21:03Z) — fetched live immediately before cloning (2026-08-20).
- **License**: Apache-2.0 — raw `LICENSE` file read directly, standard text.
- **Character-checked before cloning**: fetched a sample skill
  (`tooluniverse-admet-prediction`) via the GitHub API first, per the plan's specific
  flag for this repo — confirmed genuine, dense domain-expert content (real ADMET
  pharmacokinetics reasoning, tool-quirk caveats), not a mechanically-generated
  tool-registry stub. Proceeded to clone only after this passed.
- **Structure — a one-file count discrepancy, resolved (not a discovery gap)**: local
  discovery found 464, one short of the candidates doc's 465. Root cause:
  `skills/tooluniverse-cs-setup/templates/router_SKILL.md` — a real template file
  whose name merely *ends with* "SKILL.md" as a substring (`endswith()`, the check
  both the candidates doc's original verification and this project's own pre-vendor
  check used), not a file literally named `SKILL.md`. `find_skill_dirs`'s
  exact-filename glob patterns correctly never matched it — the tool's own discovery
  was right; the GitHub-API-based sizing check upstream of it has a real, now-fixed
  blind spot for future phases to watch for.
- **A genuine `find_skill_dirs` false positive, fixed**: `find_skill_dirs` *did*
  discover one real false positive —
  `skills/create-tooluniverse-skill/assets/skill_template/SKILL.md`, a
  fill-in-the-blanks skill-creation template (`name: tooluniverse-[domain-name]`),
  reachable by Phase 9's new `skills/*/*/*/SKILL.md` pattern even though it's bundled
  reference content. Same false-positive class first suspected in Phase 8
  (`alirezarezvani`'s `assets/sample-skill/`, `skillforge`'s
  `tests/fixtures/sample-skill/`), now confirmed a third time and reachable by a real
  pattern. Fixed with a general rule (exclude any match passing through a directory
  named `assets`, `tests`, or `fixtures`), justified by three confirmed instances
  across three corpora, checked against every vendored corpus before landing: exactly
  one real false positive fixed, zero legitimate discoveries excluded anywhere.
  Regression test added. **463 real skills discovered.**
- **Content-level dedup — three packaging layers, one pair diverged**: 136
  content-duplicate groups. Unusually, this repo ships **three** top-level copies of
  many skills (`skills/`, `plugin/skills/`, `plugins/tooluniverse/skills/`), not two
  — and 41 skill names have two *non-identical* surviving copies after
  `dedup_by_content` (which only ever collapses exact byte matches, by design).
  Investigated one (`tooluniverse-cancer-genomics-tcga`): `plugins/tooluniverse/`'s
  copy is missing a real `disable-model-invocation: true` field present in the other
  two — genuine content drift in the source repo (most plausibly a stale sync
  snapshot), not a SkillArtisan-side issue. Documented, not fixed — see
  `../audit-pilot/RESULTS.md`'s Phase 10 section. **327 unique auditable skills**
  after dedup.
- **Distinct**: academic/research authorship (Harvard Medical School's Zitnik Lab),
  the largest single repo in the roadmap, broad biomedical/scientific domain (drug
  discovery, genomics, clinical analysis, protein interpretation). Lowest hit rate of
  any corpus since mattpocock (30%), consistent with careful, expert-curated
  authorship.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `nomadamas-k-skill/`

- **Repo**: `https://github.com/NomaDamas/k-skill`
- **Pinned commit**: `1a6469192e2deb44de05b7fa462e27070f156b58` (`main` HEAD,
  2026-08-19T18:58:18Z) — fetched live immediately before cloning (2026-08-20).
- **License**: MIT — raw `LICENSE` file read directly, standard text (no named
  copyright holder, "Copyright (c) 2026" — still valid MIT text).
- **Structure**: 118 skill directories discovered, exactly matching the candidates
  doc's raw count. 0 content-duplicate groups, 0 symlinks, 0 errors.
- **Distinct**: the pilot's first non-English corpus (Korean, `locale: ko-KR` in
  every skill's `metadata` block) — included specifically for language/cultural
  diversity and to stress-test every text-pattern check's English assumptions. It
  found one real gap: `description-pushy-imperative` FAILs/WARNs 91 of 118 skills
  (77%), confirmed as a genuine English-bias problem (a literal-English-phrase regex
  plus a length threshold calibrated for English text density), not a real
  authoring-quality signal — see `../audit-pilot/RESULTS.md`'s Phase 11 section and
  tracked issue [#10](https://github.com/EONRaider/SkillArtisan/issues/10).
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `trailofbits-skills/`

- **Repo**: `https://github.com/trailofbits/skills`
- **Pinned commit**: `7be90d6e55e6b5e1607b519e97d0019b32b2656a` (`main` HEAD,
  2026-08-20T16:26:56Z) — fetched live immediately before cloning (2026-08-20).
- **License — CC-BY-SA-4.0, a real policy distinction from every other source in
  this roadmap**: raw `LICENSE` file read directly, confirmed ShareAlike, not a
  bare-permissive license like every other vendored corpus (MIT/Apache-2.0). Approved
  policy (see the Phase 8–14 roadmap plan): **audit yes, adapt no** — vendoring and
  auditing this corpus (reading + reporting findings, short attributed quotes) is not
  redistribution or adaptation, so it's treated exactly like any other corpus for
  audit purposes. The one standing restriction: never copy or adapt this repo's
  content into SkillArtisan's own shipped MIT-licensed material (corpus seeds, skill
  bodies, templates, docs beyond brief attributed quotes in `RESULTS.md`) — that's
  where ShareAlike would bite.
- **Structure**: 79 skill directories discovered, exactly matching the candidates
  doc's raw count. 0 content-duplicate groups, 0 errors. 2 harmless symlinks
  (`pip3 -> pip`, `python3 -> python`, shell shims in a plugin's `hooks/` directory)
  unrelated to skill discovery.
- **Distinct**: a named professional security-research firm (Trail of Bits), a
  useful contrast to `mukul975`'s community-authored cybersecurity corpus (Phase 4)
  — same domain character (confirmed-but-unfixable tutorial-token gitleaks findings,
  real risky-code patterns in reference material), different authorship model.
  Surfaced a genuine, exhaustively-verified sixth `path-references-exist` mechanism
  (a `{baseDir}` template-variable prefix, fixed by stripping rather than skipping —
  see `../audit-pilot/RESULTS.md`'s Phase 11 section) and a `type` field family
  corroboration (commented on
  [#9](https://github.com/EONRaider/SkillArtisan/issues/9)).
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `adobe-skills/`

- **Repo**: `https://github.com/adobe/skills`
- **Pinned commit**: `c94ebf018b19b4e075ccce1c15428c6f39dbedcd` (`main` HEAD,
  2026-08-20T17:28:52Z) — fetched live immediately before cloning (2026-08-20).
- **License**: Apache-2.0 — raw `LICENSE` file read directly, standard text.
- **Structure — a fourth genuine `find_skill_dirs` gap, fixed**: raw exact-filename
  tree count (162) exceeded the candidates doc's original figure (161) by one and
  local discovery initially found only 119. Root cause:
  `plugins/<product>/<version>/skills/<category>/<name>/SKILL.md` — one wildcard
  deeper on both sides of the literal `skills` component than the existing
  `*/*/skills/*/*/SKILL.md` pattern, e.g.
  `plugins/aem/6.5-lts/skills/aem-workflow/workflow-triaging/SKILL.md`. Checked for
  collisions against every vendored corpus before adding: zero matches anywhere
  else. Fixed — **162 of 162 now discovered**, 0 content-duplicate groups.
- **Distinct**: first-party vendor content (a named enterprise product line, Adobe
  Experience Manager, plus Workfront), two-tier product/version/category-umbrella
  structure (a category like `aem-workflow` is itself a skill with sub-skills
  beneath it) — explains an unusually high `no-human-docs-in-skill-dir` count (56)
  as a genuine structural consequence, not a check anomaly. One genuine, undocumented
  `path-references-exist` false positive (`code-review`'s literal
  `url-or-embedded-image` placeholder in unfenced checklist prose) left unfixed —
  no safe general pattern, see `../audit-pilot/RESULTS.md`'s Phase 12 section.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `google-skills/`

- **Repo**: `https://github.com/google/skills`
- **Pinned commit**: `3e9cfe3744226e78f289f827f53d4943fb6bf16e` (`main` HEAD,
  2026-08-20T18:08:34Z) — fetched live immediately before cloning (2026-08-20).
- **License**: Apache-2.0 — raw `LICENSE` file read directly, standard text.
- **Structure**: 111 skill directories discovered, exactly matching the candidates
  doc's raw count — no correction needed. 0 content-duplicate groups, 0 errors.
- **Distinct**: first-party Google vendor content. No corpus-specific findings
  beyond already-established, sampled-and-confirmed check categories shared across
  this phase's whole vendor-wave-2 batch.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `dotnet-skills/`

- **Repo**: `https://github.com/dotnet/skills`
- **Pinned commit**: `ab761ad27acdf2751d97a3c4439182a6721f2631` (`main` HEAD,
  2026-08-19T17:41:47Z) — fetched live immediately before cloning (2026-08-20).
- **License**: MIT — raw `LICENSE` file read directly, ".NET Foundation and
  Contributors."
- **Structure — a discrepancy that turned out to be the Phase 10 fix working
  correctly, not a new gap**: raw exact-filename tree count (106) matched the
  candidates doc; local discovery initially found 104. The missing 2
  (`eng/skill-validator/tests/fixtures/{no-eval-skill,sample-skill}/SKILL.md`) are
  real test fixtures for this repo's own skill-validator tooling, correctly
  excluded by the `assets`/`tests`/`fixtures` intermediate-directory rule added in
  Phase 10 for `mims-harvard/tooluniverse` — confirms that fix generalizes across
  corpora rather than being a one-off patch. **104 is the correct, final count.**
  0 content-duplicate groups.
- **Distinct**: first-party Microsoft/.NET Foundation content, real production
  first-party tooling context (its own `eng/skill-validator` — a dotnet-authored
  SKILL.md linter, structurally analogous to SkillArtisan's own validator). One
  genuine, real broken reference found in `authoring-github-workflows`
  (`agentic-workflows.agent.md` referenced, but the real file is
  `agentic-workflows.md`) — a true positive, not a check mechanism issue.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `grafana-skills/`

- **Repo**: `https://github.com/grafana/skills`
- **Pinned commit**: `51d33e71e191b409bbd25fc7be2684c610d18166` (`main` HEAD,
  2026-08-18T08:38:56Z) — fetched live immediately before cloning (2026-08-20).
- **License**: Apache-2.0 — raw `LICENSE` file read directly, standard text.
- **Structure**: 51 skill directories discovered, exactly matching the candidates
  doc's raw count — no correction needed. 0 content-duplicate groups, 0 errors.
- **Distinct**: first-party Grafana Labs content (LGTM stack — Loki, Grafana,
  Tempo, Mimir — plus k6, Pyroscope). One genuine, real broken reference found in
  `loki` (three referenced files — `logql.md`, `configuration.md`, `send-data.md`
  — confirmed via whole-repo search not to exist anywhere) — a true positive, a
  real content gap in the source repo. One deliberate scaffold-template skill
  (`name: your-skill-name` in a directory named `template`) correctly flagged by
  `frontmatter-valid`, not a real skill's own identity.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `flutter-agent-plugins/`

- **Repo**: `https://github.com/flutter/agent-plugins`
- **Pinned commit**: `1e5696a2e986345f7ecc92842b5e9293bc079d6f` (`main` HEAD,
  2026-08-20T18:33:03Z) — fetched live immediately before cloning (2026-08-20).
- **License**: BSD-3-Clause — raw `LICENSE` file read directly, "Copyright 2026
  The Flutter Authors."
- **Structure — a fifth exclusion-worthy intermediate directory, fixed**: raw
  exact-filename tree count (38) matched the candidates doc; local discovery
  initially found all 38 structurally, but 2 were real false positives:
  `tool/dart_skills_lint/example/skills/{valid,invalid}/SKILL.md` — deliberate test
  fixtures for the repo's own SKILL.md linter, both explicitly self-described as
  fixtures in their own body text and both carrying `metadata: {internal: true}`.
  Checked across every corpus audited so far before adding `example` to
  `find_skill_dirs`' intermediate-directory exclusion set: these two are the only
  matches anywhere. Fixed — **36 real skills discovered**, 0 content-duplicate
  groups.
- **Distinct**: first-party Google/Flutter content, dev-tooling domain (Dart/Flutter
  CLI workflows, its own skill-linter's dogfooded skills). Smallest vendor-cluster
  repo by real skill count.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `secondsky-claude-skills/`

- **Repo**: `https://github.com/secondsky/claude-skills`
- **Pinned commit**: `ad16332a30363b7cc13aa97baac3edeb8c9cc558` (`main` HEAD,
  2026-08-20T08:18:21Z) — fetched live immediately before cloning (2026-08-20).
- **License**: MIT — raw `LICENSE` file read directly, "Claude Skills Maintainers."
- **Structure**: 187 skill directories discovered, exactly matching the candidates
  doc's raw count — no correction needed. 0 content-duplicate groups, 0 errors.
- **Distinct**: dev-tooling cluster (largest of the trimmed set) — Cloudflare, React,
  WooCommerce, and general web/JS toolchain domain. Two genuine, reproducible broken
  cross-references found in its own content (`gemini-cli`, `woocommerce-code-review`
  — the latter assumes a packaging depth that doesn't match reality; see
  `../audit-pilot/RESULTS.md`'s Phase 13 section), not check mechanism issues.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `bobmatnyc-claude-mpm-skills/`

- **Repo**: `https://github.com/bobmatnyc/claude-mpm-skills`
- **Pinned commit**: `718070a7d622921b01687799a1f9613f36c6f615` (`main` HEAD,
  2026-07-18T19:16:51Z) — fetched live immediately before cloning (2026-08-20).
- **License**: MIT — raw `LICENSE` file read directly, "Claude MPM Contributors."
- **Structure — the corpus that broke `find_skill_dirs`' fixed-pattern-list model,
  in a good way**: raw tree count (174) matched the candidates doc; local discovery
  *with the pre-Phase-13 pattern list* found only 2. Root cause: plain category
  nesting at arbitrary depth (`universal/security/threat-modeling/SKILL.md`,
  `toolchains/php/frameworks/wordpress/wordpress-security-validation/SKILL.md`) with
  no `skills/` marker directory anywhere — a shape no finite list of fixed-depth
  patterns can cover. Triggered a full architectural replacement of
  `find_skill_dirs` with a bounded recursive walk, verified safe against all 19
  corpora already vendored (identical results everywhere except two confirmed
  improvements) and measurably faster — see `../audit-pilot/RESULTS.md`'s Phase 13
  section for the full account. **174 of 174 now discovered**, 0 content-duplicate
  groups.
- **Distinct**: dev-tooling cluster, a distinct progressive-loading/toolchain-detection
  architecture (its own name, "claude-mpm," suggests a managed skill-authoring
  pipeline) — confirmed via a coherent, whole-corpus frontmatter field family
  (`progressive_disclosure` and six sibling fields, 174/174 FAILing
  `frontmatter-valid` on it) and an explicit, deliberate multi-tier
  context-management design (declared `token_estimate` targets) that produces a
  genuinely higher `rebuild`-decision rate under SkillArtisan's own body-size
  heuristic — a real design-philosophy difference, not a bug on either side.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `kostja94-marketing-skills/`

- **Repo**: `https://github.com/kostja94/marketing-skills`
- **Pinned commit**: `70987bad4ebe9dce1f74858c1c64f3f8810f18e4` (`main` HEAD,
  2026-06-09T05:13:06Z) — fetched live immediately before cloning (2026-08-20).
- **License**: MIT — raw `LICENSE` file read directly, "kostja94."
- **Structure**: 172 skill directories discovered, exactly matching the candidates
  doc's raw count — no correction needed. 0 content-duplicate groups, 0 errors,
  clean under the recursive `find_skill_dirs`.
- **Distinct**: marketing domain (largest of the trimmed cluster). The
  highest-volume single-corpus instance of the directory/skill-name-mismatch
  packaging defect in the whole pilot (100 of 172, 58%) — confirmed as a real,
  consistent authoring convention (short internal directory names, full
  descriptive frontmatter names), not scattered mistakes. Also a second confirmed
  instance of Phase 12's undocumented, unfixable `path-references-exist` false
  positive (`[Source](url)`, live-prose placeholder) and one genuine broken
  cross-reference (`website-structure`, off-by-one-level). See
  `../audit-pilot/RESULTS.md`'s Phase 14 section.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `refoundai-lenny-skills/`

- **Repo**: `https://github.com/RefoundAI/lenny-skills`
- **Pinned commit**: `13598cc54e09399bc1bc1398b0fca284110efb2f` (`main` HEAD,
  2026-07-15T21:06:41Z) — fetched live immediately before cloning (2026-08-20).
- **License**: MIT — raw `LICENSE` file read directly, "Refound AI."
- **Structure**: 76 skill directories discovered, exactly matching the candidates
  doc's raw count — no correction needed. 0 content-duplicate groups, 0 errors.
- **Distinct**: PM domain, content sourced from a named podcast (Lenny's Podcast)
  — a genuinely different provenance character from any other corpus in the
  pilot (skills built from a named third party's interview material, not
  organically authored technical documentation). The pilot's highest-ever
  `description-pushy-imperative` rate (76 of 76, 100%) — confirmed as a genuine,
  consistent authoring-style difference (plain declarative capability statements
  throughout, no trigger framing under any phrasing), not an equivalent-phrasing
  gap.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

### `yaklang-hack-skills/`

- **Repo**: `https://github.com/yaklang/hack-skills`
- **Pinned commit**: `c9a4b9ee8645eb60763eb4eef172f1ecb0a5b3e8` (`main` HEAD,
  2026-06-16T16:11:43Z) — fetched live immediately before cloning (2026-08-20).
- **License**: MIT — raw `LICENSE` file read directly, "VillanCh."
- **Structure**: 102 skill directories discovered, exactly matching the
  candidates doc's raw count — no correction needed. 0 content-duplicate groups,
  0 errors.
- **Distinct**: offensive-security domain (a third security-adjacent corpus
  alongside `mukul975` and `trailofbits`, distinct sub-domain — web/network
  attack techniques rather than mukul975's broader cybersecurity-education scope
  or trailofbits' vulnerability-research tooling). All security-adjacent findings
  (gitleaks JWT examples, dangerous-code-pattern in offensive tooling, real
  Windows-native attack-technique syntax) matched already-established,
  confirmed-genuine classes — no new mechanism.
- **Runnability confirmed**: same Python-only dependency chain as the rest of
  `scripts/`; no repo-specific tooling needed to audit it.

## Phase 15 pilot cohort: 28 low-sitemap-count repos (deliberately lower-quality population)

One shared entry for the whole cohort — 28 repos vendored at once for the Phase 15
pilot (see `../audit-pilot/RESULTS.md`'s Phase 15 section for the full methodology
and findings). Selection: a fresh `skills.sh` sitemap crawl (2026-08-20, 20,000 URLs,
2,445 owner/repo pairs), all 25 held repos excluded, restricted to the
1–3-sitemap-listed-skills tier (1,730 candidates), license/star pre-screened via
batched GraphQL (18 calls), then a seeded random draw (`random.Random(15)`)
stratified across four star bins (8/8/6/6 from 0–2★ / 3–49★ / 50–499★ / ≥500★),
excluding only literal aggregator/awesome-list-shaped repos, forks, and empty repos.
All pins fetched live at clone time (2026-08-20); every LICENSE file read raw from
the actual clone; zero exact-content duplicates against any held corpus (all 980
pilot SKILL.mds hashed against all 4,386 held ones).

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `0xindiebruh/openclaw-mission-control-skill` | `3a0257c39e84` | 2026-02-07 | MIT | 1 | 1 | 0 |
| `5dive-ai/skills` | `5c1a075f1cba` | 2026-08-20 | MIT | 14 | 3 | 1 |
| `agentix-cloud/skills` | `9c768f4677a2` | 2026-03-21 | MIT | 1 | 1 | 0 |
| `apetta/agent-xlsx` | `5656a77e7e6b` | 2026-02-25 | Apache-2.0 | 1 | 1 | 8 |
| `byheaven/byheaven-skills` | `ca5bb493c4dc` | 2026-08-01 | MIT | 2 | 1 | 2 |
| `claude-dev-suite/claude-dev-suite` | `feb48b75aef7` | 2026-07-17 | MIT | 717 | 1 | 28 |
| `daytona/skills` | `ad4d8e088582` | 2026-08-18 | Apache-2.0 | 1 | 1 | 12 |
| `delexw/claude-code-misc` | `c729be07588f` | 2026-03-28 | MIT | 9 | 1 | 1 |
| `dnvriend/pdf-to-pptx-tool` | `8f5ff116b07b` | 2025-12-05 | MIT | 1 | 1 | 2 |
| `dominikmartn/nothing-design-skill` | `74affbb786af` | 2026-04-01 | MIT | 1 | 1 | 2,738 |
| `ecomfe/tempad-dev` | `7cfcb877d673` | 2026-07-21 | MIT | 2 | 1 | 492 |
| `fredm00n/framerlabs` | `3f51e5c9ac52` | 2026-07-13 | MIT | 2 | 1 | 134 |
| `hardhackerlabs/podwise-cli` | `496ee3a1fefa` | 2026-05-31 | MIT | 1 | 1 | 406 |
| `heroui-inc/heroui` | `7b33a66ab687` | 2026-08-19 | Apache-2.0 | 3 | 3 | 30,421 |
| `htmlstreamofficial/preline` | `1cd96367fea9` | 2026-05-10 | MIT (dual)* | 1 | 1 | 6,389 |
| `hueyexe/opencode-ensemble` | `5cb44fa16cde` | 2026-08-15 | MIT | 1 | 1 | 202 |
| `jackal092927/obsidian-official-cli-skills` | `ab6533943454` | 2026-02-13 | MIT | 1 | 1 | 39 |
| `jetbrains/go-modern-guidelines` | `40781f167719` | 2026-08-19 | Apache-2.0 | 1 | 1 | 816 |
| `kkoppenhaver/cc-nano-banana` | `3b136993b121` | 2026-02-18 | MIT | 1 | 1 | 366 |
| `lucifer1004/claude-skill-typst` | `4779c8e8b7bb` | 2026-08-17 | MIT | 1 | 1 | 119 |
| `nangohq/skills` | `496985d6fdc3` | 2026-08-20 | Elastic-2.0* | 8 | 1 | 2 |
| `naoterumaker/openclaw-gog-skills` | `4d089b1a2564` | 2026-02-16 | MIT | 9 | 2 | 4 |
| `nickcrew/claude-cortex` | `bb47af79ad3b` | 2026-06-28 | MIT | 156 | 3 | 34 |
| `one-box-u/openclaw-daily-hot-news` | `93aa62ab874c` | 2026-02-06 | MIT | 1 | 1 | 13 |
| `shoootyou/get-shit-done-multi` | `ec87275278ca` | 2026-03-20 | MIT | 34 | 1 | 22 |
| `vercel-labs/dev3000` | `5abe4f5cab00` | 2026-07-31 | MIT | 3 | 1 | 1,564 |
| `wihy/hermes-agent-skill` | `02d238da2eaa` | 2026-04-12 | MIT-0 | 1 | 1 | 0 |
| `yamadashy/repomix` | `c898ff0b3612` | 2026-08-19 | MIT | 6 | 2 | 27,979 |

**License notes (the two `*` rows, both resolved by raw read, plus the NOASSERTION
screen results):**

- `nangohq/skills` — **Elastic License 2.0 (ELv2)**, source-available, not
  OSI-approved. Same standing policy as `trailofbits-skills/`'s CC-BY-SA call:
  vendoring is a local clone only (not redistribution) and auditing (reading +
  reporting findings with short attributed quotes) is fine, but **never copy or
  adapt its content into SkillArtisan's shipped MIT-licensed material**.
- `htmlstreamofficial/preline` — dual-licensed "MIT and Preline UI Fair Use
  License"; the MIT arm covers auditing outright.
- Both were the cohort's two NOASSERTION screen results; both resolved favorably
  on raw read, consistent with the original top-44 screening's NOASSERTION
  experience.

**Structure notes (the discrepancy rows — sitemap counts are a floor, proven here
at a new extreme):**

- `claude-dev-suite/claude-dev-suite` — **717 skills found vs. 1 sitemap-listed**,
  the worst sitemap undercount ever observed in this pilot (tooluniverse's 7x was
  the prior record; this is 717x). A real, domain-organized dedicated suite
  (`skills/<domain>/<skill>/`), not an aggregator: median 833 words/skill, real
  per-domain content. 15 of its 717 skills have no YAML frontmatter at all
  (structured "USE WHEN:" blockquotes instead) — each errored individually per
  `audit.py`'s documented exit-code-4 contract, batch unaffected.
- `nickcrew/claude-cortex` — 156 found vs. 3 listed. Personal mega-collection;
  **bundles adapted copies of at least 4 obra/superpowers skills**
  (`brainstorming`, `systematic-debugging`, `using-git-worktrees`,
  `writing-skills` — `/Users/jesse` still present in one), modified enough that
  exact-content hashing doesn't match the held `obra-superpowers/` copies.
  Documented as near-duplicate adjacency, not excluded (obra is MIT).
- `shoootyou/get-shit-done-multi` — 34 found vs. 1 listed; per-platform variant
  packaging (`templates/skills/<name>/{claude,codex,copilot}`) of the "Get Shit
  Done" workflow system, re-uploaded rather than forked (GitHub `isFork` false).
- `5dive-ai/skills` — 14 found vs. 3 listed. **Two of its skills carry
  `evals/evals.json` files in the Anthropic/daymade skill-creator lineage schema**
  — the trigger for this phase's one real bug fix (see RESULTS.md Phase 15).
- `ecomfe/tempad-dev` — 2 found, 1 exact-content duplicate skipped by
  `dedup_by_content` (the only dedup hit in the whole cohort).

**Distinct**: the first cohort sourced from the population the original top-44
screening deliberately excluded — real projects' incidental skills (heroui,
repomix, preline, dev3000, jetbrains, daytona: 6 repos ≥500★ whose skill is a
bolt-on to a larger product) alongside near-zero-star solo repos, per the approved
Phase 15 plan. Also the pilot's first OpenClaw-ecosystem skills (4 repos) and
first Elastic-licensed corpus.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 16 cohort: 28 more low-sitemap-count repos (scale batch 2)

Second batch of the low-quality-cohort methodology, drawn 2026-08-21 after the user
approved scaling past the Phase 15 pilot. Same funnel, re-run fresh end to end
(the Phase 15 screen data was scratchpad-local and the sitemap regenerates):
20,000 URLs → 2,449 owner/repo pairs → 54 held repos excluded (25 original + the
28-repo Phase 15 cohort + `tripleyak`) → 1,704 in the 1–3-listed tier → 18-call
GraphQL screen → same exclusions (41 aggregator-shaped, 10 forks) → seeded
stratified draw (`random.Random(16)`, 8/8/6/6 across 0–2★/3–49★/50–499★/≥500★).
28 of 28 cloned, pinned, licenses read raw — 100% survival again. Zero exact
duplicates against the 5,366 held skills.

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `aaronvanston/skills-presentations` | `b133d724fbed` | 2026-02-19 | MIT | 5 | 1 | 10 |
| `agentchengfeng/best-minds` | `bcc2c829fde5` | 2026-01-07 | MIT | 1 | 1 | 103 |
| `aitytech/agentkits-marketing` | `e1d08b668997` | 2026-07-16 | MIT* | 32 | 1 | 585 |
| `andy-spike/skills` | `2737eadc3b88` | 2026-03-21 | MIT | 2 | 1 | 1 |
| `chaterm/terminal-skills` | `464c2954287a` | 2026-03-03 | Apache-2.0 | 63 | 2 | 57 |
| `cline/cline` | `fb60f9e5fdb1` | 2026-08-20 | Apache-2.0 | 8 | 1 | 66,586 |
| `fluxcd/agent-skills` | `dc7d150f3355` | 2026-08-19 | Apache-2.0 | 6 | 3 | 209 |
| `gabberflast/academic-pptx-skill` | `9f2b703ffe8d` | 2026-07-14 | MIT | 1 | 1 | 781 |
| `httprunner/skills` | `a2f2c13619bd` | 2026-02-28 | MIT | 8 | 1 | 2 |
| `iart-ai/tiktok-video-skills` | `2a775336b5a6` | 2026-06-22 | MIT | 4 | 3 | 7 |
| `jazzychad/ios-code-audit` | `34edb296a150` | 2026-05-21 | MIT | 1 | 1 | 33 |
| `joeseesun/yt-search-download` | `2b10938978b4` | 2026-03-06 | MIT | 1 | 1 | 116 |
| `kelos-dev/agora` | `2f3ddaba7be7` | 2026-07-07 | Apache-2.0 | 1 | 1 | 1 |
| `kochetkov-ma/claude-brewcode` | `421113f661b2` | 2026-08-16 | MIT (raw) | 54 | 3 | 31 |
| `lukastk/boxyard` | `9f63bc168401` | 2026-08-13 | MIT | 1 | 1 | 0 |
| `mave99a/novel-skill` | `0eadccbeb1fb` | 2026-01-07 | MIT | 1 | 1 | 12 |
| `meitu/meitu-skills` | `20631793691d` | 2026-07-14 | MIT | 56 | 1 | 30 |
| `memtensor/memos-cloud-skill` | `b1007f74d431` | 2026-06-26 | Apache-2.0 | 2 | 1 | 1 |
| `neondatabase/postgres-skills` | `f96c51d43518` | 2026-07-26 | Apache-2.0 | 2 | 1 | 25 |
| `ngmeyer/skills` | `701dfb8bd2ff` | 2026-06-21 | MIT | 10 | 1 | 2 |
| `pixel-process-ug/superkit-agents` | `cc7fcb7e47bc` | 2026-03-16 | MIT | 64 | 1 | 1 |
| `randroids-dojo/skills` | `37d0f88cf8d2` | 2026-08-12 | MIT | 10 | 1 | 46 |
| `s1dashu/ip-as-logo-skill` | `b1bf517c54a4` | 2026-08-20 | MIT | 1 | 1 | 3,351 |
| `sanity-io/next-sanity` | `1df99999db35` | 2026-08-20 | MIT | 12 | 1 | 950 |
| `theplannerivan/planners-ppt-hell` | `1745d6e25ef7` | 2026-08-04 | AGPL-3.0* | 1 | 1 | 225 |
| `yfe404/web-scraper` | `40ef9f8c45d4` | 2026-03-18 | MIT | 1 | 1 | 86 |
| `youmind-openlab/ai-image-prompts-skill` | `de38e2a6f5ec` | 2026-08-21 | MIT | 1 | 1 | 679 |
| `zavudev/zavu-skills` | `07542ba49cf9` | 2026-08-20 | Apache-2.0 | 13 | 2 | 1 |

**License notes (`*` rows):**

- `theplannerivan/planners-ppt-hell` — **AGPL-3.0**. Same audit-only posture as the
  ELv2 and CC-BY-SA precedents: local clone + reading/reporting is fine; **never
  copy or adapt its content into SkillArtisan's shipped MIT-licensed material**.
- `aitytech/agentkits-marketing` — repo LICENSE is MIT, but its four
  `document-skills/*` skills (docx/pdf/pptx/xlsx) are **redistributed copies of
  Anthropic's proprietary document skills**, shipping Anthropic's own
  "© 2025 Anthropic, PBC. All rights reserved." `LICENSE.txt` verbatim while the
  frontmatter rebrands them ("brand: AgentKits Marketing by AityTech"). Treat
  those four directories as Anthropic-proprietary content: audit-only, never
  adapt. The provenance finding itself is documented in RESULTS.md Phase 16.
- `kochetkov-ma/claude-brewcode` — GitHub API says NOASSERTION; raw read: MIT.

**Structure notes:**

- Five hidden collections ≥30 skills (`superkit-agents` 64, `chaterm` 63, `meitu`
  56, `brewcode` 54→43 post-dedup, `aitytech` 32) — Phase 15's "~1 in 10 repos in
  this tier is a hidden collection" prediction underestimated: here it's 5 of 28,
  though all far smaller than Phase 15's 717-skill outlier. All audited fully per
  the Phase 15 decision rule (each well under the 200-skill chunking threshold).
- `kochetkov-ma/claude-brewcode`: 11 exact-content duplicates skipped by
  `dedup_by_content` (platform-variant packaging).
- `meitu/meitu-skills`: ships a generated top-level `SKILL.md` that is a package
  release-notes manifest, not a skill (no frontmatter) — the phase's single
  per-skill error, correct exit-code-4 behavior.
- `fluxcd/agent-skills`: CNCF project whose own eval methodology independently
  converged on this pipeline's exact `evals.json` schema (including
  `expectations`) — the trigger for audit-gap issue #11.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 17 cohort: 27 more low-sitemap-count repos (scale batch 3) — one repo rejected on license

Third batch, drawn 2026-08-21 (seed 17). Funnel: 2,448 sitemap pairs → 82 held
excluded (25 original + 28 Phase 15 + 28 Phase 16 + tripleyak) → 1,674-repo tier →
17-call GraphQL screen (zero failures) → same aggregator/fork exclusions → seeded
stratified draw (8/8/6/6). **28 drawn, 27 vendored — the pilot's first license
rejection.**

`ykdojo/claude-code-tips` (9,829★) screened as NOASSERTION and was cloned for the
standard raw-file read per the established discipline — but unlike every prior
NOASSERTION case in this pilot (all ~15+ resolved favorably), its raw `LICENSE`
reads: *"Copyright (c) YK Sugi. All Rights Reserved."* followed only by a clause
granting the **author** rights over contributor PRs — no grant of any right to
use, copy, or audit the content back to the public. Functionally equivalent to no
license at all. **Dropped, not vendored** — its clone was deleted, not counted
toward this phase's totals, per the pilot's own standing license bar ("exactly as
strict as the original 44's screening," Phase 15 plan). First real rejection this
funnel has produced; every case before this was NOASSERTION resolving in the
repo's favor. No replacement drawn — 27 audited is the honest batch size.

**27 of 27 remaining cloned, pinned, licenses read raw — 100% survival on the
license-viable set.** Zero exact duplicates against the 5,728 held skills
(pre-rejection candidate pool). One repo carries a new license type for this
pilot: `wolke/bazi-mingli` — **CC BY-NC-SA 4.0** (NonCommercial, on top of the
ShareAlike restriction already seen at trailofbits). Same audit-only posture as
every prior copyleft/restrictive case: local clone + reading/reporting is fine
(SkillArtisan itself isn't commercial, and nothing here is redistributed);
**never copy or adapt into shipped MIT-licensed material.**

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `agentspace-so/agent-skills` | `18d61002379d` | 2026-04-28 | MIT | 1 | 1 | 15 |
| `anysearch-ai/anysearch-skill` | `4d6cef918e93` | 2026-08-21 | Apache-2.0 | 1 | 1 | 5,810 |
| `blitzreels/agent-skills` | `f07e9dd26fa3` | 2026-08-20 | MIT | 5 | 1 | 2 |
| `ccheney/robust-skills` | `0ace9a7f5c20` | 2026-08-14 | MIT | 10 | 3 | 57 |
| `chainbase-labs/agentkey` | `efc28096918b` | 2026-08-14 | Apache-2.0 | 1 | 1 | 591 |
| `cklxx/elephant.ai` | `bc94628f41b7` | 2026-03-23 | MIT | 30 | 1 | 11 |
| `cloudflare/kumo` | `e16b8ccfbcce` | 2026-08-20 | MIT | 2 | 1 | 3,429 |
| `decebals/claude-code-java` | `f81fbd2adb38` | 2026-02-08 | MIT | 18 | 1 | 712 |
| `edgesparkhq/agent-skills` | `d2745b1f5857` | 2026-05-15 | MIT | 2 | 2 | 1 |
| `kesslerio/academic-deep-research-clawhub-skill` | `3d422ce3544e` | 2026-07-29 | Apache-2.0 | 1 | 1 | 19 |
| `kimyx0207/kim_service` | `d218f4b50cb9` | 2026-08-13 | MIT | 9 | 1 | 163 |
| `konata9/chinese-lottery-predict-skills` | `a02057a5440c` | 2026-07-28 | MIT | 1 | 1 | 28 |
| `lngu/openclaw-skill-freeunlimited-websearch` | `3db7656c49b5` | 2026-02-20 | MIT | 1 | 1 | 2 |
| `manojbajaj95/agent-knowledge-cards` | `2089f142cbc0` | 2026-08-20 | MIT | 1 | 1 | 4 |
| `mitsuhiko/gh-issue-sync` | `955fe4c48653` | 2026-03-31 | Apache-2.0 | 1 | 1 | 160 |
| `narumiruna/telegram-bot` | `3d6862152131` | 2026-08-21 | MIT | 1 | 1 | 1 |
| `paymog/groundcover-cli` | `456ed7234e18` | 2026-08-18 | MIT | 1 | 1 | 1 |
| `praveenspeaks/cinematic-script-writer` | `f84f7d24814b` | 2026-02-10 | MIT | 2 | 1 | 1 |
| `qodo-ai/qodo-skills` | `357492caaaf3` | 2026-08-11 | MIT | 2 | 2 | 48 |
| `reviewstage/stage-cli` | `eabf305a30a3` | 2026-08-11 | MIT | 9 | 1 | 263 |
| `satya-janghu/agent-skills` | `24b06ad34ef7` | 2026-04-28 | MIT | 1 | 1 | 4 |
| `sebastian-software/effective-print-design` | `d9d97a58acc9` | 2026-02-12 | MIT | 1 | 1 | 0 |
| `snyk/studio-recipes` | `465f842b78f7` | 2026-08-20 | Apache-2.0 | 9 | 1 | 58 |
| `wolke/bazi-mingli` | `b53b4b875a87` | 2026-01-23 | CC-BY-NC-SA-4.0* | 1 | 1 | 62 |
| `xiaomingx/moltbot-connector-feishu-dingtalk` | `9dcac5e6a90e` | 2026-01-30 | Apache-2.0 | 4 | 1 | 7 |
| `yejinlei/web-search-skill` | `00b2ab6b694f` | 2026-03-03 | MIT | 1 | 1 | 2 |
| `zereight/gitlab-mcp` | `182ac8232843` | 2026-08-20 | MIT | 23 | 1 | 1,908 |

**Structure notes:**

- `cklxx/elephant.ai` (30 found vs. 1 listed) and `zereight/gitlab-mcp` (23 vs. 1)
  are this phase's hidden collections — both well under the 200-skill chunking
  threshold, audited in full.
- `xiaomingx/moltbot-connector-feishu-dingtalk`: 2 exact-content duplicates
  skipped by `dedup_by_content`.
- `snyk/studio-recipes` — genuinely well-formed dedicated security-remediation
  skills (real "Use this skill when:" trigger framing throughout), not a marketing
  page. Worth noting: Snyk's own ToxicSkills research is this project's founding
  citation for `security_scan.py`'s existence (see master spec) — this is the
  first time that same organization's own skill-authoring shows up as audited
  content rather than as a cited statistic.
- `blitzreels/agent-skills`: a third independent `evals/evals.json` schema
  variant collides with `detect_source()` — see audit-gap issue #11's Phase 17
  comment.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 18 cohort: 28 more low-sitemap-count repos (scale batch 4) — first cross-corpus duplicate

Fourth batch (2026-08-21, seed 18). Funnel: 2,448 pairs → 109 held excluded (25
original + 28+28+27 from Phases 15–17) → 1,647-repo tier → 17-call GraphQL screen,
zero failures → same exclusions → seeded draw, 28 repos. **28 of 28 cloned,
pinned, licenses read raw — fourth consecutive 100% license-viable survival.**

**First cross-corpus content duplicate found by the standing every-phase check**:
`jinfanzheng/kode-sdk-csharp`'s `examples/Kode.Agent.WebApiAssistant/skills/
skill-creator/SKILL.md` is byte-identical to `anthropics-financial-services`'
`skill-creator` (Apache-2.0 licensed, confirmed via the skill's own bundled
`LICENSE.txt`) — Anthropic's official skill-creator, legitimately bundled as demo
content for a .NET SDK example app alongside 19 other real, functioning demo
skills (weather, hotel, flight, email, etc. — genuine example-agent content, not
broken stubs). Excluded from this phase's audited count (re-auditing it would
reproduce Phase 8's own findings verbatim and double-count the same skill in the
pilot total) — the clone's copy was deleted, `verification18.json` records the
exclusion. jinfanzheng's audited count: 19, not 20. First hit in eighteen phases
of this check running clean; every prior phase checked all held content and found
zero cross-corpus matches.

One new license type: `materializeinc/agent-skills` carries the **Business
Source License 1.1** (BSL) — source-available, not OSI-approved, but its actual
grant is broader than every prior non-permissive case in this pilot: "copy,
modify, create derivative works, redistribute, and make non-production use" are
explicitly granted (converts to Apache-2.0 on 2030-02-06). The license's
"Additional Use Grant" section (database cluster memory/disk limits) is verbatim
boilerplate from Materialize's main database-product repo, applied without
adaptation to a documentation-only skills repo — a provenance oddity (same
company reusing its own license template somewhere it doesn't quite fit,
unlike Phase 16's aitytech misattributing someone else's license). Same
audit-only posture applied for consistency with every other non-MIT/Apache case
in this pilot.

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `bataitools/bat-skills` | `abeb0f47f8a8` | 2026-08-14 | MIT | 1 | 1 | 1 |
| `coji/natural-japanese` | `0f1cc1c5a4e2` | 2026-08-17 | MIT | 1 | 1 | 476 |
| `danielgwilson/luxin` | `ecaaf9dd1cc0` | 2026-08-21 | MIT | 10 | 1 | 1 |
| `dauquangthanh/hanoi-rainbow` | `0e2ebaea024a` | 2026-01-23 | MIT | 41 | 2 | 14 |
| `dinerojs/skills` | `19d469f92372` | 2026-02-28 | MIT | 3 | 1 | 2 |
| `electron/electron` | `7ca7c5016631` | 2026-08-21 | MIT | 5 | 1 | 122,625 |
| `event-catalog/skills` | `5f5c51b2e348` | 2026-07-09 | MIT | 5 | 1 | 12 |
| `f-labs-io/agent-html-skills` | `5e0cdd181e8f` | 2026-07-13 | MIT | 19 | 1 | 50 |
| `fetcher-sh/fetcher-skills` | `57aa03df66a4` | 2026-08-12 | MIT | 13 | 3 | 0 |
| `gastownhall/beads` | `66048d4fb31a` | 2026-08-21 | MIT | 3 | 1 | 26,485 |
| `geeksfino/finskills` | `8722415a68db` | 2026-03-05 | Apache-2.0 | 30 | 3 | 276 |
| `ggprompts/tfe` | `b71818c5c92d` | 2026-06-10 | MIT | 1 | 1 | 20 |
| `harbor-framework/harbor` | `c0acdfbf2441` | 2026-08-20 | Apache-2.0 | 9 | 2 | 4,490 |
| `hardikpandya/stop-slop` | `8da1f030185b` | 2026-03-18 | MIT | 1 | 1 | 16,056 |
| `irangareddy/openclaw-essentials` | `01e44e8e9c6d` | 2026-02-15 | MIT | 3 | 1 | 0 |
| `jinfanzheng/kode-sdk-csharp` | `8531dbdfa539` | 2026-02-04 | MIT | 19* | 1 | 79 |
| `knocklabs/skills` | `9940017b89d1` | 2026-08-20 | MIT | 7 | 2 | 0 |
| `letz-ai/letzai-skill` | `6b108a4a6d81` | 2026-07-28 | MIT | 1 | 1 | 0 |
| `livekit/agent-skills` | `8e7c931b8324` | 2026-06-16 | MIT | 2 | 2 | 65 |
| `llama-farm/llamafarm` | `6244d466e886` | 2026-06-01 | Apache-2.0 | 19 | 1 | 835 |
| `materializeinc/agent-skills` | `d0fd9ccc4707` | 2026-08-21 | BSL-1.1** | 8 | 1 | 3 |
| `meowa-ai/meowa-skills` | `8a0db229dfde` | 2026-08-19 | MIT | 1 | 1 | 33 |
| `mobbin/skills` | `9657786338c5` | 2026-05-04 | MIT | 1 | 1 | 15 |
| `paulnsorensen/easy-cheese` | `fa07b9d8faba` | 2026-08-20 | MIT | 19 | 1 | 16 |
| `skymavis/skills` | `02465de41221` | 2026-08-10 | MIT | 2 | 1 | 0 |
| `summerkaze/skill-arkts-syntax-assistant` | `26ea21482590` | 2026-02-01 | MIT | 1 | 1 | 84 |
| `twilio/ai` | `8aba46fb65dc` | 2026-08-13 | MIT | 57 | 2 | 30 |
| `yetone/native-feel-skill` | `9bd88c6378e1` | 2026-05-30 | MIT | 1 | 1 | 1,895 |

\* excludes 1 cross-corpus duplicate (Anthropic's `skill-creator`), 20 discovered
on disk. \*\* Business Source License 1.1, see note above.

**Structure notes**: `dauquangthanh/hanoi-rainbow` (41) and `twilio/ai` (57) are
this phase's hidden collections — both audited in full, well under the 200-skill
chunking threshold. `electron/electron` (122,625★, the pilot's highest star count
yet) contributes 5 genuinely clean release-automation skills — boilerplate-only
findings, no new pattern.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 19 cohort: 28 more low-sitemap-count repos (scale batch 5)

Fifth batch (2026-08-21, seed 19). Funnel: 2,448 pairs → 137 held excluded (25
original + 28+28+27+28 from Phases 15–18) → 1,619-repo tier → 17-call GraphQL
screen, zero failures → same exclusions → seeded draw, 28 repos. **28 of 28
cloned, pinned, licenses read raw — fifth consecutive 100% survival.**

Two new license types this phase: `bitwize-music-studio/claude-ai-music-skills`
is **CC0-1.0** (public domain dedication, the most permissive license possible —
no restriction of any kind, audit or adapt both fine, though nothing here is
being adapted regardless). `jorgealves/agent_skills` is **GPL-3.0** proper (as
opposed to AGPL, already seen at Phase 15's `planners-ppt-hell` and this phase's
own `prompt-security/clawsec`) — same audit-only posture as every other copyleft
case for consistency. `bergside/typeui` (1,793★) was this phase's NOASSERTION —
resolved favorably on raw read (MIT), same as every prior case except Phase 17's
ykdojo.

**Zero cross-corpus content duplicates this phase** (0/245 raw skills matched
against the growing 6,150-skill held set) — Phase 18's jinfanzheng match was a
one-off so far, not the start of a pattern.

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `agentlyhq/use-agently` | `639337583c28` | 2026-04-01 | MIT | 4 | 1 | 72 |
| `ant-design/ant-design-cli` | `64fb308cf9d0` | 2026-08-17 | MIT | 1 | 1 | 253 |
| `arcjet/skills` | `a46264ba4142` | 2026-08-20 | Apache-2.0 | 2 | 1 | 2 |
| `autoclaw-cc/xiaohongshu-skills` | `b043748282a5` | 2026-05-24 | MIT | 6 | 1 | 1,799 |
| `benedictking/tavily-web` | `a933268dee05` | 2026-04-21 | MIT | 1 | 1 | 2 |
| `bergside/typeui` | `2a977f1f6616` | 2026-07-04 | MIT (raw)* | 4 | 1 | 1,793 |
| `bitwize-music-studio/claude-ai-music-skills` | `b1b11a67e8ce` | 2026-07-21 | CC0-1.0 | 53 | 2 | 436 |
| `cline/sdk-skill` | `c687e680df2c` | 2026-06-17 | Apache-2.0 | 1 | 1 | 10 |
| `confa-tech/agent-skills` | `35fb4790614d` | 2026-05-19 | MIT | 1 | 1 | 0 |
| `deveshpunjabi/modern-frontend-skill` | `cd8b630f8f97` | 2026-03-20 | MIT | 1 | 1 | 4 |
| `evan715823/cheatsheet-generator-skill` | `c33d9ac4f907` | 2026-04-09 | MIT | 1 | 1 | 184 |
| `flowkit-labs/skills` | `0c9e2b63f504` | 2026-08-12 | MIT | 1 | 1 | 1 |
| `gyteng/kodevu` | `373a9da20057` | 2026-04-04 | MIT | 1 | 1 | 0 |
| `jorgealves/agent_skills` | `85014ad37d71` | 2026-01-25 | GPL-3.0** | 36 | 2 | 2 |
| `lewislulu/html-ppt-skill` | `f3a8435d3901` | 2026-04-26 | MIT | 1 | 1 | 8,002 |
| `maartenlouis/elevenlabs-remotion-skill` | `156ff9d9077e` | 2026-01-24 | MIT | 1 | 1 | 4 |
| `mattbx/shadcn-skills` | `4d6045fc5301` | 2026-04-27 | MIT | 2 | 2 | 18 |
| `muxuuu/serenity-skill` | `c2fe93deedfd` | 2026-05-05 | MIT | 1 | 1 | 3,818 |
| `nodnarbnitram/claude-code-extensions` | `35e7f7deae68` | 2026-04-20 | MIT | 45 | 1 | 15 |
| `open-circle/agent-skills` | `6abb4f9299c6` | 2026-08-20 | MIT | 3 | 1 | 15 |
| `open-pencil/skills` | `623927958f27` | 2026-06-11 | MIT | 1 | 1 | 15 |
| `prompt-security/clawsec` | `aa3aed139701` | 2026-08-20 | AGPL-3.0** | 16 | 2 | 1,086 |
| `silupanda/academic-researcher` | `e75d70d1b044` | 2026-02-16 | MIT | 7 | 1 | 12 |
| `sonofmagic/skills` | `f7b109a855b9` | 2026-08-21 | MIT | 17 | 1 | 2 |
| `tfboy1/academic-paper-writer` | `cf3dec4b829c` | 2026-06-19 | MIT | 5 | 1 | 246 |
| `theagentservice/skills` | `c9a30434f00d` | 2026-02-15 | MIT | 1 | 1 | 0 |
| `vitorpamplona/amethyst` | `0c63687ad48d` | 2026-08-21 | MIT | 31 | 2 | 1,588 |
| `will2025btc/buffett-perspective` | `e18afcfc208f` | 2026-04-06 | MIT | 1 | 1 | 212 |

\* NOASSERTION at screen, raw `LICENSE.md` reads MIT. \*\* Copyleft, audit-only
posture applied for consistency (same as every other GPL-family/CC-BY-SA/ELv2
case in this pilot).

**Structure notes:**

- `nodnarbnitram/claude-code-extensions` (45→28 post-dedup) and
  `silupanda/academic-researcher` (7→1) both use the established
  `.claude/`/`.codex/`/`.cursor/`/`.gemini/`/`.opencode/`/`.windsurf/`
  cross-tool-mirroring convention (Phase 6's symlink-inflation class, now
  content-mirrored rather than symlinked — `dedup_by_content` handles it
  correctly, no code change needed).
- **New audit-gap issue #12**: `nodnarbnitram`'s `templates/skill-skeleton`
  (and, found by the same check, `secondsky-claude-skills`' and
  `skymavis-skills`' equivalents from earlier phases) are genuine
  fill-in-the-blank authoring templates discovered and audited as if real —
  but unlike every prior `EXCLUDED_INTERMEDIATE_DIRS` addition, a blanket
  `templates` exclusion would wrongly drop **102 already-audited real skills**
  across `pixel-process-ug/superkit-agents` and `shoootyou/get-shit-done-multi`
  (both use `templates/skills/<name>/` as their real skill-storage convention).
  Documented, not fixed — see issue #12 and RESULTS.md's Phase 19 section.
- `prompt-security/clawsec`: 15 `security-gitleaks-clean` FAILs, all the same
  `RELEASE_PUBKEY_SHA256` constant repeated across its `claw-*` skill family — a
  public verification hash, not a secret, confirmed by reading multiple
  instances directly.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 20 cohort: 27 more low-sitemap-count repos (scale batch 6) — second license rejection, two more cross-corpus duplicates

Sixth batch (2026-08-21, seed 20). Funnel: 2,448 pairs → 165 held excluded →
1,591-repo tier → 16-call GraphQL screen, zero failures → same exclusions →
seeded draw, 28 repos. **28 drawn, 27 vendored.**

`spotware/ctrader-skills` (NOASSERTION at screen) resolved unfavorably on raw
read — genuine "All rights reserved... governed exclusively by the Spotware End
User License Agreement... by installing, accessing, or using this software, you
agree to be bound." No public grant at all. Dropped, clone deleted, not counted.
Second real license rejection in the pilot (first: Phase 17's ykdojo). Every
other NOASSERTION case (this phase's `vercel-labs/konsistent` included) has
resolved favorably.

**Two more cross-corpus content duplicates** — the check that found its first
hit in eighteen phases at Phase 18 found two more this time, both again
Anthropic's official `skill-creator`: `artivilla/agents-config`'s copy
(identical to the Phase 8 `anthropics-financial-services` original) and
`langfuse/skills`' copy (identical to Phase 18's own `neondatabase-postgres-skills`
copy — a third-generation match, not directly against Phase 8). Both excluded
from this phase's counts for the same reason as Phase 18's instance. **Revised
framing from Phase 18's "one-off, not a pattern"**: three cross-corpus
duplicates across three of the last three phases checked (0, then 1, then 2) —
Anthropic's `skill-creator` being independently bundled as bootstrapping content
by unrelated third parties looks like a recurring, not isolated, discovery
pattern. Worth budgeting for in future phases' triage time.

**A fourth confirmed instance of audit-gap issue #12's template-stub pattern**,
found live this phase: `skillscatalog/registry`'s `templates/basic-skill/SKILL.md`
(`name: my-skill-name`, `author: "@your-github-handle"`, and — new for this
pattern — a self-labeling `tags: [example, template]`). Excluded from the
audited count on direct human read, consistent with issue #12's own conclusion
that no automated detection is safe; this is the first of the four confirmed
instances to carry any self-description signal at all, worth a note added to
issue #12 (not a reliable general heuristic — a real skill about creating
document templates could legitimately carry the same tag — but a partial, weak
one worth having on record).

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `agentspace-so/skills` | `88d28ef1d797` | 2026-05-22 | MIT | 2 | 2 | 12 |
| `artivilla/agents-config` | `11c2e068c97f` | 2026-06-08 | MIT | 32* | 1 | 0 |
| `behisecc/vibesec-skill` | `0590993b35ad` | 2026-02-17 | Apache-2.0 | 1 | 1 | 1,209 |
| `benedictking/exa-search` | `f49762100f01` | 2026-04-21 | MIT | 1 | 1 | 5 |
| `cfircoo/claude-code-toolkit` | `d6264305dcd0` | 2026-03-28 | MIT | 18 | 1 | 17 |
| `cycleuser/skills` | `1f9017d7e68b` | 2026-08-18 | GPL-3.0** | 30 | 1 | 11 |
| `fallow-rs/fallow-skills` | `2e10e44b2b20` | 2026-08-17 | MIT | 2 | 1 | 116 |
| `freee/freee-mcp` | `85f81fd7c1d8` | 2026-08-20 | Apache-2.0 | 1 | 1 | 492 |
| `iress/design-system` | `e5ded9bc6b9e` | 2026-08-04 | Apache-2.0 | 6 | 1 | 1 |
| `jinchenma94/bazi-skill` | `112a5d84cd1a` | 2026-08-18 | MIT | 1 | 1 | 2,635 |
| `joeseesun/qiaomu-mondo-poster-design` | `e82e411c403c` | 2026-03-16 | MIT | 1 | 1 | 1,108 |
| `langfuse/skills` | `ff47830ae782` | 2026-08-20 | MIT | 1* | 1 | 251 |
| `manzxiao/text-to-image-prompt-optimizer` | `58b6ce28fc38` | 2026-02-06 | MIT | 1 | 1 | 2 |
| `michalparkola/tapestry-skills` | `80e1dc56df74` | 2026-03-11 | MIT | 7 | 2 | 523 |
| `notedit/happy-skills` | `9a2d593b6207` | 2026-03-03 | MIT | 12 | 1 | 340 |
| `openstockdata/stock-data-skill` | `5bee3d410faf` | 2026-03-16 | MIT | 1 | 1 | 18 |
| `pbakaus/agent-reviews` | `ee827ae223aa` | 2026-07-08 | MIT | 3 | 2 | 228 |
| `ruchernchong/claude-kit` | `e91af101140c` | 2026-05-18 | MIT | 10 | 1 | 0 |
| `shadowcz007/skills` | `96f8a01c7754` | 2026-03-24 | MIT | 19 | 1 | 0 |
| `skillscatalog/registry` | `e83c630d5931` | 2026-01-03 | MIT | 7* | 1 | 1 |
| `srstomp/pokayokay` | `ef6a34d63bb9` | 2026-07-05 | MIT | 26 | 1 | 9 |
| `supabase/supabase` | `31497ba12765` | 2026-08-21 | Apache-2.0 | 20 | 2 | 108,229 |
| `utooland/skills` | `b4655b549e83` | 2026-02-02 | MIT | 1 | 1 | 1 |
| `vectorize-io/hindsight` | `3de41af86758` | 2026-08-21 | MIT | 11 | 3 | 20,792 |
| `vercel-labs/konsistent` | `bdf0cba9d12c` | 2026-08-14 | Apache-2.0 (raw)*** | 2 | 1 | 160 |
| `vladm3105/aidoc-flow-framework` | `9f163fda7b9b` | 2026-08-16 | MIT | 60 | 1 | 16 |
| `zc277584121/perpetuum` | `704d1c45f316` | 2026-08-14 | MIT | 1 | 1 | 0 |

\* excludes exclusions noted above (artivilla: 1 cross-corpus dup, 33 on disk;
langfuse: 1 cross-corpus dup, 2 on disk; skillscatalog: 1 template stub, 8 on
disk). \*\* audit-only posture, consistent with every other copyleft case.
\*\*\* NOASSERTION at screen, raw `LICENSE` reads standard Apache-2.0.

**Structure notes**: `vladm3105/aidoc-flow-framework` (60) and
`artivilla/agents-config` (32→31 after exclusion) are this phase's hidden
collections, both audited in full. `supabase/supabase` (108,229★, the pilot's
new highest star count) contributes 20 skills at a 14/20 in-queue rate — not as
clean as electron/electron's Phase 18 example, another data point that star
count predicts nothing reliably about collection-level cleanliness.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.
