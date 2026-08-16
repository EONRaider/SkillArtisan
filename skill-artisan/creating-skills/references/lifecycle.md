# Lifecycle Framing

Row 14. Classifies a skill by *why it stops being useful*, so re-benchmarking effort goes where it actually pays off instead of being spread evenly across a skill library that ages in two structurally different ways.

## Table of Contents

- [Two categories](#two-categories)
- [The timelessness score](#the-timelessness-score)
- [Re-benchmarking trigger](#re-benchmarking-trigger)
- [Worked example: `creating-skills` classifies itself](#worked-example-creating-skills-classifies-itself)

## Two categories

**Capability-uplift.** The skill gives the model an ability it otherwise lacks — a script it can't derive on the spot, a procedure it would get wrong without explicit steps, domain knowledge outside training data. This is exactly the category that can go obsolete on its own: if a future base model learns to do the underlying task natively, the skill stops adding anything and starts being pure context cost. A skill in this category needs periodic re-benchmarking against new model releases, not just when something breaks.

**Encoded-preference.** The skill fixes a *choice* among several equally-valid approaches — house style, a specific output format, a team's fixed workflow order — rather than compensating for a capability gap. A smarter model doesn't make the choice moot; the choice was never a capability question in the first place. These don't carry the same obsolescence risk and don't need the same re-benchmarking cadence.

The distinction matters because the two categories fail differently: a stale capability-uplift skill quietly stops helping (worst case, it actively gets in the way of a model that would now do better unassisted); a stale encoded-preference skill just... doesn't go stale in the same sense, unless the preference itself changes.

## The timelessness score

A bare binary label can't distinguish a capability-uplift skill about to age out next quarter from one likely to stay useful for years — both get the same tag. Score it instead, 0–10, against how much of the skill's value depends on a *specific, plausibly-closing* capability gap versus a durable one:

| Score range | Meaning |
|---|---|
| 0–3 | The gap this skill fills is narrow and actively closing — a model limitation likely to be fixed in the next 1-2 releases (e.g., a specific formatting quirk models are already trending away from). |
| 4–6 | Real uplift today, but resting on a capability that's plausible to see native improvement in within a year or two. |
| **≥7 (durable bar)** | The gap is structural (real-time data access, a proprietary format, a fixed external constraint like a compliance rule) or the skill is encoded-preference, which doesn't age this way at all. |

**≥7 is the bar for "durable, not at near-term obsolescence risk."** Below it, don't treat the skill as broken — treat the score as a standing note to re-benchmark sooner rather than later, and as a factor in the audit mode's upgrade-vs-rebuild decision (`scripts/audit.py` — a skill scoring under 7 whose checklist failures are also severe is a real rebuild candidate, not just a patch candidate; see `SKILL.md`'s "Auditing existing skills" section).

Attach the score directly to the skill, not in a separate tracking document that drifts out of sync — a metadata line at the end of the SKILL.md body (or in the `metadata` frontmatter field) works:

```
Lifecycle: capability-uplift, timelessness 8/10, last verified against claude-sonnet-5 (2026-08).
```

## Re-benchmarking trigger

Re-run the Stage 1 eval engine (`scripts/eval_loop.py`, smoke preset is enough for a check-in; reliable or regression preset before deciding to retire something) whenever:

- A new model generation ships and the skill is capability-uplift with a timelessness score under 7 — check first, don't assume it still helps.
- The skill's pass-rate delta (with-skill vs. without-skill) was already thin at authoring time — a thin margin is the first thing a model upgrade erodes.
- It's been a long time since the skill was last verified and it's never been re-checked against a newer model at all, regardless of score — the "last verified against" line existing at all is worth more than its exact age.

Encoded-preference skills don't need this trigger — nothing about a smarter model makes a house-style choice stop applying. Re-benchmark them only if the underlying preference itself changes (a team adopts a new format, a compliance rule is superseded).

## Worked example: `creating-skills` classifies itself

`creating-skills` is **encoded-preference**, not capability-uplift — the frontmatter constraints, the security-scan gate structure, the decision-gate routing logic, and the writing-philosophy rules are all fixed choices about *how to build a skill well*, not a capability the underlying model lacks. A future, smarter model would still benefit from a validated frontmatter check, a gitleaks gate before publishing, and a decision gate that stops it from building a skill-shaped wrapper around something that should be CLAUDE.md — none of that is a gap native intelligence closes.

**Timelessness: 9/10.** The one component with any capability-uplift flavor is the eval engine's with/without-skill delta measurement — if a future model became so good at inferring workflow-specific procedure from a bare task description that skills stopped mattering at all, the entire premise of this plugin would need rethinking, not just this skill. That's a structural, not incremental, risk, which is why it's scored near the top rather than a flat 10.

Last verified against: claude-sonnet-5 (2026-08).
