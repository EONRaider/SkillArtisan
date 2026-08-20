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
