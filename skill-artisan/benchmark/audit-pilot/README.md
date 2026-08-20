# Audit-mode real-world pilot

Validates `scripts/audit.py` itself — its checklist findings and upgrade-vs-rebuild
judgment — against skills that already exist in the wild, authored by someone else,
for real use, not built for this benchmark. This is a different kind of test than
`../corpus/`: the corpus tests the *authoring/eval engine* (with-skill vs. without-skill
deltas on skills authored from a `seed.md`); this pilot tests the *audit* path, which
until now had never been run against real third-party skills at all — see the Gap
Table's row 31/32 status and the master spec's "Auditing existing skills" section.

User-initiated 2026-08-20: pick skills from `github.com/mattpocock/skills`, run
`audit.py report` against them as-is, and — critically — grade the audit's own findings
independently (true-positive / false-positive / missed-issue) rather than trusting the
tool's self-report (Phase 1/2). After reviewing those results, the user asked to expand
to `benchmark/vendored/daymade-claude-code-skills`, an already-vendored second corpus
(Phase 3), and separately asked to research further candidate repos for a future third
source, to keep pushing this methodology toward "hundreds" of skills across multiple
independently-authored corpora. Cost was tracked throughout so each expansion decision is
made on real data, not a guess — see `RESULTS.md`'s cost-data sections.

## Sources and pins

**Phase 1/2 — `mattpocock-skills`**:
- **Repo**: `https://github.com/mattpocock/skills`
- **Actually audited from**: the locally cached `mattpocock-skills` Claude Code plugin
  release, not a fresh clone — this machine already has it installed
  (`~/.claude/plugins/cache/claude-plugins-official/mattpocock-skills/1.2.3/`), and a
  versioned plugin release is a more citable pin than an arbitrary HEAD SHA.
- **Pinned version**: `1.2.3` (`.claude-plugin/plugin.json`). Latest changelog entry at
  this pin: PR #783, "wizard: remove the time estimate" (see `CHANGELOG.md` in the
  cached plugin dir for the full history).
- Author: Matt Pocock (aihero.dev) — chosen partly *because* the source is well-regarded
  and actively maintained, which makes it a meaningful false-positive test (does the
  audit invent problems on skills that are already decent?), not just a true-positive
  test on obviously-rough material.

**Phase 3 — `daymade-claude-code-skills`**:
- **Repo**: `https://github.com/daymade/claude-code-skills`
- **Actually audited from**: `benchmark/vendored/daymade-claude-code-skills/`, already
  cloned and pinned in this repo for the existing 16-skill corpus — no new clone, license
  check, or pinning decision needed. See `../vendored/README.md` for the pin's own history.
- **Pinned commit**: `d24f6d13f57688d8436b78647519f0ae49b37adf`, user-confirmed 2026-08-16.
- **Coverage**: all 92 skill directories `_common.find_skill_dirs` discovers under this
  root — including the 13 already used as authoring seeds for `../corpus/`, since
  `audit.py` had never been run against any of them directly (the corpus work only ever
  used their `seed.md`/adapted evals, never audited the origin skill's own SKILL.md).
  Chosen as the second corpus specifically because it's already vetted and credited in
  this repo — zero new sourcing/licensing decisions needed to reach it, per `SCALING.md`'s
  readiness assessment.

**Phase 4 — `mukul975-anthropic-cybersecurity-skills`**:
- **Repo**: `https://github.com/mukul975/Anthropic-Cybersecurity-Skills`
- **Actually audited from**: `benchmark/vendored/mukul975-anthropic-cybersecurity-skills/`,
  cloned specifically for this phase. See `../vendored/README.md` for the pin record.
- **Pinned commit**: `4c0b700ac5d280ba46695062077f0fe922ce3602` (`main` HEAD, 2026-08-08).
- **Coverage**: all 817 skill directories discovered — a security/cybersecurity-focused
  corpus, structurally uniform (`skills/<name>/SKILL.md`), chosen first among the four
  Phases 4–7 candidates for having zero structural surprises after independent
  verification (see the Phases 4–7 plan) and the largest single-domain skill count.

## Coverage

Phase 1 (8 skills, deliberately spread across maturity tiers) ran first as a pilot; see
the table below. Phase 2, run the same day after the user reviewed Phase 1's findings and
asked to expand, covered the remaining 27 skills — full coverage of all 35 skill
directories in the repo (25 shipped per `plugin.json`, 4 `misc/`, 6 `in-progress/`).
Phase 2 used the same method (audit + independent read) but didn't need a full deep-read
of every skill: 23 of 27 showed only the already-characterized boilerplate pattern from
their audit report alone, so the direct-source investigation focused on the 4 that showed
something new. See `RESULTS.md` for the full findings from both phases, including two
confirmed bugs found in SkillArtisan's own tooling (both fixed, with regression tests)
and the third-party-mode gap that's identified but not yet fixed.

## Phase 1 selected skills (8, spanning maturity tiers on purpose)

Picked to stress both ends of the audit's judgment, not cherry-picked for a favorable
result — a deliberate spread across the plugin's own maturity signal (which directory
a skill lives in, and whether it's wired into `plugin.json`'s shipped `skills` list):

| Skill | Category | Shipped in plugin.json? | Why picked |
|---|---|---|---|
| `tdd` | engineering | yes | mature, well-known workflow — false-positive test |
| `code-review` | engineering | yes | mature, structurally complex (subagent dispatch) |
| `domain-modeling` | engineering | yes | mature, ADR/CONTEXT.md-aware |
| `wizard` | engineering | yes | mature, recently patched (1.2.3 changelog) |
| `writing-for-agents` | productivity | yes | mature, meta-relevant — same subject `creating-skills` has strong opinions on |
| `grilling` | productivity | yes | mature, trigger-phrase-driven rather than task-driven |
| `git-guardrails-claude-code` | misc | **no** — not in plugin.json's skills array | built but seemingly not wired in — outsider case |
| `loop-me` | in-progress | **no** — lives under `skills/in-progress/` | explicitly unfinished — true-positive test |

## Methodology

1. Run `python scripts/audit.py report <skill-path> --json` and the text form for each
   skill, unmodified, no `--timelessness`/`--lifecycle` flags supplied (those are
   external judgment calls the script doesn't presume — leaving them unset shows what
   the decision gate does on its structural signals alone).
2. Independently read each skill's `SKILL.md` and bundled files in full — not derived
   from `audit.py`'s own output — before looking at what the audit said.
3. Grade every PASS/FAIL/WARN item as accurate (matches an independent read) or
   inaccurate (false positive: flags something not actually wrong; false negative: the
   script silently passed something that reading the skill shows is actually broken).
   MANUAL items are graded on whether the audit correctly identified them as needing a
   human read, not scored right/wrong themselves.
4. Separately judge the upgrade-vs-rebuild decision against independent judgment of the
   skill's real state.
5. Explicitly avoid circularity: grading is done by reading the source skill directly,
   not by asking `creating-skills`'/`audit.py`'s own reasoning to check its own output.
6. Log wall-clock time and rough read volume (lines/files per skill) as the cost signal
   for scale-up decisions — no per-token instrumentation exists for this kind of inline
   work, so this is a proxy, same "advisory only" caveat the harness's own `cost`
   subcommand carries.
7. **Phase 3 addition, once the corpus grew past a few dozen skills**: use
   `aggregate_findings.py` to group findings by checklist item and narrow to a review
   queue, then sample representatively within each group rather than reading every
   flagged skill — see `RESULTS.md`'s "Phase 3 methodology note" for exactly how this
   traded some rigor for scale, and what stayed exhaustive (every low-volume/high-stakes
   finding) versus what was sampled (high-volume WARN categories).

## Status

Full coverage across three independently-sourced corpora: 35/35 `mattpocock-skills` +
92/92 `daymade-claude-code-skills` + 817/817 `mukul975-anthropic-cybersecurity-skills` =
**944 real-world skills audited**. Six confirmed bugs found in SkillArtisan's own tooling
(two in `security_scan.py`, three in `validate.py`/`audit.py` combined across all
phases — see `CHANGELOG.md` for the exact breakdown), all fixed with regression tests;
deferred gaps tracked as GitHub issues (`gh issue list --label audit-gap`), not just
CHANGELOG prose. Phase 4 also validated `aggregate_findings.py`'s chunked/resumable
execution mode under a real shell timeout — zero results lost. Shipped as `v2.4.6`
(Phase 1/2) and follow-up releases for Phases 3 and 4 (see `CHANGELOG.md` for exact
versions). See `RESULTS.md` for the full findings and cost data, and `SCALING.md` for the
readiness assessment, including Phase 4's finding that a high review-queue hit rate isn't
always "more bugs to fix" — sometimes it's a corpus whose genre legitimately triggers
portability/secret-shaped checks throughout. Next: Phases 5–7 (`glebis`, `alirezarezvani`,
`obra`) per the approved roadmap
(`~/.claude/plans/home-eonraider-desktop-verified-candida-imperative-thompson.md`).
