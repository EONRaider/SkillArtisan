# Scaling readiness: from 35 skills to hundreds

User asked (2026-08-20, after the 35-skill mattpocock run) to expand this methodology to
"possibly hundreds" of skills sourced from well-established repos, and to confirm
readiness first. This is that readiness check: what already scales, what didn't exist
yet and now does, and what's still a real decision rather than an engineering task.

**Update, same day, after Phase 3 actually ran** (92 more skills from
`daymade-claude-code-skills` — see `RESULTS.md`): the predictions below were tested
against real data, not left as untested theory. Two held exactly; one didn't and is
corrected in place rather than quietly left wrong — see the marked update below.

## What already scales without changes

- **Audit execution itself.** `audit.py`/`aggregate_findings.py` (new, see below) are
  deterministic, no LLM calls — sub-second per skill. Running against hundreds of skills
  costs minutes of wall-clock, not a meaningfully different order of magnitude than 35
  did. This was never the bottleneck.
- **No subagent orchestration needed for execution.** Unlike the abandoned 5-arm
  Best-in-Market Scorecard (which spawns an authoring subagent per corpus-skill per arm —
  the thing that hit near-total trigger-detection failure and tens-of-millions-of-token
  costs at >1 concurrent worker), auditing an *existing* skill is read-only and scriptable
  end to end. That cost profile doesn't apply here.

## What didn't scale, and is now built

At 35 skills, I personally read every audit report and, for the ones with real findings,
the skill's actual source, then eyeballed which checklist items were 100%-FAIL boilerplate
by hand. That doesn't hold at hundreds. Built `aggregate_findings.py` to do the mechanical
part:

- Runs `audit.py`'s own `audit_skill()` across one or more source directories (one
  per corpus/repo, so per-source breakdown stays meaningful).
- Computes, per checklist item, the dominant-status rate across the whole run — flags
  anything hitting the boilerplate pattern (≥95% one status, configurable) that isn't
  already known-boilerplate, so a *new* scope-mismatch check doesn't have to be
  discovered by hand again next time.
- Produces a **review queue**: only the skills with a non-boilerplate FAIL/WARN, which is
  what actually needs a human (or agent) source-read. On the mattpocock corpus this
  narrowed 35 skills down to 4 — an ~89% reduction in what needs eyes-on grading.
- Verified against this run's own known-correct results: rerunning it against
  `mattpocock-skills` reproduces the exact same 4-skill review queue this pilot found by
  hand, and correctly shows `wayfinder` now clean post-fix. Not a new untested tool —
  validated against ground truth from the run just completed.

**Confirmed working in Phase 3**: `aggregate_findings.py` ran clean across all 92
`daymade-claude-code-skills` (after Bug #3's crash was fixed) and its checklist-item
dominant-rate flagging correctly re-surfaced `path-references-exist` and other items as
newly-100%-PASS after each fix was applied, without any change to the tool itself —
exactly the "verify a fix by rerunning the aggregator" workflow this was built for.

**What it deliberately does not automate**: MANUAL items (e.g. `code-review`'s
inline-vs-fork judgment call, one of this pilot's genuine finds) aren't FAIL/WARN, so they
don't enter the review queue. At scale, a sample of MANUAL items still needs a human read
— the tool narrows the FAIL/WARN grading load, not the MANUAL one. And the tool doesn't
grade true-positive vs. false-positive itself — that's still a source read, by design (see
README.md's anti-circularity principle). It only tells you *where* to spend that read.

## Done: the second source (`daymade-claude-code-skills`, 92 skills, Phase 3)

**Correction to what this section originally said**: it predicted needing to curate the
92 discovered directories down (excluding `daymade-skill/skill-creator` as "a tool, not a
skill", and expecting `demos`/`tests` fixture noise). That curation step turned out to be
unnecessary — `_common.find_skill_dirs` doesn't pick up `demos`/`tests` directories at
all (no `SKILL.md` at a discoverable depth there), and `skill-creator` genuinely does have
a valid `SKILL.md` and is a legitimate skill in its own right (just also serving a special
role as a comparison-arm entry point elsewhere in this project) — auditing it isn't wrong.
All 92 discovered directories were audited as-is, no exclusions needed. Left here,
corrected rather than deleted, because the original prediction was wrong in a way worth
remembering: "this looks like it needs curation" isn't the same as "it does" — check
before assuming.

Result: 92/92 audited, four real tool bugs found and fixed (see `RESULTS.md`), the
`claude`-reserved-word true positive corroborated 10 more times (13/13 total across both
corpora now), and 127 skills audited in total. The "second data point before committing
to a third repo" plan this section originally proposed is complete.

## What's a real decision, not an engineering task

Getting from ~114 (mattpocock + daymade) into the hundreds needs at least one more source
repo. I'm not naming or vendoring a new one unilaterally: picking a "well-established"
skills repo is an editorial and licensing call (this project's own convention — see
`vendored/README.md`'s pinning and Credits-attribution discipline for the two sources
already in use) that's genuinely the user's to make, not something to guess at. Concretely
needed before a "hundreds" run:

1. **Which additional repo(s)?** Options I can see from what's already referenced in this
   codebase: the master spec cites Snyk's ToxicSkills audit corpus (ClawHub, skills.sh —
   aggregator sites, thousands of skills, but mixed provenance/quality, useful for a
   different kind of test — security-detection stress-testing — than "well-established
   author" skills) and community sources like "superpowers" and AI Builder Club guides,
   named only as citations, not verified as clone-able/licensed sources here. I'd want you
   to confirm the actual repo(s) before I clone and pin anything new.
2. **License/attribution check per new source**, same as the two already vendored —
   confirm MIT/Apache-compatible before pinning, add to the README's Credits section if
   material is adapted, not just audited.
3. **Grading budget at hundreds-scale — corrected with real data, not the original
   estimate.** This section originally predicted the ~11% review-queue hit rate seen on
   mattpocock (4/35) would roughly hold, implying ~30-40 skills needing a read per 300.
   **Wrong, and wrong in an important direction**: `daymade-claude-code-skills` hit rate
   was 91% before fixes (84/92), and still 91% after — the fixes didn't shrink the queue
   because most of the 84 findings were genuine, not false positives (the false positives
   were concentrated but not the majority; see `RESULTS.md`'s Phase 3 sections). Hit rate
   is corpus-dependent, not a fixed constant — a single-author, mature, engineering-focused
   repo (mattpocock) and a large, heterogeneous, many-contributor-style repo (daymade,
   financial/audio/docs/dev-tooling all mixed) produced wildly different rates. **Don't
   plan a third source's grading budget off mattpocock's 11%** — assume it could be
   anywhere from ~10% to 100% depending on the source's homogeneity and maturity, and
   budget conservatively (closer to daymade's number, or higher) until a third data point
   exists. What still held: grouping by checklist-item and sampling within high-volume
   groups (used for Phase 3's 84-skill queue) kept the actual reading load manageable even
   at a 91% hit rate — full exhaustive reads, not sampling, would be the thing that
   doesn't scale, not the review-queue mechanism itself.

   **Third data point, Phase 4 (`mukul975-anthropic-cybersecurity-skills`, 817 skills):
   100% hit rate** — every single skill had at least one non-boilerplate finding. Unlike
   Phase 3, most of that volume wasn't false positives found and fixed — it was **real,
   confirmed matches genuinely present in the text, deliberately left unfixed** (see
   `RESULTS.md`'s Phase 4 "Headline" table): security-education content is *adversarial*
   to path/secret/dangerous-pattern checks by its very nature (real Windows paths, real
   credential-shaped example strings, real dangerous-sounding function names, all
   legitimately part of the teaching content). This is a genuinely different shape of
   "high hit rate" than daymade's — daymade's 91% was mostly signal *worth fixing*;
   mukul975's 100% is mostly signal that's *correctly firing on the right kind of content
   but not actionable as a code fix*. Budgeting a future source's grading pass needs to
   account for both possibilities, not just raw hit-rate percentage — a security- or
   compliance-adjacent corpus should be expected to produce a high rate of "confirmed, not
   fixed" findings rather than "confirmed, fixed" ones.

   **Fourth data point, Phase 5 (`glebis-claude-skills`, 111 skills): 77% hit rate** —
   between mattpocock's 11% and daymade/mukul975's 91%/100%, landing in between because
   this corpus mixes both shapes at once: one new real bug (`path-references-exist`'s
   fourth false-positive mechanism, a `~/`-prefixed cross-skill reference) alongside a
   cluster of genuine true positives on the exact same checks that were mostly false
   positives in Phase 4 — this author's own real leaked home directory path (22 instances
   in one skill alone), real interactive scripts, real risky deserialization. Confirms the
   Phase 4 lesson generalizes: hit-rate *shape* (fixable bug vs. correct-but-unfixable
   signal vs. genuine true positive) varies by corpus genre independently of hit-rate
   *magnitude*, and a personal/real-world-tooling corpus tends toward true positives on
   checks that fired as false positives on deliberately-crafted teaching content.
4. **Parallel subagent grading, still unused so far.** Both Phase 1/2 (35 skills, full
   reads) and Phase 3 (92 skills, sampled reads) ran entirely inline, no subagents spawned
   — cheaper in practice than expected, so this was never actually needed yet. Stays a
   real option for a third source if its hit rate and size combine into a genuinely
   large reading load: this repo already has a proven pattern for chat-orchestrated
   subagent dispatch in `benchmark/harness/run_authoring.py` (script tracks state, chat
   spawns agents) that would transfer directly, with the same rule Phase 1-3 already
   followed — a grading agent must read the *source skill* directly, never just re-ask
   `audit.py`'s own reasoning about itself.

## Recommendation

Mechanically proven across four independently-sourced corpora now (1,055 skills total,
seven real tool bugs found and fixed — see `RESULTS.md`). Phase 4 validated the chunked/
resumable execution mode added ahead of it (a real shell timeout hit mid-run, zero results
lost); Phase 5 validated that a small corpus (111 skills) doesn't need chunking at all,
and that a personal/real-world-tooling corpus can land at any hit rate with any mix of
fixable-bug/correct-but-unfixable/genuine-true-positive shapes — don't assume Phase 4's
"high hit rate mostly means unfixable noise" pattern generalizes; Phase 5's high-ish rate
(77%) was mostly genuine true positives instead. Phases 6–7 (alirezarezvani, obra) are
approved and next; budget each one's grading pass expecting a hit rate anywhere from ~10%
to 100%, with the finding *shape* varying by corpus genre independently of the rate
itself. Reuse `aggregate_findings.py`'s chunking for any single source past a couple
hundred skills, not just the largest one.
