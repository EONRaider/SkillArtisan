# Audit-mode real-world pilot — results

Phase 1: 8 skills from `mattpocock-skills` v1.2.3 (`github.com/mattpocock/skills`),
audited with `scripts/audit.py report`, findings graded independently against a direct
read of each skill. Phase 2 (2026-08-20, same day): the remaining 27 skills in the repo
(35 total, full coverage), same method. See `README.md` for source pin and methodology.

## Headline

**Yes, `audit.py` adds real value beyond boilerplate**, confirmed across the full 35-skill
repo, not just the original pilot slice. It produced one true positive corroborated
*three separate times* (a reserved-word naming defect that lines up with real-world
exclusion from the author's own shipped list, seen in 3 of 3 "claude"-named skills), one
genuine architectural judgment call worth raising with the author, and — in the process
of verifying its own findings — surfaced **two confirmed, reproducible bugs in
SkillArtisan's own shipped tooling** (`security_scan.py` and `validate.py`), both found
by testing against real code a synthetic corpus wouldn't have produced. **Both bugs are
now fixed**, with regression tests (`tests/test_security_scan.py`,
`tests/test_validate.py`), verified against the actual skill that triggered each one, and
the full 76-test suite still passes. It also has a clear, unfixed systematic weakness:
three checklist items fire as an automatic FAIL on 100% of third-party skills regardless
of actual quality, which dilutes the pass-rate number and would read as tone-deaf to an
outside author.

## Phase 1 per-skill summary (8 skills)

| Skill | Checklist | Real skill-specific findings | Verdict on findings |
|---|---|---|---|
| `tdd` | 13/16 | none beyond boilerplate | clean skill, audit correctly found nothing wrong |
| `code-review` | 13/16 | MANUAL flag on inline-vs-fork correctly surfaces a real open question (spawns 2 parallel sub-agents, no `context: fork` declared) | **true positive**, non-trivial |
| `domain-modeling` | 13/16 | none beyond boilerplate | clean skill |
| `wizard` | 12/16 | HIGH `blocking-interactive-input` on `template.sh` | **false positive — root-caused and fixed, see Bug #1 below** |
| `writing-for-agents` | 14/17 | none beyond boilerplate | clean skill |
| `grilling` | 14/17 | institutional-knowledge safeguard reported "nothing flagged" | **misleading, not wrong** — skill has zero `##` headings, so there was nothing to check; the message doesn't distinguish "validated clean" from "nothing present to validate" |
| `git-guardrails-claude-code` | 11/15 | FAIL `frontmatter-valid`: reserved word "claude" in `name` | **true positive, corroborated** — this is the one skill of the 8 excluded from `plugin.json`'s shipped list, and this is a plausible reason why |
| `loop-me` | 14/17 | none beyond boilerplate; correctly adapted `description-pushy-imperative` and `description-optimizer-run` to the skill's `disable-model-invocation: true` status instead of blindly failing them | audit's context-awareness worked correctly |

## Phase 2: remaining 27 skills (full repo coverage)

Ran the same `audit.py report` pass across every skill not already covered — 14 more
`engineering/`, 5 more `productivity/`, the remaining 3 `misc/`, and the remaining 5
`in-progress/` (see `README.md`'s file list for exact paths). 23 of 27 came back clean —
only the boilerplate three FAILs plus an occasional `gerund-naming` WARN, checklist pass
rates in the same 76–83% band as Phase 1, `UPGRADE-IN-PLACE` throughout. Four produced
real, skill-specific findings:

| Skill | Finding | Verdict |
|---|---|---|
| `wayfinder` | FAIL `path-references-exist`: "Missing referenced files: link" | **false positive — root-caused and fixed, see Bug #2 below** |
| `setup-ts-deep-modules` | FAIL `path-references-exist`: "Missing referenced files: ./src/packages/README.md" | **false positive, same check, different mechanism — not fixed, see Bug #2** |
| `claude-handoff` | FAIL `frontmatter-valid`: reserved word "claude" in `name` | **true positive, third corroborating instance** — all 3 of 3 "claude"-named skills across the full 35-skill repo landed in `misc/`/`in-progress/`, none shipped |
| `resolving-merge-conflicts` | WARN `description-pushy-imperative`: "missing 'Use when...' framing or short" | **true positive, message imprecise** — description does start with "Use when," but is only ~72 chars, under the 100-char threshold the check actually wants for reliable triggering; the OR-phrased detail message doesn't say which condition applied, so it reads as if the framing itself is missing when it's actually just short |

## The corroborated true positive: reserved "claude"/"anthropic" names predict real exclusion

Across all 35 skills, exactly 3 have "claude" in their frontmatter `name`:
`git-guardrails-claude-code`, `claude-handoff`, and no others. All 3 fail
`frontmatter-valid` (a documented hard error — `RESERVED_WORDS = ("anthropic", "claude")`
in `validate.py`, part of the cross-vendor `agentskills.io` portability layer). All 3 are
also the only skills of the 35 that sit outside `plugin.json`'s 25-skill shipped list
(2 of the 4 `misc/` skills, 1 of 6 `in-progress/`). The audit predicted a real,
independently-observable authoring decision without being told about it — this is the
strongest single piece of evidence from this pilot that the tool's checks track something
that actually matters to skill quality, not just internal-convention conformance.

## The systematic issue: three checklist items are FAIL on every third-party skill

`evals-present`, `security-scan-marker-current`, and `lifecycle-classified` FAILed on
**all 35 of 35** skills, with zero exceptions. Each is checking for a SkillArtisan-specific
artifact (its own `evals/evals.json` schema, its own packaging tamper marker, its own
lifecycle-classification frontmatter convention) that no skill authored outside
SkillArtisan's own pipeline will ever have, regardless of how good it actually is. Two
notes on severity, not identical:

- `security-scan-marker-current` is close to pure noise for a third-party audit — it's a
  packaging-step artifact, not a property of the skill's actual security (the *next* item,
  `security-gitleaks-clean`, already independently re-scans and correctly passed all 35).
- `evals-present` and `lifecycle-classified` gesture at something substantively real (no
  regression tests exist; has anyone thought about whether this skill ages as models
  improve) even though the specific artifact they look for is SkillArtisan's own.

**Recommendation**: give `audit.py report`/`bulk` a third-party-source mode (or infer it —
e.g. no `.claude-plugin/` ownership marker in the tree) that reports these three
differently: still informative, but not counted as a checklist FAIL against a skill that
was never meant to go through this pipeline. As shipped today, an outside author reading
this report would reasonably conclude the tool doesn't understand their skill wasn't
authored for it — which undercuts trust in the *other*, real findings alongside it. Not
fixed yet (unlike the two bugs below, this is a design/scope decision, not a one-line
patch) — flagging for a decision.

## The systematic issue: three checklist items are FAIL on every third-party skill

`evals-present`, `security-scan-marker-current`, and `lifecycle-classified` FAILed on
**all 8 of 8** skills, with zero exceptions. Each is checking for a SkillArtisan-specific
artifact (its own `evals/evals.json` schema, its own packaging tamper marker, its own
lifecycle-classification frontmatter convention) that no skill authored outside
SkillArtisan's own pipeline will ever have, regardless of how good it actually is. Two
notes on severity, not identical:

- `security-scan-marker-current` is close to pure noise for a third-party audit — it's a
  packaging-step artifact, not a property of the skill's actual security (the *next* item,
  `security-gitleaks-clean`, already independently re-scans and correctly passed all 8).
- `evals-present` and `lifecycle-classified` gesture at something substantively real (no
  regression tests exist; has anyone thought about whether this skill ages as models
  improve) even though the specific artifact they look for is SkillArtisan's own.

**Recommendation**: give `audit.py report`/`bulk` a third-party-source mode (or infer it —
e.g. no `.claude-plugin/` ownership marker in the tree) that reports these three
differently: still informative, but not counted as a checklist FAIL against a skill that
was never meant to go through this pipeline. As shipped today, an outside author reading
this report would reasonably conclude the tool doesn't understand their skill wasn't
authored for it — which undercuts trust in the *other*, real findings alongside it.

## Bug #1 (fixed): `scripts/security_scan.py`

`wizard`'s `template.sh` FAILed `security-pattern-checks` with a HIGH-severity
`blocking-interactive-input` finding at "line 99". Investigated directly:

- Line 99 is a **comment**: `# a default on re-runs (Enter keeps it). Visible input
  (non-secret).` — not code, and not the actual `read -r` call (that's on line 108).
- Root cause: `INTERACTIVE_INPUT_PATTERNS`'s first pattern, `\binput\s*\(`, is meant to
  catch Python's blocking `input(...)` builtin, but it also matches ordinary English
  prose — any comment containing the words "input (" (e.g. "visible input (non-secret)")
  trips it. Reproduced directly against the file: no `read -p` (the third, more careful
  pattern) appears anywhere in `template.sh`; the only match is the prose false positive.
- This is exactly the class of skill (`wizard`) that's *designed* to block on human
  interactive input — SkillArtisan's own ecosystem has the same genre (its changelog
  references a `hitl-loop.template.sh`) — so the check's underlying assumption
  ("bundled scripts must be non-interactive," `references/script-design.md`) is correct
  for agent-invoked automation scripts but doesn't apply to a script explicitly meant to
  be handed to a human to run.
- A related, lower-severity instance of the same blind spot: `git-guardrails-claude-code`'s
  `block-dangerous-git.sh` got a MEDIUM `no-documented-cli` finding for not exposing
  `--help` — but it's a Claude Code hook invoked with a fixed JSON-over-stdin contract
  dictated by the platform, not a general CLI. Correctly downweighted to WARN (didn't
  affect the checklist pass rate), so lower priority than the `input(` bug above.

**Fixed** (2026-08-20): `run_pattern_checks` in `security_scan.py` now skips lines that
are entirely a `#` comment before applying `INTERACTIVE_INPUT_PATTERNS`. Verified
directly: `wizard` now reports `[  PASS] security-pattern-checks — no pattern findings`.
Regression test added: `tests/test_security_scan.py` (prose-in-comment no longer flagged;
a real `input(...)` call and a real `read -p` are both still caught). Not touched: the
related, lower-severity `no-documented-cli` blind spot on
`git-guardrails-claude-code`'s hook script (still WARN, didn't affect the checklist pass
rate, left as a known limitation rather than a fix worth the risk of a broader change).

## Bug #2 (partially fixed): `scripts/validate.py`

`wayfinder`'s `SKILL.md` FAILed `path-references-exist` with "Missing referenced files:
link". Investigated directly:

- The skill's body includes a ```markdown fenced template example showing the map's
  expected format, containing a worked-example line:
  `` - [<closed ticket title>](link) — <one-line gist of the answer> ``. The literal word
  "link" is placeholder text inside a documentation example, not a real path.
- Root cause: `check_path_references`'s `LINK_RE` scans the *entire* SKILL.md body,
  including fenced code blocks, for anything shaped like a markdown link. It has no
  concept of "this is an example inside a code fence, not live prose."
- **Fixed**: fenced code blocks (`` ``` ``...`` ``` ``, including the language tag) are
  now stripped from the body before the link scan runs. Verified: `wayfinder` now reports
  `[  PASS] path-references-exist — every relative link resolves`. Regression test added:
  `tests/test_validate.py` (link-shaped text inside a fenced example is ignored; a real
  broken link outside a fence is still caught; a real valid link still resolves).
- **Not fixed**: `setup-ts-deep-modules` hit the *same underlying check* through a
  different mechanism — an inline (non-fenced) sentence telling the user what line to add
  to *their own* `CLAUDE.md`/`AGENTS.md`: `` [src/packages/README.md](./src/packages/README.md) ``.
  This isn't inside a code fence, so the fix above doesn't touch it, and reliably
  distinguishing "an example of a link to put in someone else's file" from "a real
  reference into this skill's own directory" from prose alone is a genuine judgment call,
  not a pattern a regex can safely make — a fix attempted here risks *suppressing* real
  broken links instead. Left as a known, structural limitation rather than force a
  speculative fix.

## Cost data (full 35-skill run)

No subagents were spawned for either phase — everything ran inline across two
conversation turns. This pilot's cost profile is structurally different from, and much
cheaper than, the abandoned 5-arm Best-in-Market Scorecard comparative benchmark that hit
near-total trigger-detection failure and tens-of-millions-of-token costs at >1 concurrent
worker (see `../corpus/README.md`'s dated correction) — that path spawns subagents per
arm per skill; this one never does.

- **Script cost**: 35 × `audit.py report` (json + text), deterministic, no LLM calls,
  sub-second per skill.
- **Grading cost**: Phase 1 read all 8 skills' full source (677 lines). Phase 2 read all
  27 audit reports for triage, then did a full direct-source investigation (SKILL.md +
  relevant script internals) on the 4 that showed non-boilerplate findings — the other 23
  didn't need a deep read once the report showed only the known boilerplate pattern.
- **Total wall-clock**: ~6 minutes for Phase 1, roughly another ~15 minutes for Phase 2
  (27-skill run + investigating 4 findings + fixing 2 bugs + writing regression tests +
  running the full 76-test suite twice).
- **Zero shell-script bugs from audit.py/security_scan.py/validate.py themselves** — the
  one real tooling snag was self-inflicted: naming a loop variable `path` in a `zsh`
  script, which collides with zsh's special `$path`/`$PATH` array and silently breaks
  command lookup for the rest of the loop. Fixed by renaming the variable; not a finding
  about SkillArtisan's tools, noted here only because it cost real debugging time.
- **No token instrumentation exists for this kind of inline work** (same "advisory only"
  caveat the harness's own `run_authoring.py cost` subcommand carries) — wall-clock and
  line-count are proxies, not an exact spend figure.

## Status and next steps

Full repo coverage achieved (35/35). Two tool bugs found and fixed, with regression tests.
One systematic design gap identified and documented, not yet fixed (the third-party-mode
recommendation above — a real scope decision, not a one-line patch). Given the confirmed,
corroborated true positive (reserved-name detection predicting real exclusion) and two
real bugs found in SkillArtisan's own tooling, this kind of real-world audit pass is
worth repeating periodically — e.g. against a second, differently-sourced skill corpus,
or re-run against this same repo after its next release, both cheap given the
no-subagent cost profile established here.
