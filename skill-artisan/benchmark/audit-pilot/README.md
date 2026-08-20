# Audit-mode real-world pilot — mattpocock/skills

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
tool's self-report. Also explicitly asked to track pilot cost so a later decision about
expanding from 8 skills to a larger set is made on real data, not a guess.

## Source and pin

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
   for the scale-up decision — no per-token instrumentation exists for this kind of
   inline work, so this is a proxy, same "advisory only" caveat the harness's own
   `cost` subcommand carries.

## Status

Full repo coverage complete (35/35 skills, both phases). Two confirmed bugs found in
SkillArtisan's own tooling (`security_scan.py`, `validate.py`), both fixed with
regression tests (`tests/test_security_scan.py`, `tests/test_validate.py`); one
identified false-positive mechanism left unfixed by design (see `RESULTS.md`'s Bug #2).
Shipped as `v2.4.6`. See `RESULTS.md` for the full findings, cost data, and
`SCALING.md` for the readiness assessment behind scaling this methodology to hundreds of
skills across multiple source repos, including `aggregate_findings.py` — a new tool
that mechanically reproduces this run's own review-queue triage.
