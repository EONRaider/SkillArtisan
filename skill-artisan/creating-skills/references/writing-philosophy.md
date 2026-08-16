# Writing Philosophy

Ported from `skill-creator` (its second-strongest asset, after the eval engine) and extended with the coherent-unit-scoping and degrees-of-freedom checks below. This file is the one place all of `creating-skills`' prose-quality rules live — the decision gate and security checklist point here rather than repeating them.

## Table of Contents

- [Imperative voice](#imperative-voice)
- [Explain the why](#explain-the-why)
- [Generalize from feedback, don't overfit](#generalize-from-feedback-dont-overfit)
- [Keep it lean](#keep-it-lean)
- [Coherent-unit scoping](#coherent-unit-scoping)
- [Degrees of freedom](#degrees-of-freedom)
- [Content hygiene](#content-hygiene)

## Imperative voice

Write instructions as commands, not descriptions. "Read the transcript completely" rather than "The transcript should be read completely." Imperative voice reads faster and leaves less room for the model to interpret an instruction as optional context.

## Explain the why

Today's models have real theory of mind. Given a good harness, they generalize past rote instructions — but only if they understand the purpose behind a rule. Bare `MUST`/`ALWAYS`/`NEVER` in all caps is a yellow flag: it's usually standing in for reasoning the author didn't spell out. Reframe it as an explanation instead.

Compare:

> **NEVER** skip the baseline run.

> Always run baseline (without-skill) and with-skill executions from the same clean-context prompt. Without a baseline, a benchmark can't tell you whether the skill helped or whether the model would have done just as well unassisted — the delta is the whole point of the comparison.

The second version survives contact with an edge case the author didn't anticipate; the first doesn't, because the model has nothing to reason from when the literal rule doesn't quite fit.

This applies to every reference file in `creating-skills`, not just SKILL.md bodies.

## Generalize from feedback, don't overfit

Skills get used far more times than they get iterated on. When a test case surfaces a problem, the instinct is to patch it with a rule that fixes exactly that case — an ever-growing list of `if X, do Y` exceptions. That produces a skill that's brittle everywhere it wasn't tested and bloated everywhere it was.

Instead, ask what broader category of situation the failure represents, and fix that. If three test cases all made the model reinvent the same helper script, the fix isn't three special-cased instructions — it's bundling the script once in `scripts/` and telling the skill to use it (this is also how `skill-creator`'s own scripts accumulate: watch for repeated ad hoc work across eval transcripts, not just failures).

The same discipline applies to description tuning (see the eval engine's train/validation split in `scripts/description_optimizer.py`): a description tuned to pass every specific query in the train set, at the cost of generalizing, is overfit — which is exactly why the optimizer selects the best iteration by *validation* score, not train score.

## Keep it lean

Cut content the model would get right without it. Every sentence in a SKILL.md body is loaded into context on every activation — a paragraph explaining something Sonnet or Opus already does correctly by default is pure cost with no benefit. Read a draft with fresh eyes after writing it and ask, for each section: would removing this change the model's behavior for the worse? If not, remove it.

This is in tension with "explain the why" above — the resolution is that the *why* should be as short as the reasoning actually requires, not padded into a paragraph. One clause is often enough.

## Coherent-unit scoping

Distinct from degrees of freedom below — this is about the skill's *boundary*, not its *internal instruction style*. A skill should encapsulate one coherent unit of work, the way a well-scoped function does one thing.

- **Too narrow**: splitting one workflow across multiple skills forces them to load together and risks conflicting or duplicated instructions when they disagree on approach. If two skills would always be invoked together for the same task, they're probably one skill.
- **Too broad**: a skill covering several unrelated capabilities becomes hard to activate precisely — its description has to cover everything it does, which dilutes triggering accuracy for each individual capability, and most activations only need a fraction of the loaded content.

A useful test: can you describe the skill's job in one sentence without using "and" to join two unrelated verbs? "Fills PDF forms and sends Slack notifications" is two skills wearing one description.

## Degrees of freedom

Match instruction specificity to task fragility, in three explicit tiers — not a vague "narrow bridge vs. open field" spectrum. Every tier still ends in a single default approach plus an explicit escape hatch; none of these are a menu of equally-valid options.

| Tier | When to use | What it looks like | Escape hatch |
|---|---|---|---|
| **High freedom** | Multiple approaches are genuinely valid; the task has no single right answer | Text guidance describing the goal and constraints, not a procedure | Note that alternate approaches are fine as long as [constraint] holds |
| **Medium freedom** | A preferred pattern exists but some variation across cases is expected and safe | Pseudocode, or a parameterized script the model fills in | State when deviating from the pattern is acceptable, and why |
| **Low freedom** | The operation is fragile or error-prone — a wrong step has real cost (data loss, security exposure, silent corruption) | An exact script or command to run verbatim, not paraphrased | Document the one case where a human should intervene instead of running it |

Worked example: writing a commit message is high freedom (many valid phrasings, the model's judgment is fine here). Generating a chart from a fixed data schema is medium freedom (a `build_chart.py` script with parameters, since the shape is consistent but styling varies). Rotating a security-scan's tamper-detection marker via atomic write is low freedom (`scripts/security_scan.py`'s marker logic is an exact, unvarying sequence — get the temp-file-then-rename order wrong and the safety property it exists for disappears).

When in doubt, freedom should decrease as the blast radius of a mistake increases, not as a matter of how experienced you assume the author is.

## Content hygiene

- **No time-sensitive information.** Don't write "as of 2026" or "the current version is X" — it goes stale silently and nobody re-reads a shipped skill to catch it. If an old pattern needs documenting for migration purposes, put it in a collapsed `<details>` section explicitly labeled as historical, not in the main flow of instructions.
- **Forward-slash paths only.** Never `C:\Users\...` — skills run across platforms, and Windows-style paths break silently on the ones that aren't Windows.
- **Consistent terminology.** Pick one term per concept and use it everywhere in the skill (`references/`, not sometimes "references" and sometimes "docs" and sometimes "resources"). Inconsistent terminology reads as a signal that the model should treat these as different things when they're not.
- **No voodoo constants.** A magic number in a bundled script (a timeout, a retry count, a threshold) needs a one-line comment saying where it came from — measured, or a reasonable guess, or matched to an external constraint. An unexplained constant looks load-bearing even when it isn't, and the next editor won't know whether it's safe to change.
- **Declare dependencies, don't assume them.** If a script needs a package beyond the stdlib, declare it via `compatibility` (see `references/surface-matrix.md`) or invoke it through a pinned one-off runner (`uvx`, `pipx`, `npx`) rather than assuming it's pre-installed in whatever environment the skill ends up running in.
