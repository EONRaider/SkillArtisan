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
   anywhere from ~10% to ~90% depending on the source's homogeneity and maturity, and
   budget conservatively (closer to daymade's number) until a third data point exists.
   What still held: grouping by checklist-item and sampling within high-volume groups
   (used for Phase 3's 84-skill queue) kept the actual reading load manageable even at a
   91% hit rate — full exhaustive reads, not sampling, would be the thing that doesn't
   scale, not the review-queue mechanism itself.
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

Mechanically ready, proven across two independently-sourced corpora (127 skills total,
four real tool bugs found and fixed as a direct result — see `RESULTS.md`). Not ready to
unilaterally pick a third source — per the user (2026-08-20), candidate repos for that are
being researched separately (via a dedicated research request) and will be fed into this
same methodology once chosen. When that happens: budget the grading pass assuming a
daymade-like hit rate (correction above), not mattpocock's lower one, until the new
source's actual rate is known; reuse `aggregate_findings.py` as-is (add the new source
directory as another `--label`); and expect it to keep finding real things — the marginal
finding rate did not taper off between Phase 1/2 and Phase 3, it went up.
