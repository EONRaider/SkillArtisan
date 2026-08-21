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

## Phase 21 cohort: 23 more low-sitemap-count repos (scale batch 7) — the tier's low-star pool thins out

Seventh batch (2026-08-21, seed 21). Funnel: 2,448 pairs → 192 held excluded →
1,564-repo tier → 16-call GraphQL screen, zero failures → same exclusions →
seeded draw. **The 0–2★ bin's pool dropped to 3 repos (drew all 3, below the
usual target of 8)** — the first sign the tier's low end is thinning as
consecutive phases draw it down; total draw was 23, not 28. `cockroachdb/
cockroach`'s clone hit a transient network failure (GnuTLS recv error mid-fetch)
and succeeded cleanly on a single retry — recorded as infrastructure noise, not
a rejection.

23 of 23 cloned, pinned, licenses read raw — 100% survival on the drawn set. Two
new source-available license types, both read in full and both explicitly
grant broad non-competing-use rights (same shape as Phase 18's BSL 1.1, audit-
only posture applied for consistency): `cockroachdb/cockroach`'s own
"CockroachDB Software License" and `millionco/expect`'s **FSL-1.1-MIT**
(Functional Source License — converts to MIT after a delay period, permits
"any purpose other than a Competing Use").

**`thelobbi/claude`: 452 skills discovered vs. 1 sitemap-listed** — a
452x undercount, the pilot's second-largest hidden collection after Phase 15's
717x `claude-dev-suite`. A real, dedicated multi-plugin Claude Code toolkit
(content spot-checked directly, not assumed from volume alone — genuine, well-
formed skills throughout). 50 exact-content duplicates deduped (452→402),
chunked for audit (5×100-skill windows) per the established >200-skill rule.

**Structural note, new to this pilot**: 49 of thelobbi's 402 skills (12%) live
under a `plugins/claude-code-expert/archive/v7.6.0/` versioned-snapshot
directory — real, previously-published content from an old plugin version, not
a template stub (a genuinely different character than issue #12's pattern).
35 of the phase's 35 total per-skill errors and 77 of its "Missing required
field: name" `frontmatter-valid` FAILs concentrate almost entirely in this
archived subtree — an older, pre-`name:`-field authoring convention frozen in
the archive, correctly flagged as real defects in that historical snapshot, not
a new bug. Not excluded (genuinely real content, unlike a template) and not
opened as an issue (no miscalibration — a `rebuild`/FAIL verdict on a
demonstrably outdated skill snapshot is a legitimate audit outcome).

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `21st-dev/agent-elements` | `b04b36cb6381` | 2026-04-24 | MIT | 1 | 1 | 95 |
| `agents365-ai/drawio-skill` | `2ee141e0ff18` | 2026-08-05 | MIT | 1 | 1 | 7,862 |
| `aotenjou/silicon-paddleocr` | `c01bbe8c5a87` | 2026-02-10 | MIT | 1 | 1 | 1 |
| `astro-han/karpathy-llm-wiki` | `eafcc77001e4` | 2026-07-24 | MIT | 1 | 1 | 1,966 |
| `cockroachdb/cockroach` | `8812064a015d` | 2026-08-07 | CockroachDB-SL* | 15 | 1 | 32,407 |
| `comet-ml/opik-skills` | `88c7250135d7` | 2026-08-19 | Apache-2.0 | 2 | 2 | 6 |
| `didit-protocol/skills` | `408979a9b2a4` | 2026-08-10 | MIT | 13 | 1 | 26 |
| `dream-num/skills` | `9e4358e8f1cd` | 2026-08-15 | Apache-2.0 | 7 | 1 | 62 |
| `henricook/claude-glab-skill` | `b5ef4fb77f8e` | 2025-11-07 | MIT | 1 | 1 | 74 |
| `kenchangh/kicad-schematic` | `5ebbc911a14d` | 2026-02-26 | MIT | 1 | 1 | 1 |
| `learnprompt/luban-skill` | `cea2da331027` | 2026-07-11 | MIT | 1 | 1 | 927 |
| `learnwy/skills` | `d727b3862052` | 2026-06-03 | MIT | 13 | 1 | 3 |
| `lingui/skills` | `acc25ae9f61d` | 2026-08-14 | MIT | 6 | 2 | 9 |
| `mcp-use/skills` | `3bf0eaa4b007` | 2026-01-31 | Apache-2.0 | 2 | 1 | 1 |
| `millionco/expect` | `39e975007257` | 2026-04-10 | FSL-1.1-MIT** | 8 | 1 | 3,551 |
| `react-native-community/skills` | `1fb0e0848fc7` | 2026-08-05 | MIT | 2 | 1 | 26 |
| `supermemoryai/supermemory` | `34876664810a` | 2026-08-20 | MIT | 1 | 1 | 28,978 |
| `thelobbi/claude` | `3678a0c7540f` | 2026-08-18 | MIT | 452*** | 1 | 19 |
| `tigrisdata/skills` | `668ea424758e` | 2026-07-23 | MIT | 18 | 1 | 3 |
| `timbroddin/app-store-aso-skill` | `3f0b917384ae` | 2026-05-04 | MIT | 1 | 1 | 95 |
| `twostraws/swiftdata-agent-skill` | `922d989473a9` | 2026-03-11 | MIT | 1 | 1 | 391 |
| `veris-ai/veris-skills` | `711573d85dba` | 2026-08-21 | Apache-2.0 | 4 | 1 | 3 |
| `vladimir-human/humanizer-ru` | `e5f4eba5d0c5` | 2026-08-16 | MIT | 2 | 1 | 111 |

\* CockroachDB Software License — source-available, broad grant "for the
purposes of operating, evaluating, testing, fixing, integrating with, and
improving CockroachDB," audit-only posture applied. \*\* Functional Source
License 1.1 (MIT Future License) — same posture. \*\*\* 402 post-dedup, audited.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 22 cohort: 20 more low-sitemap-count repos (scale batch 8) — 0-2★ bin fully exhausted

Eighth batch (2026-08-21, seed 22). Funnel: 2,448 pairs → 215 held excluded →
1,541-repo tier → 16-call GraphQL screen, zero failures → same exclusions →
seeded draw. **The 0–2★ bin's drawable pool is now 0** — fully exhausted after
eight phases drawing it down (Phase 21 saw it drop to 3; this phase confirms
the depletion). Total draw: 20 repos, not 28. 20/20 cloned, pinned, licenses
read raw — 100% survival. Two NOASSERTION cases both resolved favorably on raw
read: `acedatacloud/skills` (Apache-2.0) and `maplibre/maplibre-agent-skills`
(MIT).

**`organvm-iv-taxis/a-i--skills`: 703 raw discovered, 520 exact-content
duplicates deduped (183 unique)** — not a new bug, the repo's own description
("12 categories," "distributions") explains it structurally: the same ~172
unique skills are packaged three times over (`distributions/claude/`,
`distributions/codex/`, `distributions/extensions/`) plus a canonical
`skills/<category>/` source tree — the established multi-tool-mirroring
convention (Phase 6/15/19), just organized as top-level directories instead of
dotfiles. `dedup_by_content` handled it correctly.

**A sixth confirmed instance of issue #12's template-stub pattern**, and a
useful new data point: `acedatacloud/skills`' `template/SKILL.md`
(`name: template-skill`, `description: A template for creating new
AceDataCloud Agent Skills. Copy this directory and customize.`) isn't nested
under any parent directory named `templates` at all — it *is* the skill's own
top-level directory, named `template` (singular). Even a narrower fix scoped
to "the skill directory's own name" rather than an intermediate parent
wouldn't safely catch this without risking excluding a real skill someone
names literally `template` — logged on issue #12 as reinforcing evidence, not
a new conclusion. Excluded from this phase's audited count on direct read.

**Richest single-author field family found yet**: `organvm-iv-taxis/a-i--skills`
uses a ~13-field custom governance/classification taxonomy across most of its
165 flagged skills (`governance_phases`, `governance_norm_group`,
`governance_auto_activate`, `organ_affinity`, `complements`, `complexity`,
`tier`, `time_to_learn`, `inputs`, `outputs`, `side_effects`, `includes`,
`prerequisites`) — a genuinely elaborate, internally-consistent personal
schema (matches the repo's own "organ"/"taxis" branding), not scattered
ad-hoc fields. Commented on issue #9.

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `acedatacloud/skills` | `6335fc99f960` | 2026-08-21 | Apache-2.0 (raw)* | 101** | 1 | 16 |
| `alchaincyf/paul-graham-skill` | `8de3d2bf4e0c` | 2026-05-28 | MIT | 1 | 1 | 89 |
| `arvindrk/extract-design-system` | `1873741ba8de` | 2026-06-19 | MIT | 1 | 1 | 183 |
| `benedictking/codex-review` | `348ce8c85bb9` | 2026-04-21 | MIT | 1 | 1 | 12 |
| `bufbuild/claude-plugins` | `c4766e5fff1b` | 2026-06-18 | Apache-2.0 | 1 | 1 | 18 |
| `buluslan/ecommerce-competitor-analyzer` | `853c7102b769` | 2026-08-19 | MIT | 1 | 1 | 52 |
| `daydreammy/tushare-openclaw-skill` | `d9778b278374` | 2026-02-08 | MIT | 1 | 1 | 16 |
| `denissergeevitch/agents-best-practices` | `47c5590af77e` | 2026-08-10 | MIT | 1 | 1 | 2,233 |
| `hermeticormus/libreuiux-claude-code` | `e5a061ebeb85` | 2026-05-27 | MIT | 74 | 1 | 93 |
| `jimliu/baoyu-design` | `026d4ea012bd` | 2026-07-29 | MIT | 2 | 2 | 3,523 |
| `joeseesun/qiaomu-knowledge-site-creator` | `1efa6ca13402` | 2026-02-25 | MIT | 1 | 1 | 362 |
| `kesslerio/ultimate-frontend-design-openclaw-skill` | `b36c53e95de3` | 2026-02-23 | Apache-2.0 | 1 | 1 | 6 |
| `maplibre/maplibre-agent-skills` | `efacb28bae72` | 2026-08-09 | MIT (raw)* | 5 | 2 | 134 |
| `organvm-iv-taxis/a-i--skills` | `1d929d47cf56` | 2026-07-19 | Apache-2.0 | 703→183 | 1 | 15 |
| `sagargupta16/claude-cost-optimizer` | `519e972b0e45` | 2026-08-15 | MIT | 2→1 | 1 | 35 |
| `santifer/career-ops` | `5291cc79755c` | 2026-08-21 | MIT | 1 | 1 | 67,113 |
| `streamlit/streamlit` | `fc86025a6db4` | 2026-08-21 | Apache-2.0 | 21 | 1 | 45,577 |
| `vercel/flags` | `6294177c50e3` | 2026-08-18 | MIT | 1 | 1 | 616 |
| `whatevertogo/feishuskill` | `08e9dddf692a` | 2026-03-22 | MIT | 1 | 1 | 38 |
| `yizhiyanhua-ai/fireworks-tech-graph` | `d56d45a286f1` | 2026-08-19 | MIT | 2→1 | 1 | 10,745 |

\* NOASSERTION at screen, raw LICENSE/LICENSE.md resolves favorably.
\*\* excludes 1 template stub, 102 on disk.

**Structure notes**: `jimliu/baoyu-design` — a real true-positive
`absolute-user-path` finding (Phase 5-class, not a doc example): a committed
build/sync log (`references/upstream-sync/apply-report.json`) leaks the
author's real local machine paths (`/Users/jimliu/GitHub/baoyu-design/...`)
dozens of times, accidentally checked in as tooling output.
`hermeticormus/libreuiux-claude-code`'s `plugins/archetypal-alchemy/` is
genuinely creative content (a Tarot-Major-Arcana-to-UI-color-palette mapping
skill) — real, well-formed, just written in prose-heading style without a
frontmatter block (3 of the phase's per-skill errors, correctly caught).

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 23 cohort: 20 more low-sitemap-count repos (scale batch 9) — the pilot's largest hidden collection yet

Ninth batch (2026-08-21, seed 23). Funnel: 2,448 pairs → 235 held excluded →
1,521-repo tier → 16-call GraphQL screen, zero failures → same exclusions →
seeded draw (0–2★ bin still exhausted, as Phase 22). 20 of 20 cloned, pinned,
licenses read raw — 100% survival, no NOASSERTION cases this phase.

**`terminalskills/skills`: 1,018 skills discovered vs. 1 sitemap-listed** — the
pilot's largest single hidden collection ever (surpassing Phase 21's
`thelobbi/claude` at 452 and Phase 15's `claude-dev-suite` at 717 in raw
count). Content spot-checked directly across multiple unrelated topics before
committing to a full audit (genuine, well-formed, alphabetically-organized
`skills/<topic>/` reference library spanning an encyclopedic range — "3dsmax-
rendering" through "zustand" — each skill's frontmatter carrying a consistent
`author: terminal-skills` / `version` / `category` / `tags` schema).
Chunked into 11×~100-skill windows per the established >200-skill rule, using
Phase 21's corrected lesson (chunk against the post-dedup discovery count, not
a raw guess). **Zero per-skill errors across all 1,018 skills** — the cleanest
large corpus this pilot has audited at scale.

**Real bug found and fixed (v2.5.13)**: two `terminalskills/skills` skills
(`mlflow`, `sequenzy-email-marketing`) auto-detected as first-party via
`has_lifecycle_markers`' unguarded metadata-field substring match — both carry
a `tags:` entry (`ml-lifecycle`, `lifecycle-email`) that happens to contain
the literal substring "lifecycle" in an unrelated domain context (MLflow's ML
lifecycle, email-campaign lifecycles). Fixed by requiring the same
co-occurrence discipline the body-text check already used. See
`../audit-pilot/RESULTS.md`'s Phase 23 section and `CHANGELOG.md`'s [2.5.13].

**Highest single-corpus reserved-word concentration in the pilot**: 7 of
`terminalskills/skills`' 1,018 skills trip the reserved-word check
(`anthropic-sdk`, `claude-code`, `claude-computer-use`, `claude-hud`,
`claude-mem`, `git-guardrails-claude-code`, `oh-my-claudecode`) — a natural
consequence of an encyclopedic library genuinely covering Claude/Anthropic
tooling as topics in their own right, not the "excluded from the author's own
shipped list" pattern earlier corpora showed. Reserved-word true positive now
28/28 across the whole pilot, zero exceptions.

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `a-tokyo/agent-skills` | `99652ee6a787` | 2026-08-06 | MIT | 11 | 2 | 15 |
| `agno-agi/agno` | `7b8e5308e9c8` | 2026-08-21 | Apache-2.0 | 4 | 3 | 41,817 |
| `antdv-next/skills` | `0dd42f92751b` | 2026-07-03 | MIT | 1 | 1 | 10 |
| `cnemri/google-genai-skills` | `7277476f9229` | 2026-02-06 | MIT | 10 | 1 | 125 |
| `erikote04/swift-api-design-guidelines-agent-skill` | `36cdc1b5680f` | 2026-02-18 | MIT | 1 | 1 | 27 |
| `fatfingererr/macro-skills` | `13e538802829` | 2026-02-03 | MIT | 37 | 1 | 3 |
| `fradser/dotclaude` | `6f2a0b2345b9` | 2026-08-12 | MIT | 104 | 1 | 582 |
| `framix-team/openclaw-tavily` | `6db474508f44` | 2026-02-14 | MIT | 1 | 1 | 75 |
| `herdrdev/herdr` | `624dfd479655` | 2026-08-20 | Apache-2.0 | 5 | 1 | 31,223 |
| `mouse-lin/finesse-skill` | `5050b6c71e27` | 2026-08-04 | MIT | 1 | 1 | 470 |
| `nhadaututtheky/neural-memory` | `2015cb9b0973` | 2026-08-16 | MIT | 5 | 3 | 237 |
| `ningzimu/image-to-editable-ppt-skill` | `fb869763127f` | 2026-07-28 | MIT | 1 | 1 | 2,089 |
| `oil-oil/beautify-github-readme` | `55bdb1c05414` | 2026-07-27 | MIT | 1 | 1 | 1,648 |
| `outsharp/shipp-skills` | `c623cae557f3` | 2026-03-22 | Apache-2.0 | 9 | 1 | 4 |
| `parthjadhav/ios-marketing-capture` | `00ae3cbe2250` | 2026-04-11 | MIT | 1 | 1 | 254 |
| `temporalio/skill-temporal-cloud` | `2d867d1f96ae` | 2026-03-26 | MIT | 1 | 1 | 5 |
| `terminalskills/skills` | `7a5cc96749b0` | 2026-07-26 | Apache-2.0 | 1,018 | 1 | 134 |
| `tobi/qmd` | `dbfd0b4736ae` | 2026-08-18 | MIT | 2 | 2 | 29,023 |
| `tscircuit/skill` | `3dbfeec2d2c9` | 2026-08-13 | MIT | 1 | 1 | 18 |
| `wshuyi/translate-pdf-skill` | `5836f0de12d9` | 2026-01-01 | MIT | 1 | 1 | 21 |

**Structure notes**: `mouse-lin/finesse-skill` (4→1 post-dedup) and
`nhadaututtheky/neural-memory` (8→5) both use the established multi-tool-
mirroring convention. `fradser/dotclaude` (104 skills) is this phase's second
hidden collection, audited in full.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 24 cohort: 20 more low-sitemap-count repos (scale batch 10) — first two major vendors from the low-star tier

Tenth batch (2026-08-21, seed 24). Funnel: 2,448 pairs → 255 held excluded →
1,501-repo tier → 16-call GraphQL screen (one transient `gh: HTTP 503`
absorbed cleanly by per-batch persistence, resumed on retry) → same
exclusions → seeded draw (0–2★ bin still exhausted). 20 of 20 cloned, pinned,
licenses read raw — 100% survival.

**Two major-vendor repos drawn this phase** — `oracle/skills` (Oracle
Corporation, UPL-1.0, a new pilot license type — OSI-approved, broadly
permissive) and `canner/wrenai` (17,347★, multi-licensed by path:
`skills/**` and `core/**` are both explicitly Apache-2.0 per the repo's own
path→license map, confirmed by reading the full `LICENSE` file and checking
every discovered skill path against the table — no ambiguity). `aws-samples/
sample-well-architected-skills-and-steering` is **MIT-0** (MIT, no attribution
required). Two NOASSERTION cases resolved favorably on raw read:
`chjm-ai/stock-monitor-skill` (MIT) and `redwoodjs/local-ci` (FSL-1.1-MIT,
already-seen license type).

**An eighth confirmed instance of issue #12's template-stub pattern**:
`aws-samples/...`'s `skills/example-skill/SKILL.md`, self-declared "Example
skill template... You should never use this skill directly as it is just a
template." Its own directory is named `example-skill`, not `example` — yet
another shape the existing exact-name exclusion wouldn't catch. Excluded from
this phase's audited count on direct read; commented on #12.

**First phase with zero rebuild decisions and zero first-party
misclassifications** since scaling began — a clean, uneventful phase by the
pilot's own established measures, correctly reported as such.

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `adspower/adspower-browser` | `06dc59d65e09` | 2026-07-20 | MIT | 1 | 1 | 131 |
| `alchaincyf/zhangxuefeng-skill` | `a9a71563a39f` | 2026-05-28 | MIT | 1 | 1 | 10,177 |
| `aws-samples/sample-well-architected-skills-and-steering` | `4b58ba02670a` | 2026-08-17 | MIT-0 | 5* | 2 | 247 |
| `bryanwhl/ffmpeg-video-editor` | `d5c3ee6e9896` | 2026-03-03 | MIT | 1 | 1 | 7 |
| `canner/wrenai` | `f2841bcbdf8d` | 2026-08-21 | Apache-2.0 (multi)** | 7 | 1 | 17,347 |
| `chjm-ai/stock-monitor-skill` | `91de3efccf55` | 2026-02-02 | MIT (raw)*** | 1 | 1 | 45 |
| `collaborative-deep-research/agent-papers-cli` | `23a1941893d0` | 2026-03-22 | Apache-2.0 | 4 | 2 | 49 |
| `cypress-io/ai-toolkit` | `9c9038ee1faf` | 2026-06-25 | MIT | 3 | 3 | 40 |
| `daleseo/korean-skills` | `ae12ba27982e` | 2026-05-04 | MIT | 3 | 3 | 160 |
| `dpconde/claude-android-skill` | `edfca5e36ceb` | 2025-12-07 | MIT | 1 | 1 | 314 |
| `jiaiyan/element-plus-skills` | `1d126b39a805` | 2026-03-13 | MIT | 89 | 1 | 24 |
| `kunchenguid/chrome-devtools-axi` | `fb6eb4545053` | 2026-08-20 | MIT | 1 | 1 | 324 |
| `oracle/skills` | `9f7192af7cdb` | 2026-08-14 | UPL-1.0 | 14 | 2 | 815 |
| `penfick/skills` | `89479377389f` | 2026-06-05 | MIT | 1 | 1 | 12 |
| `redwoodjs/local-ci` | `a8db59493b88` | 2026-08-21 | FSL-1.1-MIT (raw)*** | 3 | 1 | 779 |
| `rllm-org/hive` | `9ed315971ea2` | 2026-04-27 | Apache-2.0 | 3 | 3 | 213 |
| `skillhq/flight-search` | `49ed0d291fef` | 2026-04-12 | MIT | 1 | 1 | 25 |
| `unovue/shadcn-vue` | `24999cd6cf62` | 2026-08-17 | MIT | 1 | 1 | 10,476 |
| `voltagent/skills` | `066b137c520a` | 2026-01-27 | MIT | 4 | 3 | 14 |
| `yusukebe/ax` | `8abbca2fc400` | 2026-08-05 | MIT | 1 | 1 | 686 |

\* excludes 1 template stub, 6 on disk. \*\* per-path multi-license, all
discovered skill paths fall under the Apache-2.0-licensed `skills/**`/`core/**`
trees. \*\*\* NOASSERTION at screen, raw read resolves favorably.

**Structure notes**: `jiaiyan/element-plus-skills` (89 skills) confirmed a
genuine off-by-one relative-path defect
(`element-plus-components/SKILL.md` references `./components/el-affix/
SKILL.md`, but `components/` actually sits at the repo root, not nested under
`element-plus-components/`) — same established class as Phase 9/12/14's
off-by-one authoring defects. `rllm-org/hive`: 3 exact-content duplicates
deduped.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 25 cohort: 20 more low-sitemap-count repos (scale batch 11)

Eleventh batch (2026-08-21, seed 25). Funnel: 2,448 pairs → 275 held excluded
→ 1,481-repo tier → 15-call GraphQL screen, zero failures → same exclusions →
seeded draw (0–2★ bin still exhausted). 20 of 20 cloned, pinned, licenses read
raw — 100% survival, no NOASSERTION cases this phase. `chuspeeism/
dashi-ppt-skill` — **AGPL-3.0**, same audit-only posture as every other
copyleft case. Zero cross-corpus duplicates against the 9,519-skill held set.

`8090-inc/software-factory-plugin`: 2 exact-content duplicates deduped
(4→2). `tondevrel/scientific-agent-skills` (62 skills) — a genuine scientific-
computing reference library (numpy, scipy, sympy, biopython, qiskit, rdkit,
opencv, pyscf, mdanalysis) — is this phase's hidden collection, audited in
full; its own domain density (each library's SKILL.md running well past
1,000 lines) drove all 9 of this phase's `rebuild` decisions, spot-verified
(`numpy/SKILL.md`: 1,361 lines).

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `8090-inc/software-factory-plugin` | `90459912f10e` | 2026-06-08 | MIT | 2 | 1 | 7 |
| `alchaincyf/elon-musk-skill` | `5a7d8cf0f23c` | 2026-05-28 | MIT | 1 | 1 | 487 |
| `alchaincyf/mrbeast-skill` | `504c360a0b35` | 2026-05-28 | MIT | 1 | 1 | 104 |
| `bradautomates/claude-video` | `83da59fa78c3` | 2026-06-30 | MIT | 1 | 1 | 15,943 |
| `chuspeeism/dashi-ppt-skill` | `7cb23347f91c` | 2026-07-30 | AGPL-3.0* | 1 | 2 | 5,862 |
| `deeflect/mies` | `0b6c4d27706c` | 2026-05-29 | MIT | 1 | 1 | 4 |
| `epiral/bb-browser` | `7975dc74b3f6` | 2026-05-29 | MIT | 2 | 2 | 6,063 |
| `greedychipmunk/agent-skills` | `378ec597428a` | 2026-08-13 | MIT | 17 | 1 | 14 |
| `jin-doh/traceknot` | `6efbf1ea6383` | 2026-08-21 | MIT | 1 | 1 | 3 |
| `jpeggdev/humanize-writing` | `da03340e5bb3` | 2026-03-14 | MIT | 1 | 1 | 51 |
| `linear/linear-release` | `cbd166fad995` | 2026-08-21 | MIT | 1 | 1 | 63 |
| `motion-creative/skills` | `5d031702c7b8` | 2026-03-11 | MIT | 5 | 1 | 10 |
| `remix-run/agent-skills` | `33578aae4aa3` | 2026-06-18 | MIT | 3 | 3 | 138 |
| `sailtonight/kalopilot-skill` | `ea60e237dbfb` | 2026-08-17 | MIT | 1 | 1 | 6 |
| `storybookjs/react-native` | `c53ff1c9947f` | 2026-07-27 | MIT | 3 | 2 | 1,310 |
| `tamagui/tamagui` | `9f2297f893fa` | 2026-08-20 | MIT | 3 | 1 | 14,150 |
| `tondevrel/scientific-agent-skills` | `6e89d9e8c841` | 2026-02-01 | MIT | 62 | 2 | 19 |
| `wzyn20051216/solidworks-automation-skill` | `cc1e9301ecdf` | 2026-08-03 | MIT | 5 | 1 | 753 |
| `yejinlei/pdf-ocr-skill` | `c44d4e7b758a` | 2026-04-20 | MIT | 1 | 2 | 14 |
| `yyh211/claude-meta-skill` | `ba6f50c5724d` | 2026-05-15 | MIT | 12 | 1 | 274 |

\* audit-only posture applied for consistency.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 26 cohort: 20 more low-sitemap-count repos (scale batch 12) — third and fourth cross-corpus duplicates, two new license types

Twelfth batch (2026-08-21, seed 26). Funnel: 2,448 pairs → 295 held excluded
→ 1,461-repo tier → 15-call GraphQL screen, zero failures → same exclusions →
seeded draw (0–2★ bin still exhausted). 20 of 20 cloned, pinned, licenses
read raw — 100% survival. `rhavekost/author-toolkit`'s NOASSERTION resolved
favorably on raw read (MIT).

**Two new license types**, both read in full: `alphamoemoe/foci` — **LGPL-2.1**
(the pilot's first, distinct from the GPL-3.0/AGPL-3.0 already seen), and
`alexgreensh/token-optimizer` — **PolyForm Noncommercial License 1.0.0** (a
real, recognized source-available license restricting commercial use,
permitting any "permitted purpose" otherwise). Both get the same audit-only
posture as every other restrictive-license case in this pilot.

**Two more cross-corpus content duplicates** (a fourth consecutive phase
where this check found a hit, following Phases 18/20): `composio-community/
skills`' copy of Anthropic's `skill-creator` (matches Phase 18's
`neondatabase-postgres-skills` copy) and — a genuinely different character
from every prior instance — **`streamlit/agent-skills`' sole skill
(`developing-with-streamlit`) is byte-identical to a copy already held from
Phase 24's `streamlit/streamlit`**: the *same company* publishing the
identical skill verbatim across two of its own repos, not a third party
redistributing someone else's official content. After excluding the
duplicate, `streamlit/agent-skills` contributes **zero** new skills to the
pilot — its one skill was entirely redundant with already-held content.

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `alchaincyf/naval-skill` | `259e452ef6f6` | 2026-05-28 | MIT | 1 | 1 | 232 |
| `alexgreensh/token-optimizer` | `4ac97642c0bd` | 2026-08-19 | PolyForm-NC-1.0* | 6 | 3 | 1,936 |
| `alphamoemoe/foci` | `68012be7e5e1` | 2026-01-25 | LGPL-2.1* | 6 | 1 | 7 |
| `composio-community/skills` | `c4b270016aa8` | 2026-03-19 | MIT | 1** | 2 | 148 |
| `d4kooo/openclaw-token-memory-optimizer` | `8963642ad606` | 2026-02-05 | MIT | 1 | 1 | 20 |
| `dbos-inc/agent-skills` | `f6d4d2394ef1` | 2026-08-19 | MIT | 4 | 2 | 17 |
| `elementsix/elementsix-skills` | `bda217719e13` | 2026-03-04 | MIT | 1 | 1 | 303 |
| `feicaiclub/video-spec-builder` | `9e73275b35e8` | 2026-05-18 | MIT | 1 | 1 | 915 |
| `hamen/material-3-skill` | `14385f2bf380` | 2026-07-16 | MIT | 1 | 1 | 1,290 |
| `mepuka/effect-ontology` | `c148102d5789` | 2025-12-25 | MIT | 15 | 1 | 5 |
| `mrgediao/shuorenhua` | `1a97697fb2b1` | 2026-08-21 | MIT | 1 | 1 | 1,169 |
| `petekp/claude-code-setup` | `f1cb10fdacff` | 2026-08-06 | MIT | 18 | 1 | 44 |
| `rhavekost/author-toolkit` | `b78287003edf` | 2026-07-14 | MIT (raw)*** | 6 | 2 | 13 |
| `safaiyeh/app-store-review-skill` | `6b98eb4f0e3b` | 2026-08-11 | MIT | 1 | 1 | 285 |
| `shopmeskills/mcp` | `81f9813f632a` | 2026-02-20 | MIT | 2 | 1 | 3 |
| `streamlit/agent-skills` | `c69a265613f1` | 2026-07-23 | Apache-2.0 | 0** | 1 | 224 |
| `toolsai/auto-skill` | `f4e042cb1718` | 2026-08-17 | MIT | 1 | 1 | 196 |
| `torpedod/claude-council` | `f963fd62a423` | 2026-04-22 | MIT | 1 | 1 | 13 |
| `warpdotdev/oz-skills` | `6c08c49fc6c5` | 2026-04-17 | MIT | 15 | 2 | 821 |
| `yoshiko-pg/difit` | `e4023997f359` | 2026-08-09 | MIT | 6 | 2 | 3,088 |

\* audit-only posture applied for consistency. \*\* excludes 1 cross-corpus
duplicate each. \*\*\* NOASSERTION at screen, raw read resolves favorably.

**Structure notes**: `alexgreensh/token-optimizer` (16→6 post-dedup) and
`yoshiko-pg/difit` (8→6) both use the established multi-platform-packaging
convention. `alexgreensh`'s `token-optimizer` skill's own gitleaks/pattern
findings (14 gitleaks, 22 HIGH) all trace to `scripts/benchmark.py` and
`runtime_env.py` — fake alphabet-sequence test tokens
(`ghp_ABCDEFghijklmnop...`) and generic example paths (`/Users/dev/project`,
`<you>` placeholders), consistent with the tool's own purpose (benchmarking
against realistic-looking test fixtures).

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 27 cohort: 19 more low-sitemap-count repos (scale batch 13) — spotware re-drawn and re-rejected, a third cross-corpus duplicate character

Thirteenth batch (2026-08-21, seed 27). Funnel: 2,448 pairs → 315 held
excluded → 1,441-repo tier → 15-call GraphQL screen, zero failures → seeded
draw. **20 drawn, 19 vendored** — `spotware/ctrader-skills` came up again by
chance (same pin, `01e93fec`, as its Phase 20 rejection — the held-set
exclusion only tracks *vendored* repos, not *rejected* ones, so a genuinely
proprietary repo can be re-drawn). Re-verified consistently (same "All
rights reserved... Spotware End User License Agreement" text) and dropped
again. **Fixed going forward**: `ykdojo/claude-code-tips` (Phase 17) and
`spotware/ctrader-skills` are now added to the funnel script's permanent
exclusion set alongside the 25 originally-held repos, so neither gets
re-drawn a third time.

**A third distinct character of cross-corpus duplicate**: `kimyx0207/
findskill`'s `original/SKILL.md` is byte-identical to `artivilla/
agents-config`'s `find-skills` (Phase 20) — but unlike the Anthropic-
skill-creator-redistribution shape (Phases 18, 20, 26) or the same-company-
self-duplicate shape (Phase 26's Streamlit), this is a third party
deliberately preserving *another* third party's exact tool unmodified
(directory literally named `original`) alongside their own derivative
(`windows`, a genuinely distinct Windows-compatibility fork — the repo's own
description says as much: "Windows兼容版...修复npx skills空输出问题"). The
`original` copy excluded from this phase's count; the real `windows` fork
audited normally.

Two NOASSERTION cases resolved favorably on raw read: `muthuishere/
hand-drawn-diagrams` (MIT) and `vercel/streamdown` (Apache-2.0).
`netresearch/security-audit-skill` carries **both** `LICENSE-CC-BY-SA-4.0`
and `LICENSE-MIT` files with no explicit path-scoping — treated under the
same audit-only posture as every restrictive case for consistency, though
the MIT option alone would already cover this pilot's usage if a dual-license
convention (either license, author's choice) applies. `doccker/cc-use-exp`
carries **PolyForm Noncommercial License 1.0.0** — the pilot's second
instance (first: Phase 26's alexgreensh).

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `andrewgleave/skills` | `d6c72b885a19` | 2026-04-23 | MIT | 5 | 1 | 31 |
| `antibrow/anti-detect-browser-skills` | `c91f6e17be78` | 2026-08-12 | MIT | 3 | 3 | 9 |
| `axtonliu/axton-obsidian-visual-skills` | `1265976d9746` | 2026-02-11 | MIT | 3 | 3 | 3,323 |
| `deepdotspace/deepspace-skill` | `28766417f905` | 2026-08-21 | MIT | 1 | 1 | 5 |
| `doccker/cc-use-exp` | `448997909221` | 2026-06-30 | PolyForm-NC-1.0**** | 108 | 1 | 1,011 |
| `giulioco/skills` | `2db17d19e51d` | 2026-07-02 | Apache-2.0 | 8 | 1 | 10 |
| `greendesertsnow/pocketbase-skills` | `c573263e84a2` | 2026-04-08 | MIT | 1 | 1 | 10 |
| `handsomestwei/patent-disclosure-skill` | `424da1ae803d` | 2026-08-20 | MIT | 1 | 1 | 5,204 |
| `hithink-tech/financial-api` | `9dbef74d2ce5` | 2026-08-17 | MIT | 11 | 1 | 610 |
| `kevmoo/dash_skills` | `893f53ddd02d` | 2026-08-19 | Apache-2.0 | 10 | 3 | 142 |
| `kimyx0207/findskill` | `93b8024620f6` | 2026-08-13 | MIT | 1* | 1 | 110 |
| `muthuishere/hand-drawn-diagrams` | `b1a87cf580e9` | 2026-08-10 | MIT (raw)** | 1 | 1 | 60 |
| `netresearch/security-audit-skill` | `647a9ba130c7` | 2026-08-13 | CC-BY-SA-4.0/MIT*** | 1 | 1 | 36 |
| `oil-oil/ui-ux-guide` | `da6a44d3081f` | 2026-04-18 | Apache-2.0 | 1 | 1 | 91 |
| `quantumnous/skills` | `a0db8d8e878c` | 2026-03-14 | MIT | 1 | 1 | 79 |
| `raroque/vibe-security-skill` | `850938f20f69` | 2026-03-15 | MIT | 1 | 1 | 965 |
| `texiaoyao/office-automation-skill` | `111beb1b0a62` | 2026-02-22 | MIT | 1 | 1 | 6 |
| `vercel/streamdown` | `725e390fc4da` | 2026-08-21 | Apache-2.0 (raw)** | 1 | 1 | 5,525 |
| `yeadon8888/cangjie-skill` | `c489ba54a420` | 2026-04-12 | MIT | 3 | 1 | 201 |

\* excludes 1 cross-corpus duplicate, 2 on disk. \*\* NOASSERTION at screen,
raw read resolves favorably. \*\*\* dual-licensed, no explicit scoping,
audit-only posture applied. \*\*\*\* audit-only posture applied for
consistency.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 28 cohort: 20 more low-sitemap-count repos (scale batch 14) — a fifth cross-corpus duplicate, two more #11 sub-cases at once

Fourteenth batch (2026-08-21, seed 28). Funnel: 2,448 pairs → 336 held
excluded → 1,420-repo tier → 15-call GraphQL screen (one transient "unexpected
end of JSON input" on batch 4, resumed cleanly on retry) → seeded draw,
`rainlib/ai-storyboard` is **GPL-3.0**, audit-only posture applied. 20 of 20
cloned, pinned, licenses read raw — 100% survival, no NOASSERTION cases.

**A fifth cross-corpus content duplicate** — the same Anthropic official
`mcp-builder` skill found in `bmad-labs/skills`, byte-identical to Phase 25's
`yyh211/claude-meta-skill` copy. Excluded from this phase's count, same
treatment as every prior instance.

**Two #11 sub-cases in one phase, six misclassified skills total**: `bmad-labs/
skills` writes `evals.json` using this pipeline's exact `expectations` field
across 6 of its skills at once — the **third** independent author on the
full-schema-match sub-case (after Phase 16's fluxcd, Phase 26's petekp).
`evanbacon/serve-sim` uses yet another field-name variant,
`expected_behavior` (neither `assertions` nor `expectations`) — a fourth
distinct flavor of the no-discriminator-signal bucket the other 8
corroborations hit. Nine authors total across all #11 sub-cases combined,
commented on the issue.

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `benedictking/context7-auto-research` | `23ff46058325` | 2026-04-21 | MIT | 1 | 1 | 16 |
| `bmad-labs/skills` | `088a427df8b0` | 2026-07-09 | MIT | 22* | 3 | 15 |
| `colbymchenry/codegraph` | `81e1f4a92fdb` | 2026-08-20 | MIT | 2 | 2 | 67,550 |
| `crafter-station/skills` | `ceef4cd58732` | 2026-08-17 | MIT | 8 | 1 | 109 |
| `crypto-com/crypto-agent-trading` | `41c3a8c877d1` | 2026-06-10 | Apache-2.0 | 2 | 2 | 19 |
| `davis7dotsh/better-context` | `864e5ba45256` | 2026-04-11 | MIT | 3 | 2 | 1,155 |
| `decathlon/tzatziki` | `ec2d27473c76` | 2026-08-18 | Apache-2.0 | 1 | 1 | 88 |
| `ejirocodes/agent-skills` | `6e805e4cc8a4` | 2026-06-25 | MIT | 7 | 1 | 5 |
| `evanbacon/serve-sim` | `14ad57ff9225` | 2026-07-17 | Apache-2.0 | 2 | 1 | 2,685 |
| `francyjglisboa/agent-skill-creator` | `f4f7d35eb242` | 2026-08-11 | MIT | 4 | 1 | 2,291 |
| `humanlayer/skills` | `3c2629142c5d` | 2026-08-13 | MIT | 5 | 2 | 385 |
| `iamzifei/wechat-article-publisher-skill` | `d3508c44248a` | 2026-08-12 | MIT | 1 | 1 | 154 |
| `module-federation/core` | `08fdc4dfbf4d` | 2026-08-19 | MIT | 4 | 1 | 2,617 |
| `rainlib/ai-storyboard` | `6610fd33f348` | 2026-01-11 | GPL-3.0** | 4 | 1 | 44 |
| `sammcj/agentic-coding` | `25cb214728a0` | 2026-08-20 | Apache-2.0 | 77 | 3 | 158 |
| `seflless/deepwiki` | `3ba91173780c` | 2026-02-12 | MIT | 1 | 1 | 23 |
| `superdesigndev/superdesign-skill` | `f9f05cd988c2` | 2026-08-21 | MIT | 1 | 1 | 436 |
| `vercel-labs/emulate` | `d0219d05818a` | 2026-08-19 | Apache-2.0 | 14 | 1 | 1,554 |
| `vince-winkintel/gitlab-cli-skills` | `70626ac9b979` | 2026-08-18 | MIT | 48 | 1 | 45 |
| `xobotyi/cc-foundry` | `3f58b07df062` | 2026-08-17 | MIT | 65 | 1 | 19 |

\* excludes 1 cross-corpus duplicate, 23 on disk. \*\* audit-only posture
applied for consistency.

**Structure notes**: `vince-winkintel/gitlab-cli-skills` (48), `sammcj/
agentic-coding` (77), and `xobotyi/cc-foundry` (65) are this phase's hidden
collections, all audited in full. `vercel-labs/emulate`'s gitleaks findings
(9, sampled and confirmed) are all realistic-looking example credentials for
each service it emulates (`sk_test_emulated`, `test_token_admin`) — a direct
consequence of the tool's own stated purpose (local API emulation).

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 29 cohort: 19 more low-sitemap-count repos (scale batch 15) — a genuine filename-case defect on the pilot's highest-star repo, one sitemap false positive dropped

Fifteenth batch (2026-08-21, seed 29). Funnel: 2,448 pairs → 356 held
excluded → 1,400-repo tier → 14-call GraphQL screen, zero failures → seeded
draw. 20 drawn; **19 vendored**.

`steel-dev/cli` discovered **zero** skills and, on investigation, contains no
`SKILL.md`/`skill.md` file anywhere in the repo at all — its `init_agent_guide.md`
is a CLI-generated onboarding doc, not a Claude Skills-format file. A genuine
sitemap false positive (skills.sh's crawler indexed it via loose
keyword-adjacency, not a real skill), dropped consistent with the standing
character-check discipline. Not counted toward this phase's totals, no
replacement drawn.

**`graphify-labs/graphify` (108,962★, the pilot's new highest star count)
also discovered zero skills — but for a genuinely different, more
consequential reason**: it ships real, well-formed skill content at
`graphify/skill.md` — **lowercase**, not the spec-required `SKILL.md`.
Confirmed by reading the file directly: legitimate frontmatter, a working
slash-command definition. On a case-sensitive filesystem (Linux, most CI),
this skill would silently fail to load in a real Claude Code session exactly
the way it failed `find_skill_dirs`' discovery here — `find_skill_dirs`
correctly mirrors the spec's case-sensitive requirement rather than papering
over it. Kept vendored (not dropped) with this finding recorded: the pilot's
single highest-star repo drawn so far ships a skill broken by filename case,
likely working only by accident on the author's own case-insensitive
development machine (macOS/Windows default).

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `agentrhq/authsome` | `0d756011a6fe` | 2026-07-05 | MIT | 1 | 1 | 82 |
| `aidotnet/moyucode` | `9fa0412ff1d5` | 2026-01-28 | MIT | 59 | 1 | 83 |
| `arjitj2/swiftui-design-principles` | `791d22d73f84` | 2026-03-15 | MIT | 1 | 1 | 23 |
| `atlassian/forge-skills` | `6d3897463bdb` | 2026-08-17 | Apache-2.0 | 6 | 1 | 20 |
| `bevibing/tutor-skills` | `397110c9fefb` | 2026-02-28 | MIT | 2 | 2 | 1,105 |
| `buildgreatproducts/plaid` | `002ea9330057` | 2026-05-05 | MIT | 1 | 1 | 214 |
| `graphify-labs/graphify` | `b2cd36267456` | 2026-08-20 | Apache-2.0 | 0* | 1 | 108,962 |
| `imsus/pi-extension-minimax-coding-plan-mcp` | `357c0856d7c6` | 2026-04-12 | MIT | 2 | 1 | 15 |
| `lancelin111/crawl4ai-skill` | `e1bdcff8034f` | 2026-03-11 | MIT | 1 | 1 | 16 |
| `lottiefiles/motion-design-skill` | `f9a8a041b851` | 2026-05-18 | MIT | 1 | 1 | 1,307 |
| `nshipster/sosumi.ai` | `afec623b039a` | 2026-08-11 | MIT | 1 | 1 | 464 |
| `pashov/skills` | `c577eb7799c3` | 2026-07-09 | MIT | 5 | 1 | 1,088 |
| `qianwen-ai/qianwenai-deploy` | `3669469d3227` | 2026-08-05 | Apache-2.0 | 1 | 1 | 9 |
| `render-oss/skills` | `3f2aa30eaadc` | 2026-08-18 | MIT | 21 | 3 | 76 |
| `saisudhir14/claude-skills` | `edef07bc111f` | 2026-03-31 | MIT | 9 | 1 | 8 |
| `sawyerhood/dev-browser` | `73fe10f045b9` | 2026-07-14 | MIT | 1 | 1 | 6,554 |
| `seo-skills/seo-audit-skill` | `bbca017b5608` | 2026-07-20 | MIT | 2 | 1 | 385 |
| `specstoryai/agent-skills` | `9454d3f2b9ac` | 2026-01-30 | Apache-2.0 | 6 | 1 | 33 |
| `yaojingang/yao-meta-skill` | `f5d8f681372e` | 2026-08-17 | MIT | 1 | 1 | 2,397 |

\* real skill content exists but is undiscoverable due to a filename-case
defect in the source repo — see note above; correctly not counted as an
audited skill.

Also this phase: two more issue #11 corroborations (`agentrhq/authsome`,
bare-shape bucket; `atlassian/forge-skills`, the exact-`expectations`
full-schema-match sub-case — fourth author now) — logged, and per the user's
direction this session now pivots to actually resolving #11/#12 rather than
continuing to accumulate corroborations.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 30 cohort: 20 more low-sitemap-count repos (scale batch 16) — first AGPL-3.0, a genuine cross-skill absolute-path leak

Sixteenth batch (2026-08-21, seed 30). Funnel rebuilt fresh this session (prior
scratchpad tooling doesn't persist across sessions): 2,448 sitemap pairs → 365 held
excluded → 1,380-repo tier → 14-call GraphQL screen (0 call-errors after fixing a
real bug in the rebuilt screening script itself — see `../audit-pilot/RESULTS.md`'s
Phase 30 section) → seeded draw. 20 drawn, **20/20 vendored**, no rejections.

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `alchaincyf/ilya-sutskever-skill` | `056284b63c2d` | 2026-05-28 | MIT | 1 | 1 | 47 |
| `alextangson/feishu_skills` | `7569ef14adee` | 2026-03-26 | MIT | 10 | 2 | 65 |
| `anivar/zod-skill` | `bb0620d90ed0` | 2026-08-08 | MIT | 1 | 1 | 20 |
| `atlassian/atlassian-mcp-server` | `94a30436435f` | 2026-07-27 | Apache-2.0 | 6 | 1 | 979 |
| `baidu-netdisk/bdpan-storage` | `b0f22b465a47` | 2026-08-11 | Apache-2.0 | 2 | 1 | 202 |
| `dhruvanbhalara/skills` | `28b936d5c2ee` | 2026-07-10 | MIT | 43 | 1 | 29 |
| `done-0/value-realization` | `ba9ea9599815` | 2026-08-01 | MIT | 1 | 1 | 527 |
| `fastapi/fastapi` | `c3f316b7e814` | 2026-08-19 | MIT | 1 | 1 | 101,742 |
| `flyer-li/paper-analyst` | `1e385a3f6f86` | 2026-04-26 | MIT | 1 | 1 | 66 |
| `honra-io/drizzle-best-practices` | `c1bc07273a84` | 2026-05-24 | MIT | 1 | 1 | 20 |
| `iart-ai/webgl-animation-skills` | `50697d659fbf` | 2026-06-22 | MIT | 3 | 1 | 8 |
| `op7418/guizang-ppt-skill` | `c91369c449d3` | 2026-08-07 | AGPL-3.0 | 1 | 1 | 24,572 |
| `raphaelbarbosaqwerty/maestro-dev-skills` | `53ce7c0e9dc9` | 2026-02-05 | MIT | 1 | 1 | 8 |
| `screenci/screenci` | `fedeafcc72be` | 2026-08-18 | MIT | 2 | 2 | 3 |
| `shanraisshan/claude-code-best-practice` | `d4df0acdfe1c` | 2026-08-21 | MIT | 9 | 2 | 64,829 |
| `shawnchee/caveman-skill` | `82af154a91dd` | 2026-04-06 | MIT | 1 | 1 | 71 |
| `theplasmak/faster-whisper` | `1c8d6a682c56` | 2026-02-22 | MIT | 1 | 1 | 10 |
| `tinyfish-io/tinyfish-cookbook` | `2751ef766264` | 2026-08-17 | MIT | 30 | 1 | 2,119 |
| `wandb/skills` | `b93e46c7a2be` | 2026-08-06 | Apache-2.0 | 3 | 1 | 66 |
| `xiaomimimo/mimo-skills` | `fa2a81225730` | 2026-04-24 | MIT | 1 | 1 | 90 |

**License note**: `op7418/guizang-ppt-skill` — first AGPL-3.0 in the pilot, confirmed
by raw `LICENSE` read. OSI-approved and copyleft-restrictive on redistributing/
modifying the licensed work itself, not on reading it — standing audit-only posture
applies (read + report with short attributed quotes; never copy/adapt into
SkillArtisan's own MIT-licensed material), same as every other non-permissive license
already in this table.

**Structure note**: `dhruvanbhalara/skills` (43 found vs. 1 listed) ships a genuine,
verified cross-skill absolute-path leak — `file:///Users/dhruvanbhalara/Desktop/
Github%20Projects/skills/...` in 4 sibling-skill cross-reference links across 3
skills (`dart-optimization` ×2, `flutter-debugging`, `flutter-native`), the author's
real local dev path, not a placeholder. Confirmed by direct `grep -rl` against the
clone. Same class as the glebis (Phase 5) and jimliu (Phase 22) findings, not a new
mechanism. Full write-up, including two confirmed-non-issue gitleaks findings and a
third zero-reserved-word phase: `../audit-pilot/RESULTS.md`'s Phase 30 section.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 31 cohort: 20 more low-sitemap-count repos (scale batch 17) — an attributed cross-corpus duplicate, a real product repo's full test suite in scope

Seventeenth batch (2026-08-21, seed 31). Funnel: 2,448 sitemap pairs → 385 held
excluded → 1,360-repo tier → 14-call GraphQL screen (0 call-errors) → seeded draw.
20 drawn, **20/20 vendored**, zero rejections.

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `bartundmett/skills` | `a126a4cb557c` | 2026-01-25 | MIT | 3 | 1 | 11 |
| `branding5/social-media-image-sizes` | `76e189160207` | 2026-04-30 | MIT | 2 | 1 | 5 |
| `carmahhawwari/ui-design-brain` | `38f04c5a1dee` | 2026-02-27 | MIT* | 1 | 1 | 871 |
| `cocoon-ai/architecture-diagram-generator` | `4b9087d55268` | 2026-05-13 | MIT | 1 | 1 | 6,984 |
| `contentful/skills` | `1f817475b9ad` | 2026-08-20 | MIT | 9 | 1 | 37 |
| `fugazi/test-automation-skills-agents` | `bb4fcdf9dcc4` | 2026-08-19 | MIT | 9 | 1 | 224 |
| `glittercowboy/taches-cc-resources` | `1757615b99ab` | 2026-04-01 | MIT | 12 | 1 | 1,967 |
| `harperfast/skills` | `c4b7bb3e6be2` | 2026-08-17 | Apache-2.0 | 2 | 1 | 3 |
| `hookdeck/webhook-skills` | `0760add95b3f` | 2026-08-20 | MIT | 158 | 3 | 81 |
| `iserter/laravel-claude-agents` | `8868214ee3fe` | 2026-04-20 | MIT | 15 | 2 | 43 |
| `itechmeat/llm-code` | `f53cef9bbfba` | 2026-08-01 | MIT | 38 | 2 | 22 |
| `lambdatest/agent-skills` | `0491a3a29aa1` | 2026-07-24 | MIT | 72 | 2 | 357 |
| `lucaperret/agent-skills` | `e7039ec02cda` | 2026-03-20 | MIT | 6 | 1 | 6 |
| `matlab/agent-skills-playground` | `1a4cdb907868` | 2026-08-12 | Modified-BSD-3-Clause* | 29 | 1 | 167 |
| `mc3545dada/mspm0-skill` | `0cea5a0b234f` | 2026-07-28 | MIT | 1 | 1 | 354 |
| `mempalace/mempalace` | `3e56979fb456` | 2026-08-20 | MIT | 12 | 1 | 58,519 |
| `rmyndharis/antigravity-skills` | `3eff4af253b3` | 2026-08-03 | MIT | 307 | 2 | 1,354 |
| `schrepa/graft` | `c9425b89a417` | 2026-03-26 | Apache-2.0 | 1 | 1 | 5 |
| `teng-lin/notebooklm-py` | `3bb0c1850ac4` | 2026-08-17 | MIT | 1 | 1 | 18,841 |
| `trading212-labs/agent-skills` | `aaed5cc2ebc5` | 2026-02-04 | MIT | 1 | 1 | 101 |

**License notes (the two `*` rows, both NOASSERTION on the GraphQL screen, resolved
favorably by raw read)**:

- `carmahhawwari/ui-design-brain` — plain MIT text, just filed as `LICENSE.txt` rather
  than the extension-less `LICENSE` GitHub's classifier expects.
- `matlab/agent-skills-playground` — a real, deliberately modified BSD-3-Clause: the
  MathWorks copyright, standard 3-clause redistribution/attribution language, plus a
  fourth clause restricting use "solely for use in conjunction with MathWorks products
  and service offerings." A new license character for this pilot (restrictive-but-real,
  not a standard SPDX match) — same audit-only posture as every other non-permissive
  license already in this table (read + report, never copy/adapt into SkillArtisan's
  own MIT-licensed material).

**Structure/dedup notes**:

- `hookdeck/webhook-skills` (158 found vs. 1 listed) and `rmyndharis/antigravity-skills`
  (307 found vs. 2 listed, this phase's largest single repo) were both investigated
  directly before committing to a full audit — Hookdeck's own real per-vendor
  webhook-integration library (`metadata.author: hookdeck` throughout) and a large
  personal multi-domain skill collection respectively, both genuine content, neither an
  aggregator/link-list.
- `branding5/social-media-image-sizes` and `matlab/agent-skills-playground` each ship
  one exact-content duplicate (flat-vs-nested packaging; the same skill bundled by
  value into two separate demo packages) — both caught automatically by
  `dedup_by_content`, not counted twice.
- **A sixth, newly-distinct cross-corpus-duplicate character**: `glittercowboy/
  taches-cc-resources` and the already-held `cfircoo-claude-code-toolkit` share 6
  identically-named skills, 3 byte-identical (`create-plans`, `debug-like-expert`,
  `create-subagents`). Confirmed as an **attributed downstream adaptation**, not
  silent copying — `cfircoo-claude-code-toolkit`'s own README explicitly credits
  "glittercowboy — Inspiration and Claude Code patterns," and glittercowboy's repo
  history predates cfircoo's. The 3 byte-identical skills are excluded from this
  phase's net-new count (already counted when `cfircoo-claude-code-toolkit` was
  originally audited); glittercowboy's other 9 skills are genuinely new and stay
  counted. **680 raw discovered, 678 after within-cohort dedup, 675 net-new to the
  pilot.**
- `teng-lin/notebooklm-py` (18,841★) ships `SKILL.md` at its repo root, sweeping its
  whole real CLI-tool codebase into scope — the pilot's largest single-skill finding
  volume (2,342 pattern findings, 78 gitleaks hits), fully traced to the product's own
  test fixtures and documented default paths, not a security issue. Full write-up:
  `../audit-pilot/RESULTS.md`'s Phase 31 section.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.

## Phase 32 cohort: 20 more low-sitemap-count repos (scale batch 18) — a bundled real Chrome automation profile, a wholesale Anthropic-skills copy

Eighteenth batch (2026-08-21, seed 32). Funnel: 2,448 sitemap pairs → 405 held
excluded → 1,340-repo tier → 14-call GraphQL screen (0 call-errors) → seeded draw.
20 drawn, **20/20 vendored**, zero rejections.

| Repo | Pin | Commit date | License | Found | Sitemap | Stars |
|---|---|---|---|---:|---:|---:|
| `agentara/skills` | `dcb37f647711` | 2026-08-15 | MIT | 23 | 2 | 445 |
| `alibaba-flyai/flyai-skill` | `f89974d2bd48` | 2026-08-21 | MIT | 1 | 1 | 917 |
| `alibaba/skill-up` | `85661758ff44` | 2026-08-20 | Apache-2.0 | 19 | 1 | 647 |
| `antonbabenko/terraform-skill` | `0a3a4a66e990` | 2026-07-03 | Apache-2.0* | 1 | 1 | 2,292 |
| `anycap-ai/anycap` | `6314153ee599` | 2026-07-29 | MIT | 9 | 3 | 42 |
| `catalyst-cooperative/agent-skills` | `249de8cbd265` | 2026-08-16 | MIT | 2 | 2 | 3 |
| `cdeistopened/skill-stack` | `d607d66198b2` | 2026-07-07 | MIT | 81 | 1 | 27 |
| `changeflowhq/skills` | `1ce59f2ca0e5` | 2026-02-10 | MIT | 4 | 1 | 9 |
| `crustdata/skills` | `f2a0906836bf` | 2026-08-07 | MIT | 8 | 2 | 7 |
| `fanzhidongyzby/openclaw-serper` | `9b2411287c8c` | 2026-02-11 | MIT | 2 | 1 | 4 |
| `home-assistant/core` | `32a484642853` | 2026-08-21 | Apache-2.0 | 6 | 1 | 90,026 |
| `iamzhihuix/happy-claude-skills` | `f49e7782a551` | 2026-04-19 | MIT | 13 | 3 | 303 |
| `joeseesun/qiaomu-design` | `39dac8238a6b` | 2026-07-10 | MIT | 1 | 2 | 498 |
| `larksuite/meegle-cli` | `0702dd3461a3` | 2026-08-20 | MIT | 1 | 1 | 210 |
| `leonxlnx/unlazy` | `ed9e8d2b5919` | 2026-08-11 | MIT | 1 | 1 | 586 |
| `openaccountant/skills` | `f5abe381f24b` | 2026-04-09 | MIT | 44 | 3 | 57 |
| `raphaelsalaja/userinterface-wiki` | `256a954080c8` | 2026-03-17 | MIT | 1 | 2 | 873 |
| `shmulc8/captain-obvious` | `4da9b1d9ce4c` | 2026-08-16 | MIT | 1 | 1 | 12 |
| `talkstream/ru-text` | `73dc04a492fc` | 2026-08-17 | MIT | 4 | 1 | 209 |
| `tencent/agentlymail` | `b4cccb1eecd7` | 2026-08-19 | Apache-2.0* | 1 | 1 | 36 |

**License note (the two `*` rows, both NOASSERTION on the GraphQL screen, resolved
favorably)**: `antonbabenko/terraform-skill` and `tencent/agentlymail` are both plain
Apache-2.0, just with non-standard attribution text ahead of the license body
(Anton Babenko's own header; Tencent's standard open-source preamble) that kept
GitHub's classifier from confidently matching either.

**Structure/dedup notes**:

- `cdeistopened/skill-stack` (81 found vs. 1 listed) mirrors 8 skills byte-identically
  into `public/skills/` and `.claude/skills/` (caught automatically by
  `dedup_by_content`) and separately bundles a **full 17-skill wholesale copy of
  Anthropic's official skills collection** under `.claude/skills/anthropic-skills/`
  (`pdf`, `docx`, `pptx`, `xlsx`, `skill-creator`, `mcp-builder`, `canvas-design`, and
  10 more) — 3 of the 17 are exact byte-for-byte matches against already-held copies
  (excluded from the net-new count), the other 14 are different snapshots of the same
  upstream content and stay counted per the standing convention.
- `alibaba/skill-up` (19 found vs. 1 listed) is itself a real Go tool for evaluating
  Agent Skills; 3 of its discovered entries are genuine `e2e/testdata/` Go test
  fixtures with no frontmatter, correctly erroring individually (exit-code-4
  contract), confirmed by reading the fixtures' own source-file documentation.
- `changeflowhq/skills`' `stealth-browser` ships a full committed Chrome automation
  profile (extensions, preferences) so automated sessions look like "a normal browser
  with real extensions" — investigated end-to-end (no real `Cookies`/`History`/
  `Login Data` files present, both flagged findings traced to Chrome's own internal
  integrity token and an ad-blocker's public filter-list URL paths, not real secrets
  or a leaked personal profile). Full write-up: `../audit-pilot/RESULTS.md`'s Phase 32
  section.
- `agentara/skills`' `world-cup-predictor` has a genuine, high-volume
  `absolute-user-path` leak (118 hits, all the same author path baked into one
  committed dashboard data file) — same concentrated-single-source shape as Phase
  22's jimliu.

**Runnability confirmed**: same Python-only dependency chain as the rest of
`scripts/`; no repo-specific tooling needed to audit any of them.
