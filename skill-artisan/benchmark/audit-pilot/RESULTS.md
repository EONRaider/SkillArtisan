# Audit-mode real-world pilot — results

Phase 1: 8 skills from `mattpocock-skills` v1.2.3 (`github.com/mattpocock/skills`),
audited with `scripts/audit.py report`, findings graded independently against a direct
read of each skill. Phase 2 (2026-08-20, same day): the remaining 27 skills in the repo
(35 total, full coverage), same method. Phase 3 (2026-08-20, same day, after user sign-off
on scaling): all 92 skills in `benchmark/vendored/daymade-claude-code-skills` — a second,
independently-authored, already-vendored/pinned corpus, audited via the new
`aggregate_findings.py` — 127 real-world skills audited in total across two corpora. See
`README.md` for source pins and methodology, `SCALING.md` for the readiness assessment
that led into Phase 3.

## Headline

**Yes, `audit.py` adds real value, and it keeps finding real things as the sample grows.**
Across 127 skills in two independently-authored corpora it produced a true positive
corroborated **13 separate times** (a reserved-word naming defect — every single
"claude"/"anthropic"-named skill across both repos, 13 of 13, sits outside its own
author's shipped/mature list), one genuine architectural judgment call worth raising with
an author, and — in the process of verifying its own findings — surfaced **four confirmed,
reproducible defects in SkillArtisan's own shipped tooling** (two in `security_scan.py`,
two in `validate.py`, one of the four found only because Phase 3 used a second, much
larger and more heterogeneous corpus than Phase 1/2's). **All four are now fixed**, each
with a regression test, each verified directly against the real skill that triggered it,
and the full 87-test suite still passes. It also has a clear, unfixed systematic weakness
(three checklist items FAIL on 100% of third-party skills regardless of quality) and one
newly-flagged, not-yet-decided gap (a real frontmatter field, `agent:`, that at least one
skill uses meaningfully but SkillArtisan's spec knowledge doesn't recognize).

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
| `setup-ts-deep-modules` | FAIL `path-references-exist`: "Missing referenced files: ./src/packages/README.md" | **false positive — actually fixed as a side effect of Bug #2's Round 2 fix; originally mis-documented as unfixed, corrected below** |
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

**Round 2, found in Phase 3**: the `#`-comment fix wasn't the whole story — the same
`\binput\s*\(` prose-match recurred inside **Python docstrings**, which don't start with
`#`. Two real, independent hits in `daymade-claude-code-skills`: `excel-automation`'s
`apply_input_cell()` docstring, *"Style a cell as user input (blue font, green fill)"*,
and `asr-transcribe-to-text`'s module docstring, *"Outputs per input (flat under
OUTPUT_DIR...)"*. Neither is a real `input()` call. **Fixed properly this time**: added
`docstring_line_numbers()`, which finds every line inside a triple-quoted Python string
literal once per `.py` file, and the interactive-input check now skips those lines too
(not just `#` lines). Verified: both skills now report `security-pattern-checks — no
pattern findings` (well, `excel-automation` reports other unrelated MEDIUM findings, but
`blocking-interactive-input` is gone). Regression test added:
`test_prose_mentioning_input_in_a_docstring_is_not_flagged` in the same file. Two
real-world confirmations for the same root defect in one afternoon — the fix needed to be
"strip narrative text before pattern-matching," not "handle this one specific narrative
shape."

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
- **Originally reported as unresolved, corrected below**: `setup-ts-deep-modules` hit the
  *same underlying check* through what I first described as "an inline (non-fenced)
  sentence" needing a judgment call the fenced-block fix couldn't make. That description
  was wrong — the sentence is `` `Packages are deep modules — see [src/packages/README.md](./src/packages/README.md) before adding or importing one.` ``,
  wrapped in a single-backtick inline code span, not bare prose. I missed that at the time.
  It turned out to be the exact same mechanism as Round 2's fix below, and got fixed as a
  side effect of that fix without me noticing — caught only while smoke-testing
  `aggregate_findings.py`'s new chunking mode against this corpus during Phase 4 prep and
  seeing the review queue come back one skill short of the documented count. Verified
  directly: `setup-ts-deep-modules` now reports `path-references-exist — every relative
  link resolves`. No further code change needed — this entry exists to correct the record.

**Round 2, found in Phase 3**: a *third* independent mechanism for the same check, found
across 3 skills in `daymade-claude-code-skills` — `docs-cleaner`, `meeting-minutes-taker`,
`youtube-downloader` — all had link-syntax examples wrapped in **inline single-backtick
code spans**, not fenced blocks: `` `[doc.md](reviewed-document)` `` as a cautionary
example of what *not* to write (`meeting-minutes-taker`'s own words: *"Do NOT create
markdown links to files that don't exist"* — flagged as if it were exactly that mistake),
and `` `![Thumbnail](URL)` `` showing image-embed syntax. **Fixed**: inline code spans
(`` `...` ``, no backtick or newline inside) are now stripped the same way fenced blocks
are, before the link scan runs. Verified: all 3 now report `path-references-exist — every
relative link resolves`; rerunning the aggregator across the whole 92-skill corpus
afterward showed `path-references-exist` at 100% PASS, confirming no other skill in either
corpus had a *real* broken link masked by this — every single instance found across both
pilots was one of these three narrative-example shapes. Regression test added.
Trade-off accepted knowingly (same one as the fenced-block fix): a real link written
stylistically inside backticks would now go unchecked — judged a smaller risk than 100%
of the false positives actually observed.

## Bug #3 (fixed): `scripts/audit.py` crashed outright on a real `evals.json` shape

Running the new `aggregate_findings.py` against all 92 `daymade-claude-code-skills`
crashed partway through with `AttributeError: 'list' object has no attribute 'get'` —
not a WARN, not a FAIL, a Python exception that would have killed `audit.py bulk` too
(its own docstring promises "Exit codes: 0 report generated ... regardless of pass/fail",
which this violated). Root cause: `check_evals_present` assumed `evals.json` is always
`{"evals": [...]}` and called `.get()` on whatever `json.loads()` returned.
`github-sensitive-data-cleanup`'s `evals/evals.json` is a bare JSON *list* — a real shape
in the wild, not hypothetical: this project's own `benchmark/corpus/github-sensitive-data-cleanup/meta.json`
already documents adapting exactly this file's bare-list shape when it was used as a
corpus seed, months before this defect in `audit.py` itself was found. **Fixed**:
`check_evals_present` now accepts a bare list (counts it directly), the existing
`{"evals": [...]}` wrapper (unchanged), or reports a clean FAIL — never a crash — for
anything else. Verified: the skill now reports `PASS — 6 eval case(s)`, and the full
92-skill aggregation run completes without incident. Regression test added:
`tests/test_audit.py` (bare list counted, wrapped dict still works, short list still
warns, an unexpected scalar shape fails cleanly instead of crashing).

## Bug #4 (fixed): `references-toc-for-long-files` only recognized one literal phrase

The single highest-impact false positive found across both pilots. The check's whole
logic was `"table of contents" not in text.lower()` — an exact-phrase substring match.
Across the 92-skill `daymade-claude-code-skills` corpus this FAILed **59 of 92 skills**
(69%) on first run. Investigated a sample of 6: 4 had a real, working `## Contents`
heading with a genuine anchor-link list right there (`bilibili-source`'s
`references/bilibili_api.md` being the clearest case — a proper TOC, just not spelled
"Table of Contents"); 2 genuinely had no TOC of any kind. **Fixed**: added
`TOC_HEADING_RE`, matching a `## Contents` / `## TOC` / `## Index` heading (case-insensitive)
as an equally valid TOC, alongside the original literal-phrase check. Verified on the
whole corpus: FAILs dropped from 59 to 50 — the fix caught the false positives without
touching the genuine gaps (spot-checked 4 of the remaining 50 directly: all 4 truly have
no navigational heading of any kind, confirming these are real, not another missed
variant). Deliberately didn't chase every conceivable synonym further (e.g. "Overview"
sections, which are usually prose introductions, not link lists) — the fix targets the
specific, confirmed failure mode, not every heading word that might loosely relate to
navigation. Regression test added: `tests/test_audit_references_toc.py` (Contents/TOC/Index
headings all recognized, literal phrase still works, genuine absence still FAILs, short
files never need one).

## Corroborated further: 10 more reserved-name true positives, and a new true-positive shape

`daymade-claude-code-skills` added **10 more** "claude"-named skills, all correctly
FAILed by the same reserved-word check as Phase 1/2's 3 — bringing the total to **13 of
13** across both corpora, zero exceptions. It also surfaced a true positive Phase 1/2
never saw: **directory/skill-name mismatches**. `fixing-claude-export-conversations`
lives in a directory named `claude-export-txt-better`, and `developing-ios-apps` lives in
`iOS-APP-developer` — both flagged by `skills-ref` (the official validator `validate.py`
wraps) with "Directory name '...' must match skill name '...'". This is a real packaging
defect distinct from naming style — a plugin loader that resolves skills by directory path
could genuinely fail to find these by their declared name. Not a bug in SkillArtisan;
correctly delegated to the official spec tool and correctly surfaced.

## Flagged, not fixed: a real frontmatter field SkillArtisan's spec doesn't recognize

`competitors-analysis` FAILed `frontmatter-valid` with "Unrecognized frontmatter field(s):
agent" — it declares `context: fork` *and* `agent: general-purpose`, using the second
field to specify which subagent type should handle the forked invocation. That's a
coherent, real usage pattern, but `agent` appears nowhere in `validate.py`'s
`CLAUDE_CODE_ONLY_FIELDS` allowlist or in `references/surface-matrix.md`. Unlike the four
bugs above, this isn't fixed: I don't have confirmation this is an actual Claude
Code-recognized field (vs. a bespoke convention specific to this skill's own author) that
would justify allowlisting it, and guessing wrong risks quietly accepting a field Claude
Code itself doesn't act on either. Flagged for the same kind of decision as the
third-party-mode gap below, not code-fixed speculatively. Tracked:
[#5](https://github.com/EONRaider/SkillArtisan/issues/5).

## The systematic issue: three checklist items are FAIL on nearly every third-party skill

Holds at the larger scale too. `evals-present`, `security-scan-marker-current`, and
`lifecycle-classified` FAILed on all 35 mattpocock skills and effectively all 92 daymade
skills (`security-scan-marker-current`/`lifecycle-classified` at ~100%; `evals-present`
slightly under only because Bug #3's fix now credits real bare-list evals files). Same
conclusion as Phase 1/2, now with a much larger sample behind it — not fixed, still a
scope decision:

- `security-scan-marker-current` is close to pure noise for a third-party audit — it's a
  packaging-step artifact, not a property of the skill's actual security (the *next* item,
  `security-gitleaks-clean`, already independently re-scans and correctly passed all 127).
- `evals-present` and `lifecycle-classified` gesture at something substantively real (no
  regression tests exist; has anyone thought about whether this skill ages as models
  improve) even though the specific artifact they look for is SkillArtisan's own.

**Recommendation**: give `audit.py report`/`bulk` a third-party-source mode (or infer it —
e.g. no `.claude-plugin/` ownership marker in the tree) that reports these three
differently: still informative, but not counted as a checklist FAIL against a skill that
was never meant to go through this pipeline. As shipped today, an outside author reading
this report would reasonably conclude the tool doesn't understand their skill wasn't
authored for it — which undercuts trust in the *other*, real findings alongside it. Not
fixed yet — a design/scope decision, not a one-line patch. Tracked:
[#4](https://github.com/EONRaider/SkillArtisan/issues/4).

## Phase 3 methodology note: sampling, not exhaustive reads

`SCALING.md` predicted, before Phase 3 ran, that a larger corpus would need statistical
sampling rather than a full manual read of every flagged skill, the way Phase 1/2 read
all 35. That held: `aggregate_findings.py`'s review queue narrowed 92 skills to 84 with a
non-boilerplate finding, still too many to read individually. Actual method used: grouped
the 84 by which checklist item fired (11 distinct item-ids), read a representative sample
per group (2-6 skills, more for the highest-volume items) plus every low-volume/high-stakes
item in full (all 12 `frontmatter-valid` FAILs, all 5 `rebuild`-decision skills, the single
`forward-slash-paths-only` and `agent`-field cases), and treated a sample's outcome as
representative of its group rather than re-deriving it per skill. This is *not* the same
rigor as Phase 1/2's full-corpus read — flagged explicitly rather than implied away: the
~40 `description-pushy-imperative` and ~12 `no-time-sensitive-info` WARNs were sampled
(3-4 each), not individually verified. One sampled-but-not-fixed observation:
`description-pushy-imperative` also flags descriptions using "use whenever"/"use for"
phrasing instead of the literal "use when" it checks for — roughly 16 of 39 such WARNs
have this kind of equivalent-but-differently-phrased trigger language. Judged a real but
softer case than the four fixed bugs (no evidence either phrasing performs differently in
actual trigger-accuracy testing, only that they're semantically similar) — documented, not
code-changed. Tracked: [#6](https://github.com/EONRaider/SkillArtisan/issues/6).

## Cost data (127 skills, three phases)

No subagents were spawned in any phase — everything ran inline across two conversation
sessions. This pilot's cost profile is structurally different from, and much cheaper
than, the abandoned 5-arm Best-in-Market Scorecard comparative benchmark that hit
near-total trigger-detection failure and tens-of-millions-of-token costs at >1 concurrent
worker (see `../corpus/README.md`'s dated correction) — that path spawns subagents per
arm per skill; this one never does, in any phase, at any scale tried so far.

- **Script cost**: 127 total audit runs (35 individual `audit.py report` calls in
  Phase 1/2, 92 via `aggregate_findings.py` in Phase 3) — deterministic, no LLM calls,
  the full 92-skill Phase 3 run completes in well under a second once the four tool bugs
  it exposed were fixed (before that, it crashed partway through on Bug #3 — see above).
- **Grading cost**: Phase 1 read all 8 skills' full source (677 lines) exhaustively.
  Phase 2 read all 27 audit reports for triage, deep-read the 4 with real findings.
  Phase 3 didn't attempt exhaustive reads — see "Phase 3 methodology note" above — it
  grouped 84 flagged skills by which of 11 checklist items fired and sampled
  representatively, reading every low-volume/high-stakes item in full and a
  statistically-reasonable sample (2-6 skills) of each high-volume item.
- **Total wall-clock**: ~6 min (Phase 1) + ~15 min (Phase 2) + ~35 min (Phase 3: the
  92-skill run, the crash investigation and fix, three more bug investigations and fixes,
  four new regression tests, and three full aggregation reruns to confirm each fix).
  Phase 3 found roughly one confirmed bug per 9 minutes of wall-clock — the marginal
  finding rate did not drop as the corpus grew from 35 to 127 skills.
- **Zero shell-script bugs from audit.py/security_scan.py/validate.py themselves in
  Phase 1/2** — the one real tooling snag there was self-inflicted (a `zsh` loop variable
  named `path`, colliding with zsh's special `$path`/`$PATH` array). Phase 3, by
  contrast, found four real bugs in the tools themselves — the larger, more
  heterogeneous, more real-world-messy daymade corpus (financial/audio/docs tooling
  authored by many different real workflows, versus mattpocock's more uniform,
  single-author engineering-workflow style) surfaced defect classes Phase 1/2 never hit,
  consistent with SCALING.md's expectation that a second, differently-sourced corpus
  would add real signal, not just more of the same.
- **No token instrumentation exists for this kind of inline work** (same "advisory only"
  caveat the harness's own `run_authoring.py cost` subcommand carries) — wall-clock and
  line-count are proxies, not an exact spend figure.

## Status and next steps

127 skills audited across two independently-sourced, real-world corpora (35/35 mattpocock
+ 92/92 daymade, full coverage of both). Four tool bugs found and fixed, each with a
regression test, each verified against the real skill that triggered it (87-test suite,
all passing). Two systematic gaps identified and documented, not yet fixed by design (the
third-party-mode recommendation, and the unrecognized `agent:` frontmatter field) — real
scope/spec decisions, not one-line patches. One softer, sampled-not-verified observation
(the "use whenever"/"use for" phrasing gap) left for a future pass if it turns out to
matter.

The finding rate did not taper off between Phase 1/2 and Phase 3 — if anything, the
larger, more heterogeneous second corpus found *more* real tooling defects per skill
audited, not fewer. That's the strongest evidence yet that this methodology scales:
`SCALING.md`'s prediction (execution stays cheap, grading needs sampling past a few dozen
skills, a second differently-sourced corpus adds real signal) held on all three counts.

## Phase 4: mukul975/Anthropic-Cybersecurity-Skills (817 skills)

Third corpus, part of the approved Phases 4–7 roadmap
(`~/.claude/plans/home-eonraider-desktop-verified-candida-imperative-thompson.md`). Pinned
`4c0b700a` (main HEAD, 2026-08-08) — see `../vendored/README.md` for the full pin record.
817 real skill directories, 817/817 fully discoverable by the existing `find_skill_dirs`
(uniform `skills/<name>/SKILL.md` depth), matching the live count verified before pinning.

### Chunked execution — resilience actually exercised, not just planned

Ahead of this phase, `aggregate_findings.py` was hardened per the user's explicit request
to evaluate resiliency: catch *any* exception per-skill (not just the two originally
anticipated), and support `--start`/`--end` chunked runs plus a `--merge` mode to
recombine them. Smoke-testing that against known-good mattpocock/daymade data also
surfaced and fixed a real documentation error (`setup-ts-deep-modules` was mis-documented
as an unfixed false positive; it was actually already fixed as a side effect of Bug #2's
Round 2 — corrected above).

The hardening paid off immediately: this corpus runs meaningfully slower per skill
(~0.8s vs. sub-second for the first two corpora — real `gitleaks` invocations against
larger reference content, not a hang), and the first unchunked attempt hit a shell-level
timeout partway through. Because execution was already split into nine ~100-skill chunks,
each writing its own JSON immediately on completion, **zero results were lost** — the
timeout only cost re-running one chunk, not the whole corpus. Final run: 9/9 chunks
succeeded, 817/817 skills audited, **0 errors** (no crash-style bug this phase, unlike
Phase 3's Bug #3).

### Headline: not every false positive should be fixed — this phase is why

Phase 4's dominant lesson isn't a new bug — it's a boundary case for the *four already-fixed*
checks that Phase 1–3 could fix cleanly (checks that were unambiguously matching the wrong
thing: a comment, a template example, a crash). This corpus is security-education content,
and it stress-tests exactly the class of check that's supposed to catch something risky:
absolute paths, non-portable syntax, secret-shaped strings, dangerous-function-shaped
code. Investigated four high-volume categories directly; all four are **real, confirmed
matches on genuinely present text — not bugs — and deliberately left unfixed**, because a
fix would mean teaching the checks to recognize "this looks fake" or "this looks like
teaching content," which is exactly the kind of semantic judgment a pattern-matcher can't
safely make without risking a worse failure mode: silently missing a real leaked secret or
a real dangerous call dressed up to look like an example.

| Check | Skills | What's actually there | Why not fixed |
|---|---|---|---|
| `security-gitleaks-clean` | 27 | A crafted-fake AWS key (`AKIAEXPOSEDKEY123456`), the canonical jwt.io tutorial token, placeholder tokens (`USER_TOKEN`, `YOUR_API_KEY`) | Some of these (the fake AWS key, the JWT) have moderate-to-*high* entropy specifically because they're built to look realistic for teaching — entropy-based filtering would also silently suppress real leaked secrets shaped the same way. This is exactly the limitation the project's own README already discloses ("a clean scan is a gate, not a guarantee"). |
| `security-pattern-checks` — `absolute-user-path` | 34 | Fictional forensic evidence paths (`C:\Users\suspect\Documents\...`, `C:\Users\jsmith\Downloads`) in digital-forensics teaching content | No reliable signal distinguishes "fictional example evidence path" from "author's real leaked path" — a real leak could just as easily use a plausible-looking username. |
| `security-pattern-checks` — `forward-slash-paths-only` | 84 | Real Windows-native tool command syntax (`SharpDPAPI.exe /target:C:\Users\bob\AppData\...`) | This *is* the correct, required syntax for the actual Windows tools being taught (SharpDPAPI, SharpChrome) — there's no forward-slash equivalent to teach instead. Unambiguously legitimate content, not a portability mistake. |
| `security-pattern-checks` — `dangerous-code-pattern` | 7 | A malware-scanning tool's own pattern-definition metadata, e.g. `(r"os\.system\(", "os.system() execution")` — the match is the human-readable *label* describing what the pattern detects, not a real call | Low volume (7 of 817) and genuinely hard to fix safely: distinguishing "this occurrence is a descriptive label" from "this occurrence is a real invocation" via regex risks new false negatives on the very thing this check exists to catch. |

### What *is* new: a corpus-defining frontmatter gap

Unlike the false positives above, `frontmatter-valid` FAILed **817 of 817** skills on a
genuinely new, structured pattern: a consistent family of framework-mapping metadata
fields (`author`, `domain`, `mitre_attack`, `nist_csf`, `subdomain`, `tags`, `version`,
plus optionally `d3fend_techniques`, `mitre_f3`, `atlas_techniques`, `nist_ai_rmf`
depending on which security frameworks a skill maps to) — not sloppy authoring, a real,
coherent taxonomy used uniformly across the whole corpus, none of it recognized by
`validate.py`. Same class of gap as the `agent:` field (issue #5), but 817x the scale and
a coherent field family rather than one isolated field — tracked as its own issue:
[#7](https://github.com/EONRaider/SkillArtisan/issues/7).

### Corroborated, not new

- **`description-pushy-imperative`**: 668 of 817 (82%) — the same "use for"/"use during"
  vs. literal "use when" gap already tracked as
  [#6](https://github.com/EONRaider/SkillArtisan/issues/6), now at much higher incidence
  than Phase 3's sampled ~40%. Commented on the existing issue rather than opening a new
  one — same root cause, stronger evidence it's a real, common, legitimate convention.
- **`references-toc-for-long-files`**: 194 FAILs, sampled — every one checked genuinely
  lacks any Contents/TOC/Index heading. Bug #4's fix (Phase 3) remains correctly
  calibrated: no false positives reintroduced by this corpus's very different reference-doc
  style (many short, topic-focused reference files rather than a few long ones).
- **1 `rebuild`-decision skill** (`detecting-command-and-control-over-dns`, 1,379 lines) —
  confirmed genuinely oversized, correct verdict.

### Cost and hit rate — a third data point

Review-queue hit rate: **817 of 817 (100%)** — higher than daymade's 91%, far higher than
mattpocock's 11%. Consistent with `SCALING.md`'s already-corrected prediction (hit rate is
corpus-dependent, not a constant) rather than a new surprise, and the *reason* is now
concrete rather than abstract: security/forensics content inherently contains large
volumes of the exact shapes (paths, credential-like strings, dangerous-sounding function
names) these checks are built to catch, whether or not anything is actually wrong.
Execution: 9 chunks, ~70–90s each (real `gitleaks` cost, not a hang), no subagents, no
crash after hardening. Total wall-clock for Phase 4 including chunking, triage across
~2,300 individual findings (grouped into 9 checklist-item categories, sampled per the
established methodology — not read individually), and this write-up: roughly 45–60
minutes. **944 skills now audited across three independently-sourced corpora.**
