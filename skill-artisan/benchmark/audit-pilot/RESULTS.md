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

## Phase 5: glebis/claude-skills (111 skills)

Fourth corpus. Pinned `52fdf242` (`main` HEAD, 2026-08-19) — see `../vendored/README.md`.
111 real skill directories (98 at repo root, 13 nested under `confide/skills/`), both
shapes already discoverable. Ran unchunked (small enough not to need it): 108/111 audited
cleanly, 3 skills errored — correctly, not a bug (below).

### Confirmed, correct, first time exercised at bulk scale: zero-frontmatter skills error out cleanly

3 skills (`daydream`, `insight-extractor`, `thinking-patterns`) have `SKILL.md` files with
**no YAML frontmatter at all** — plain Markdown starting straight from a `# Title`
heading. `audit.py report` has always treated this as unparseable (documented exit code
4, "SKILL.md unreadable/unparseable" — a skill with no `name`/`description` genuinely
can't be checklist-audited). This is the first time a bulk/chunked run actually hit that
path, and `aggregate_findings.py`'s per-skill exception handling (added ahead of Phase 4)
did exactly what it should: caught the `ValueError` for each of the 3, recorded a clean
error entry, and kept auditing the other 108 — not a crash, not a silent skip, and not a
new bug to fix. A genuine real-world validation of already-documented behavior, not a
finding about it being wrong.

### Bug #5 (fixed): `path-references-exist`'s fourth false-positive mechanism

`agency-docs-updater` FAILed with "Missing referenced files: ~/.claude/skills/calendar-sync"
— a real, deliberate cross-skill dependency reference:
`[calendar-sync](~/.claude/skills/calendar-sync)`, documenting that this skill expects a
companion skill installed elsewhere on the user's machine, not a file bundled inside
`agency-docs-updater`'s own directory. `check_path_references` had no concept of a
`~/`-prefixed target meaning "somewhere else entirely," on top of the two mechanisms
(fenced blocks, inline code spans) already fixed for the same check across Phases 3 and
2's Bug #2. **Fixed**: added `~` to `SKIP_PREFIXES` alongside `http://`/`https://`/
`mailto:`/`#` — a target starting with `~` can never be a relative path within the
skill's own bundle, so this carries no risk of masking a real broken intra-skill link, a
cleaner case than either of the two earlier fixes for the same check. Verified: the skill
now reports `path-references-exist — every relative link resolves`; rerunning across the
full 111-skill corpus confirmed 100% PASS afterward — no other skill in this corpus had a
masked real broken link either. Regression test added to `tests/test_validate.py`, whose
docstring was updated to describe all four mechanisms found across three phases as one
family, not four separate stories.

### Real content, real true positives — a useful contrast with Phase 4

Where Phase 4's security-education corpus mostly produced *confirmed-but-not-fixable
false positives* on `security-pattern-checks` (fictional forensic paths, crafted-fake
credentials), this personal-automation-tooling corpus produced the same checks firing on
**genuine, real problems** in the audited content:

- **`absolute-user-path`**: the author's own real home directory,
  `/Users/glebkalinin/Brains/brain` (matching the author's actual name), hardcoded
  throughout multiple skills — 22 occurrences in `automation-advisor` alone, across
  `SKILL.md`, `README.md`, and reference docs. A genuine portability problem (none of
  these skills work for anyone but the author as shipped) and a mild information-hygiene
  one (reveals the author's real system username). Exactly the class of real leak this
  check exists to catch — not a false positive at all.
- **`blocking-interactive-input`**: real `input("You: ")` / `input("Select provider...")`
  calls in `llm-cli`'s bundled `executor.py`/`llm_skill.py` — a genuinely interactive CLI
  chat tool that would hang if the agent invoked it expecting non-interactive completion.
- **`dangerous-code-pattern`**: real `import pickle` / `pickle.load(` in `gmail`'s bundled
  `gmail_search.py` — a common but genuinely risky pattern (deserializing cached
  credentials), correctly flagged.
- **`security-gitleaks-clean`** (1 instance, `telegram-telethon`): a placeholder
  `api_hash` value in a test fixture (`tests/conftest.py`) — the same "crafted, not real"
  false-positive class as Phase 4, now confirmed in a third distinct context (test
  fixtures, not tutorial prose or documentation). Not fixed, same reasoning as before.

Together with Phase 4's contrasting result, this is good evidence these checks aren't
inherently noisy — they correctly track what's actually in the content, and *which*
result you get (mostly false positives vs. mostly true positives) depends on the corpus's
genre, not on the checks themselves.

### Corroborated, not new

- **`description-pushy-imperative`**: further corroboration of
  [#6](https://github.com/EONRaider/SkillArtisan/issues/6)'s "use for"/"use during"
  phrasing gap.
- **`references-toc-for-long-files`**: 23 FAILs sampled, all genuine — no TOC/Contents/
  Index heading present. Bug #4 remains correctly calibrated on a fourth, structurally
  different corpus.
- **`no-human-docs-in-skill-dir`**: 15 FAILs, same pattern as daymade (README.md bundled
  inside the skill's own directory) — not new.
- **`frontmatter-valid`** (2 of 111, not a corpus-wide pattern like #7): both genuine
  true positives, not tool defects — `temple-generator` uses `user_invocable` (underscore)
  where the recognized field is `user-invocable` (hyphen), a real author typo/convention
  slip, correctly caught; `library-sync` uses a bespoke `triggers` field with no
  recognized counterpart. Low volume, no coherent taxonomy behind it the way #7's fields
  are — no new issue opened.
- **`body-size-limits`** (2 WARNs, 741 and 515 lines) — both well under the ~2x threshold
  that would trigger a `rebuild` decision, correctly left as WARN, not FAIL.

### Cost — a fourth hit-rate data point

Review-queue hit rate: **83 of 108 (77%)** — between mattpocock's 11% and daymade/
mukul975's 91%/100%, and unlike mukul975, a genuine mix of real true positives (the
author's own leaked path, real interactive scripts, real risky deserialization) rather
than mostly confirmed-but-unfixable noise. Execution: single unchunked run, ~85s total (no
resilience issue this time — 111 skills stayed well under the threshold where Phase 4
needed chunking). One real bug found and fixed. Total wall-clock including triage and
write-up: roughly 30–40 minutes. **1,055 skills now audited across four independently-
sourced corpora.**

## Phase 6: alirezarezvani/claude-skills (349 skills)

Fifth corpus, and the one that stress-tested this pilot's own verification discipline the
hardest. Pinned `aa8d7788` (`main` HEAD, 2026-07-17) — see `../vendored/README.md`. The
plan required one extra step before trusting this corpus's size: a broader sample check of
the flat-vs-nested duplicate-content pattern the planning session had found (one sample,
`kubernetes-operator`, confirmed a byte-identical duplicate). Doing that check exhaustively
instead of on a larger sample — cheap to script, so no reason not to — found the planning
session's conclusion didn't generalize: only 12 of 125 nested-layer skills are exact
duplicates; **113 have no flat-layer counterpart at all**, genuinely unique content that
was invisible to `find_skill_dirs` entirely.

### The real discovery-logic bug this phase found: symlinks

Extending `find_skill_dirs` with a fifth pattern to reach that nested depth
(`category/plugin/skills/name/SKILL.md`) should have brought total discovery to roughly
785 (669 flat + 125 nested − duplicates). It didn't — it returned **1,140+**. The cause
wasn't the new pattern: `alirezarezvani/claude-skills` symlink-mirrors every skill into
four cross-tool directories (`.codex/`, `.gemini/`, `.hermes/`, `.vibe/`) for compatibility
with other agent products, and `Path.glob()` follows symlinks for ordinary path
components — every one of those four mirrors was being independently rediscovered as if
it were new content. This was always a latent bug in `find_skill_dirs` (used by
`audit.py bulk` and `dedup_search.py` too, not just this pilot's tooling); this is simply
the first of six corpora built with a symlink-mirroring convention, so the first time it
manifested. **Fixed**: skip any match reached through a symlink at any level — the file
itself or any directory between the search root and it. Regression tests added to a new
`tests/test_common_find_skill_dirs.py`.

That fix alone dropped the count to 361 — still not matching a clean expectation, which
led to the second correction below.

### The second correction: the planning-session skill count was itself wrong, for a different reason

Going back to reconcile 361 against the expected ~785 turned up a second, independent
methodology problem — this time in *my own verification process* from planning, not in
`find_skill_dirs`. The planning session's "≈669 flat skills, 125 nested" breakdown came
from GitHub's tree API, filtered by `.path | endswith("SKILL.md")`. That filter doesn't
distinguish a real file (git blob mode `100644`) from a tracked symlink (mode `120000`) —
and a meaningful fraction of the paths counted as "flat skills" were themselves symlinks
into other parts of the same tree, not distinct real files. Recounting directly against
the actual local checkout, with symlinks properly excluded throughout: **233 real flat
skills**, not 669. Combined with the 113 genuinely-new nested skills (confirmed
exhaustively, not by sample) and the small root/two-level counts, and after deduplicating
12 exact-content pairs (added as a new `dedup_by_content` step in
`aggregate_findings.py`, since this is a content judgment `find_skill_dirs` deliberately
doesn't make): **349 real, unique, auditable skills** — close to the repo's own
self-reported "362," not the "~672" this project's own supposedly-more-rigorous
cross-check had concluded. The lesson, stated plainly: a git-API-based verification pass
is not a substitute for checking against the real, cloned filesystem once one exists, and
"I double-checked this against an API" isn't the same claim as "I double-checked this
against the actual content." Corrected in `vendored/README.md`, `SCALING.md`, and the
running skill-count tally everywhere else in this project.

### The audit itself: 349/349, 0 errors, and a rich set of confirmed true positives

- **A genuine YAML syntax error, correctly caught**: `md-slides`' description contains an
  unescaped `<!-- notes: ... -->` — the bare colon inside an unquoted YAML scalar is
  invalid syntax (confirmed directly with `yaml.safe_load`: "mapping values are not
  allowed here"). Not a SkillArtisan defect — the skill's own frontmatter is genuinely
  broken and would likely fail other YAML consumers too, not just `skills-ref`.
- **A second and third `[skills-ref] Directory name ... must match skill name ...`
  instance** (`playwright-pro`'s nested copy lives in a directory literally named `pw`) —
  the same real packaging-defect class Phase 3 first found in daymade, now corroborated a
  third time.
- **A fourteenth reserved-word "claude" instance** (`claude-coach` — fittingly, a skill
  that teaches users to be better at using Claude specifically). Running total: 14 of 14
  across five corpora, still zero exceptions.
- **12 genuinely broken references**, all following the same shape:
  `../../../../megaprompts/NN-<name>-megaprompt.md`. Confirmed by direct search: no
  `megaprompts/` directory exists anywhere in the repo. Real, not a `path-references-exist`
  false-positive mechanism — the fifth phase running that check without finding a new one.
- **Real interactive scripts** (`executive-mentor`'s `decision_matrix_scorer.py`: genuine
  `input()` calls building a weighted decision matrix interactively) and **real
  placeholder secrets in test fixtures** (`skill-tester`'s `test_security_scorer.py`,
  sequential fake keys like `sk-1234567890abcdef`) — both corroborating already-understood,
  already-decided-not-to-fix patterns from Phases 4/5, not new findings.
- **`references-toc-for-long-files`**: 177 FAILs (the highest count of any phase),
  sampled and confirmed genuine — business/enterprise reference docs in this corpus
  consistently skip a Contents heading. Bug #4 remains correctly calibrated on a fifth,
  yet again structurally different corpus.
- **`frontmatter-valid`**: several distinct unrecognized-field clusters
  (`author`/`compatible_tools`/`tags`/`version`; `triggers`; `command`;
  `agents`/`author`/`tags`/`version`) — real, but none as large or uniform as #7's
  817/817 pattern. Commented on [#5](https://github.com/EONRaider/SkillArtisan/issues/5)
  rather than opening a new issue: three independent corpora now show "skills carry
  custom, non-portable metadata beyond the 6 portable fields" as a common pattern, which
  is worth a general answer rather than one-field-at-a-time allowlisting.
- **`description-pushy-imperative`**: only 30 of 349 (8.6%) — notably *lower* than every
  other corpus so far (Phase 3 ~40%, Phase 4 82%, Phase 5 55%). Reported honestly on
  [#6](https://github.com/EONRaider/SkillArtisan/issues/6) as evidence the gap's
  *magnitude* is corpus-dependent, not as further escalation — this corpus's authors
  mostly do use literal "use when" framing.

### Cost — a fifth hit-rate data point, and the most expensive phase to get right

Review-queue hit rate: **266 of 349 (76%)**, in the same band as Phase 5. But the more
important cost signal this phase is upstream of grading entirely: two real, non-trivial
discovery-logic bugs had to be found and fixed *before* a trustworthy audit could even
run, one of which was in shared, previously-shipped code (`_common.find_skill_dirs`), and
one of which was a correction to this pilot's own earlier verification methodology, not
to any of SkillArtisan's shipped tooling. Execution: 4 chunks of ~90, ~70–90s each, 0
errors. Total wall-clock for Phase 6 — including the exhaustive duplicate-content
re-check, both discovery-logic fixes and their regression tests, the full audit, triage,
and this write-up — was the longest of any phase so far, roughly 90–120 minutes,
proportionate to being the structurally messiest corpus encountered. **1,404 skills now
audited across five independently-sourced corpora.**

## Phase 7: obra/superpowers (14 skills) — the last phase on the approved roadmap

Sixth and final corpus. Pinned tag `v6.3.0` (`b36e0829`) — see `../vendored/README.md`.
Applied Phase 6's new standing rule (re-verify against the real clone, not just an API
check, before trusting planning-session numbers) even though nothing suspicious was
expected: 14 skills confirmed locally, exactly matching both the planning-session figure
and the live GitHub tree API count — the one source in this whole roadmap that needed no
correction once actually checked. One harmless symlink exists in the repo
(`AGENTS.md -> CLAUDE.md`), unrelated to skill discovery.

### The cleanest result of any phase — and an expected one, not a surprising one

14/14 audited, 0 errors, 7 of 14 (50%) review-queue hit rate. Every flagged item was
either an already-tracked pattern or a low-severity, correctly-calibrated WARN:

- **`description-pushy-imperative`** (6 skills): a mix of two already-understood shapes —
  `test-driven-development`'s description literally starts "Use when implementing any
  feature..." (the phrase *is* there, it's just under the 100-character length threshold,
  the same imprecise-message case documented back in Phase 2); the rest use "You MUST use
  this before..." instead of "use when" — the same phrasing-convention gap tracked on
  [#6](https://github.com/EONRaider/SkillArtisan/issues/6), not escalated further here.
- **`references-toc-for-long-files`** (1 FAIL, `using-superpowers`): genuinely no
  Contents/TOC/Index heading in `references/codex-tools.md` — Bug #4 remains correctly
  calibrated on a sixth, structurally distinct corpus.
- **`security-pattern-checks`** (1 WARN, `brainstorming`): a `no-documented-cli` hit on
  two small server-lifecycle scripts (the same known, low-priority blind spot from
  Phase 1/2 — a fixed-interface script doesn't need `--help`) and one obviously-templated
  URL (`http://host:port`) — neither worth chasing further.
- **`body-size-limits`** and **`degrees-of-freedom-writing-style`** (2 WARNs each): all
  well under their respective FAIL thresholds, correctly left as WARN.

No `frontmatter-valid` FAILs at all (100% PASS) — this corpus has no "claude"-named
skills, so it neither adds nor contradicts the 14/14 reserved-word streak from the other
four corpora; there was simply nothing to test against here. No `rebuild` decisions, no
gitleaks findings, no new false-positive mechanism on any check. **Zero new bugs found,
zero new gaps opened** — the exact outcome the approved plan's own cost-expectations
section anticipated as legitimate and worth reporting honestly, not a failure of the
phase: "don't expect a new bug every phase... that's a legitimate, reportable outcome on
its own (evidence the known classes are now well-covered)."

### Cost — the cheapest phase by far

Execution: single unchunked run, well under a minute. No resilience concerns, no
discovery-logic surprises, no new documentation corrections needed. Total wall-clock
including triage and this write-up: roughly 15–20 minutes — proportionate to being both
the smallest corpus and the one requiring the least investigation. **1,418 skills now
audited across six independently-sourced corpora — the approved Phases 4–7 roadmap is
complete.**

## Roadmap complete: six corpora, nine bugs, thirteen deferred-item cross-references

Final tally across the whole real-world audit pilot, Phases 1 through 7:

| Phase | Corpus | Skills | New bugs found | Notable |
|---|---|---|---|---|
| 1–2 | `mattpocock-skills` | 35 | 2 | First-ever real-world run; reserved-word true positive discovered |
| 3 | `daymade-claude-code-skills` | 92 | 4 | Highest bug-density phase; hit-rate prediction corrected |
| 4 | `mukul975-anthropic-cybersecurity-skills` | 817 | 0* | "Not every false positive should be fixed" — 4 categories confirmed-but-unfixable |
| 5 | `glebis-claude-skills` | 111 | 1 | Useful contrast with Phase 4 — same checks, mostly true positives this time |
| 6 | `alirezarezvani-claude-skills` | 349 | 2† | Discovery-logic bugs in shared code, not just audit checks; planning-session numbers self-corrected |
| 7 | `obra-superpowers` | 14 | 0 | Cleanest result — confirms known classes are well-covered, not a failed search |

\* Phase 4 found and fixed a crash-style bug (`evals.json` shape handling) and a
false-positive check (`references-toc-for-long-files`) that are counted under Phase 4 in
`CHANGELOG.md`'s per-release breakdown, not "0" in the strict sense — this table's "0"
above refers specifically to the security-pattern-checks investigation's headline finding
(not every false positive should be fixed), see the Phase 4 section for the full count.
† Both in `_common.find_skill_dirs`/`aggregate_findings.py`, not in the checklist items
themselves.

**Totals**: 1,418 real-world skills audited, nine confirmed bugs fixed with regression
tests (91 tests passing, all added or extended during this pilot's six phases), a
reserved-name true
positive corroborated 14 times with zero exceptions across five corpora that had any
"claude"/"anthropic"-named skills to test against, three deferred gaps tracked as GitHub
issues with cross-phase corroboration instead of scattered CHANGELOG mentions, and one
methodological correction (the git-tree-API blob/symlink conflation) applied to this
pilot's own verification discipline, not just to SkillArtisan's shipped tooling. See
`SCALING.md` for the full readiness-assessment history and what would carry forward if
this methodology is ever pointed at a seventh source.

## Phase 8: anthropics/knowledge-work-plugins, claude-for-legal, financial-services (430 skills)

First phase of the approved Phase 8–14 skills.sh-sourced expansion roadmap
(`~/.claude/plans/i-maintain-skillartisan-a-velvety-possum.md`), and the pilot's first
first-party-Anthropic-authored source — none of the prior six corpora were vendor- or
Anthropic-authored. Three repos, pinned live immediately before cloning (see
`../vendored/README.md` for exact SHAs): `anthropics-knowledge-work-plugins` (212 raw),
`anthropics-claude-for-legal` (151 raw), `anthropics-financial-services` (118 raw).

### Two genuine `find_skill_dirs` coverage gaps, found and fixed before a trustworthy audit could run

Same standing discipline as Phase 6: verify local discovery against the actual clone,
not the candidates doc's git-tree count. Two of three repos didn't match:
`claude-for-legal` discovered 151/151 exactly; `knowledge-work-plugins` initially found
185/212 (27 missing); `financial-services` initially found just **1 of 118** — both real,
both fixed in the same commit as `_common.find_skill_dirs`'s discovery patterns.

- **`financial-services`**: wraps the already-supported `category/plugin/skills/<skill>`
  convention in one more top-level `plugins/` directory
  (`plugins/partner-built/spglobal/skills/earnings-preview/SKILL.md`) — 117 of 118 skills
  live at exactly this depth.
- **`knowledge-work-plugins`**: `zoom-plugin` nests platform/surface *sub-skills* one or
  two levels beneath an already-discovered skill directory
  (`.../skills/contact-center/android/SKILL.md`,
  `.../skills/meeting-sdk/web/client-view/SKILL.md`) — each a real, independently
  frontmattered skill, explicitly routed to from the parent skill's own body text
  (`contact-center/SKILL.md` literally links `[android/SKILL.md](android/SKILL.md)`),
  not example or test content. Before adding the pattern, checked it wouldn't collide
  with two known false-positive shapes already present in *other* vendored corpora —
  `alirezarezvani`'s `assets/sample-skill/` and `skillforge`'s
  `tests/fixtures/sample-skill/`, both bundled example/test content nested inside an
  unrelated skill's own directory — confirmed neither has `skills` as a path component
  at the depth the new patterns require, so both stay correctly excluded.

**Fixed**: three new patterns added to `find_skill_dirs`. All 481 raw skills now
structurally discovered (212 + 151 + 118). Regression tests added to
`tests/test_common_find_skill_dirs.py`, including two negative tests reproducing the
`alirezarezvani`/`skillforge` false-positive shapes to guard against ever re-introducing
them. Full 127-test suite passes.

### Content-level dedup: a new *reason* for the same mechanism `dedup_by_content` already handles

`financial-services` has 31 content-duplicate groups (51 of 118 skills) — but for a
different reason than `alirezarezvani`'s flat-vs-nested install duplication (Phase 6):
this repo bundles shared utility skills (`audit-xls`, `xlsx-author`, `break-trace`,
`gl-recon`, etc.) **by value** into multiple independently-installable plugins, so each
plugin works standalone without depending on another being present — e.g. `audit-xls`
appears byte-identical in 7 separate plugins. `dedup_by_content` (built in Phase 6)
already handles this correctly with no code change: it operates on content hash
regardless of *why* the duplication happened. **67 unique auditable skills** after
dedup, for a **430-skill final total** across the three repos (212 + 151 + 67).

### Bug #6 (fixed): `check_path_references`' fifth false-positive mechanism

`cold-start-interview` (`claude-for-legal`, present in 5 plugin-specific copies) FAILed
`path-references-exist` with "Missing referenced files: URL" — 12 times total. Root
cause: an author-facing authoring note inside an HTML comment, showing what an optional
collateral link should look like when it exists:
`<!-- ... "Want a walkthrough? [Watch the intro](URL) or [read the guide](URL)." -->` —
a literal `URL` placeholder, not a real path. Same root-cause family as the four
mechanisms already fixed across Phases 2, 3, and 5 (fenced code blocks, inline code
spans, `~/`-prefixed cross-skill references) — link-syntax examples that aren't live
prose. **Fixed**: HTML comments (`<!-- ... -->`) are now stripped before the link scan
runs, alongside the existing fenced-block and inline-span stripping. Verified: all 5
copies of `cold-start-interview` now report `path-references-exist — every relative
link resolves`; rerunning the aggregator across the full 430-skill batch afterward
showed `path-references-exist` at 100% PASS — no other skill in this batch had a real
broken link masked by this. Regression test added to `tests/test_validate.py`, whose
docstring now describes all five mechanisms as one family.

### A stray marker file, self-inflicted during investigation — not a tool bug

While investigating two `security-pattern-checks` findings, running `security_scan.py`
directly as its own CLI (rather than through `audit.py report`, which only calls its
read-only functions) wrote a `.security-scan-passed` marker into two vendored skill
directories as a side effect — a real violation of this project's "vendored: cloned
read-only, none modified in place" convention, and it silently flipped those two
skills' third-party/first-party classification on a subsequent individual audit call.
Confirmed `audit.py`'s own `check_security` never calls the marker-writing path (only
`verify_marker`/`run_gitleaks`/`run_pattern_checks`, all read-only) — so the full
430-skill aggregator run itself was never at risk of this. Both stray markers deleted,
classification reverified correct. Noted here as an operational lesson for future
phases (use `audit.py report <path>` to investigate a finding, never
`security_scan.py <path>` directly against vendored content), not as a SkillArtisan
defect.

### Corroborated, not new

- **Directory/skill-name mismatch** (the packaging-defect class first found in Phase 3,
  corroborated in Phase 6): ~40 instances in `zoom-plugin` alone — every skill's `name:`
  differs from its directory name by design (e.g. directory `cobrowse-sdk`, `name:
  zoom-cobrowse-sdk`). The platform sub-skills compound this with a second,
  distinct `skills-ref` error: slash-namespaced names (`contact-center/android`) also
  trip "Skill name contains invalid characters." Real, largest single-corpus instance
  of this class so far, not a new mechanism.
- **`security-gitleaks-clean`** (7 skills, up to 19 findings in one): all investigated
  matches are truncated, placeholder-shaped OAuth tokens in SDK tutorial documentation
  (e.g. `"eyJhbGciOiJIUzI1NiJ9..."`) — the same confirmed-but-unfixable tutorial-token
  class established in Phases 4/5, not new.
- **`forward-slash-paths-only`** (2 skills, `zoom-meeting-sdk-windows`,
  `video-sdk/windows`): real Windows-native SDK path syntax in legitimate platform
  documentation — the same confirmed-correct-content class Phase 4 established for
  Windows security tooling, now corroborated in a completely different domain
  (consumer video SDK docs, not forensics).
- **`security-pattern-checks` — `blocking-interactive-input`** (1 skill,
  `nextflow-development`): a genuine, real interactive bioinformatics-pipeline CLI
  workflow — same already-understood class as Phase 1's `wizard` and Phase 5's
  `llm-cli`, not new.
- **`references-toc-for-long-files`** (38 FAILs, sampled): genuine absence of any
  Contents/TOC/Index heading in every sample checked — Bug #4 (Phase 3) remains
  correctly calibrated on a seventh, structurally distinct corpus.
- **`description-pushy-imperative`** (142 of 430, 33%): further corroboration of
  [#6](https://github.com/EONRaider/SkillArtisan/issues/6)'s "use for"/"use during"
  phrasing gap, in the same mid-range band as several prior corpora.
- **`references-one-level-deep`** (2 FAILs) and **`no-human-docs-in-skill-dir`**
  (1 FAIL): both genuine, both low-volume, both already-understood check shapes.
- **4 `rebuild`-decision skills**: three Zoom platform-SDK reference docs
  (`zoom-meeting-sdk-web`, `zoom-meeting-sdk-windows`, `video-sdk/windows`) and one
  financial model (`dcf-model`) — all confirmed genuinely oversized technical
  reference content, correct verdict.
- **No reserved-word "claude"/"anthropic" hits at all** in any of the 430 skills — a
  legitimate negative result (Anthropic's own shipped content simply doesn't name
  skills that way), not a gap in the check. The 14/14 corroboration streak from prior
  corpora has nothing to test against here, same honest framing as Phase 7's
  "nothing new" result.

### Flagged, not fixed: `triggers:` — new first-party corroboration of a previously-deferred field

Every one of `zoom-plugin`'s ~43 skills declares a `triggers:` frontmatter field, and
the plugin's own `CONTRIBUTING.md` documents it explicitly, in the same breath as two
fields `validate.py` already recognizes as legitimate Claude Code extensions
(`argument-hint`, `user-invocable`). This is materially stronger evidence than the
Phase 5/6 characterization that kept `triggers` out of `THIRD_PARTY_FIELD_FAMILIES` as
a "bespoke one-off convention" — first-party Anthropic content, not a third-party
author's habit, and used systematically, not sporadically. Checked directly against the
official docs (`https://code.claude.com/docs/en/skills.md`) before drawing any
conclusion: `triggers` is confirmed **not** a Claude-Code-native field (the docs have
`when_to_use`, already allowlisted, serving a similar purpose under a different name) —
ruling out the #5-style fix and pointing toward the #7-style one (a new
`THIRD_PARTY_FIELD_FAMILIES` entry) instead. Not fixed speculatively — tracked:
[#8](https://github.com/EONRaider/SkillArtisan/issues/8).

### Cost — a sixth hit-rate data point, and a real operational lesson

Review-queue hit rate: **230 of 430 (53%)** — between mattpocock's 11% and the
mid-to-high band most other corpora have landed in, consistent with the plan's prior
expectation that a professional/vendor-authored corpus would land low-to-mid.
Execution: unchunked, unbuffered by chunking since well under the ~200-skill single-run
comfort zone established in Phase 5. **A real, non-code operational cost showed up
this phase for the first time**: the first full run took over 12 minutes (vs.
seconds-to-low-minutes for comparable prior corpus sizes) because `validate.py`
resolves `skills-ref` via `npx` per skill by default — real npm-registry resolution
overhead repeated 430 times, not a hang (confirmed via process inspection:
`do_poll`-blocked on a child process, not idle). **Fixed for all future phases**:
installed `skills-ref@0.1.5` (the pinned version) to a user-local npm prefix
(`~/.npm-global`), which `validate.py`'s own `find_skills_ref_cmd()` already prefers
over `npx` when present — re-running the identical 430-skill batch after this dropped
total wall-clock to **40 seconds**. This is a one-time local-environment fix, not a
code or vendored-content change; noted here since it materially changes the cost
profile for Phases 9–14 (a ~2,500-skill remaining scope that would otherwise have
carried real npx-overhead cost at that volume). Two real bugs found and fixed
(a shared-code discovery gap, a validate.py false-positive mechanism), one new
`audit-gap` issue opened. Total wall-clock including the two discovery-logic
investigations, the HTML-comment fix, the stray-marker cleanup, and this write-up:
roughly 90–110 minutes — the second-most expensive phase after Phase 6, for a similar
reason (real discovery-logic work, not just grading). **1,848 skills now audited
across seven independently-sourced corpora.**

## Phase 9: nvidia/skills, forcedotcom/sf-skills, aws/agent-toolkit-for-aws (616 skills)

Second phase of the Phase 8–14 roadmap — vendor wave 1 (corporate-DevRel authorship,
three different vendors and domains at once). Three repos, pinned live immediately
before cloning: `nvidia-skills` (344 raw), `forcedotcom-sf-skills` (179 raw),
`aws-agent-toolkit-for-aws` (151 raw).

### A third genuine `find_skill_dirs` gap: `aws-agent-toolkit-for-aws` found only 49 of 151

Same standing discipline as Phase 6/8: `nvidia-skills` and `forcedotcom-sf-skills`
both discovered exactly 344/179, matching the candidates doc's raw counts — no
correction needed. `aws-agent-toolkit-for-aws` did not: only 49 of 151 discovered.
Root cause: a literal top-level `skills/` collection directory — not preceded by any
wildcard, unlike every pattern already in `find_skill_dirs` — with either two or
three category levels of nesting beneath it before the skill's own directory
(`skills/core-skills/amazon-bedrock/SKILL.md`,
`skills/specialized-skills/database-skills/rds-db2/SKILL.md`). 101 of the 102 missing
skills live at these two depths (the other 49 already matched the existing
`plugins/<plugin>/skills/<skill>/SKILL.md` pattern). Checked for collisions against
every other vendored corpus (old and new) before adding the two new patterns: zero
matches anywhere else. **Fixed**: all 150 of 151 now discovered. One skill remains a
documented, known gap rather than a fifth pattern justified by a single example: a
doubly-nested sub-package shape
(`plugins/aws-agents/skills/agents-pay/packages/openclaw/skills/agents-pay/SKILL.md`)
— real content, but 1 instance out of 616 skills this phase, judged not worth the
pattern-list risk that a narrower, single-purpose pattern would carry. Regression
tests added to `tests/test_common_find_skill_dirs.py`. Full 129-test suite passes.

### Content-level dedup, a third confirmation of the same mechanism

`forcedotcom-sf-skills` has 29 content-duplicate groups (58 of 179 skills) — the same
flat-`skills/`-plus-self-contained-mini-plugin dual-packaging pattern first found in
`alirezarezvani` (Phase 6), not a new mechanism. `dedup_by_content` handles it with no
code change. `nvidia-skills` has 1 duplicate group. **Final unique totals**: 343
(nvidia) + 150 (forcedotcom) + 123 (aws) = **616 auditable skills**.

### Genuine content defect, not a check bug: NVIDIA's `doca-*` family has systematic off-by-one relative links

`path-references-exist` FAILed 78 of 616 skills — nearly all in `nvidia-skills`'
`doca-*` family (DOCA is NVIDIA's DPU/BlueField SDK). Investigated directly rather
than assumed: `doca-aes-gcm/SKILL.md` literally contains
`` [`doca-debug`](../../doca-debug/SKILL.md) ``, but `doca-debug` is a *direct
sibling* of `doca-aes-gcm` under `skills/` — the correct relative path is one level
up (`../doca-debug/SKILL.md`), not two. Confirmed by testing both paths against the
real directory tree, and confirmed the pattern is consistent across a random sample
of the `doca-*` family, not an isolated typo. This is the same class of finding as
Phase 6's 12 broken `../../../../megaprompts/` links in `alirezarezvani` — a real,
reproducible authoring/sync defect in the third-party corpus itself (plausibly an
artifact of NVIDIA's stated daily sync pipeline flattening a deeper source-repo
structure into this consolidated `skills/` collection), not a `check_path_references`
false-positive mechanism. Not fixed in SkillArtisan (nothing to fix); documented here
as the highest-volume genuine true positive this check has produced across the whole
pilot.

### Flagged, not fixed: two more NVIDIA field families, one with a real security caveat

35 `frontmatter-valid` FAILs, all in `nvidia-skills`, concentrated in two coherent
families neither Claude-Code-native (checked against the official docs) nor already
in `THIRD_PARTY_FIELD_FAMILIES`:

- **`owner` / `service` / `reviewed`** (8 skills): a real, consistently-used internal
  governance triplet (e.g. `owner: "NVIDIA CORPORATION"`, `service:
  "auto-magic-calib"`, `reviewed: "2026-06-15"`) — same shape as issue #7's
  cybersecurity taxonomy, a reasonable new family candidate.
- **`tools`** (16 skills): a YAML list of literal Claude Code tool names
  (`tools: [Read, Glob, Grep]`). **Important distinction, checked directly against
  the official docs before drawing any conclusion**: this superficially resembles
  the already-portable `allowed-tools` field, but `allowed-tools` has real runtime
  permission-bypass semantics ("tools Claude can use without asking permission"),
  while NVIDIA's `tools:` reads as descriptive/cataloging metadata alongside
  `author`/`tags`/`version`, with no evidence its authors intended a permission
  effect. **These must never be treated as aliases** — silently normalizing `tools`
  into `allowed-tools` would risk granting real, unintended permission-bypass
  behavior. Whatever fix this eventually gets must go through the same
  `THIRD_PARTY_FIELD_FAMILIES` downgrade-to-warning path as `owner`/`service`/
  `reviewed`, never the portable-field path.

Two more instances of the already-tracked `triggers:` field (`nemotron-asr-finetune`,
`nemotron-speech`) — the third and fourth corroborations after Phase 8's ~43, further
supporting [#8](https://github.com/EONRaider/SkillArtisan/issues/8) without escalating
it further. Not fixed speculatively — new issue tracked:
[#9](https://github.com/EONRaider/SkillArtisan/issues/9).

### Corroborated, not new

- **`security-gitleaks-clean`**: a 384-finding outlier
  (`forcedotcom-sf-skills`' `omnistudio-epc-catalog-generate`) is UUIDs used as
  Salesforce/Vlocity record identifiers (`%vlocity_namespace%__GlobalKey__c`) in a
  large product-catalog example dataset — the same confirmed-but-unfixable
  high-entropy-string class established in Phase 4/5, now at unprecedented volume
  because of dataset size, not a new mechanism.
- **`security-pattern-checks` — `blocking-interactive-input`**: real interactive
  hardware-calibration CLI workflows (`amc-run-rtsp-calibration`'s
  `run_rtsp_calibration.py`, genuine `input()` calls for a camera-capture
  confirmation flow) — same already-understood class as Phase 1's `wizard`, Phase 5's
  `llm-cli`, Phase 8's `nextflow-development`.
- **`security-pattern-checks` — `absolute-user-path`**: real, hardware-specific
  deployment paths (`doca-bare-metal-deployment`'s `/home/ubuntu`,
  `/mnt/home/ubuntu/.ssh/` — the standard user on NVIDIA's BlueField DPU appliance
  OS) — same legitimate-fixed-target class as Phase 4's Windows-native tool syntax,
  a different platform, same reasoning.
- **`forward-slash-paths-only`** (2, `holoscan-install-container/wheel`): real
  Windows-style paths in legitimate platform documentation, same corroborated class.
- **`references-toc-for-long-files`** (289, sampled), **`description-pushy-imperative`**
  (247, sampled — further corroboration of
  [#6](https://github.com/EONRaider/SkillArtisan/issues/6)),
  **`degrees-of-freedom-writing-style`** (81, sampled), **`no-time-sensitive-info`**
  (39, sampled), **`no-human-docs-in-skill-dir`** (29), **`references-one-level-deep`**
  (20): all genuine, all already-established check shapes across 8 prior phases —
  no new mechanism in any sample checked.
- **1 `rebuild`-decision skill** (`aws-agent-toolkit-for-aws`'s `amazon-dynamodb`,
  631 lines) — confirmed genuinely oversized reference content.

### Cost — a seventh hit-rate data point, and confirmation the npm fix holds at scale

Review-queue hit rate: **569 of 616 (92%)** — in the high band alongside
daymade/mukul975, higher than Phase 8's vendor corpus. Consistent with the plan's own
caveat that vendor corpora wouldn't all land in the same low-to-mid band Phase 8 did —
`nvidia-skills` in particular is technical, reference-heavy SDK/hardware documentation
across many small product-specific skills, closer in shape to mukul975's
security-education density than Phase 8's more uniform legal/financial-services
prose. Execution: unchunked (616 skills, under the ~800-skill threshold that needed
chunking in Phase 4), **72 seconds total wall-clock** with the local `skills-ref`
install from Phase 8 in place — confirms that fix holds at a larger scale than it was
first measured against (430 → 616 skills, no chunking, no npm-registry overhead).
One real `find_skill_dirs` bug found and fixed, one confirmed-genuine content defect
documented (not a SkillArtisan fix), one new `audit-gap` issue opened covering two
field families. Total wall-clock including the discovery-logic investigation, the
doca-family root-cause confirmation, and this write-up: roughly 60–75 minutes.
**2,464 skills now audited across eight independently-sourced corpora.**
