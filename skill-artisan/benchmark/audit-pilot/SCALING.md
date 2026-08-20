# Scaling readiness: from 35 skills to hundreds

User asked (2026-08-20, after the 35-skill mattpocock run) to expand this methodology to
"possibly hundreds" of skills sourced from well-established repos, and to confirm
readiness first. This is that readiness check: what already scales, what didn't exist
yet and now does, and what's still a real decision rather than an engineering task.

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

**What it deliberately does not automate**: MANUAL items (e.g. `code-review`'s
inline-vs-fork judgment call, one of this pilot's genuine finds) aren't FAIL/WARN, so they
don't enter the review queue. At scale, a sample of MANUAL items still needs a human read
— the tool narrows the FAIL/WARN grading load, not the MANUAL one. And the tool doesn't
grade true-positive vs. false-positive itself — that's still a source read, by design (see
README.md's anti-circularity principle). It only tells you *where* to spend that read.

## What's ready right now: a second source, zero new sourcing decisions

`benchmark/vendored/daymade-claude-code-skills/` is already cloned, already pinned
(`d24f6d1`, user-confirmed 2026-08-16), already used as this project's corpus source, and
already has a Credits-section attribution in the README. Running
`_common.find_skill_dirs` against it directly (the same discovery `audit.py bulk` uses)
finds **92 real skill directories** — 13 already used as corpus seeds, so **~79 unaudited
skills** available immediately, no new clone, no new license check, no new pin decision.
Combined with the 35 already done, that's ~114 without touching a new repo at all — most
of the way to "hundreds" from one already-vetted source.

Caveat, matching how `corpus/README.md` already treated this same repo: not every
discovered directory is a real, intended skill to grade — the tree includes
`daymade-skill/skill-creator` (a tool/fork, not a skill), and likely `demos`/`tests`-style
fixture content mixed in among the 92. Curating that list (same judgment call
`corpus/README.md` already made when it said "not the repo's other 68 pre-built skills")
is a short, mechanical pass before running this at scale — not a blocker, but not "just
run it on all 92" either.

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
3. **Grading budget at hundreds-scale.** Even with the review-queue narrowing, if the hit
   rate holds near the ~11% seen in this run (4/35), a 300-skill run implies roughly
   30-40 skills needing an actual source read — that's a multi-session effort, not a
   single turn. Worth deciding up front whether that's done inline (as this pilot was) or
   via parallel subagents reading one skill each (this repo already has a proven pattern
   for chat-orchestrated subagent dispatch in `benchmark/harness/run_authoring.py` — the
   same script-tracks-state/chat-spawns-agents division of labor would apply here, with
   the added rule that a grading agent must read the *source skill* directly, never just
   re-ask `audit.py`'s own reasoning about itself).

## Recommendation

Ready to scale mechanically; not ready to unilaterally pick new sources. Concrete next
step I can take immediately on your go-ahead: curate and audit the ~79 unaudited
`daymade-claude-code-skills` skills using `aggregate_findings.py` (zero new sourcing
decisions, reuses an already-pinned, already-credited source) as a second data point
before committing to a third, unvetted repo. That alone gets real coverage past 110
skills across two independently-sourced corpora, which is a meaningfully stronger claim
than one corpus, before any new licensing/sourcing decision is needed.
