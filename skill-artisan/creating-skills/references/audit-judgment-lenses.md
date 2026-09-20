# Audit Judgment Lenses

Four judgment calls for auditing an *existing* skill that no mechanical check can make — `scripts/audit.py`'s `MANUAL_ONLY_ITEMS` points here for each. Adapted from a separate personal skill's audit process, which ran these as a forked, disallowed-Bash-and-Write review of one skill's `SKILL.md` in isolation; here they're one step inside this plugin's own broader audit checklist instead, since `audit.py` already has the mechanical findings (body size, frontmatter validity, security scan) on hand and there's no need for a second, separate audit pass to get to the same judgment calls.

## Table of Contents

- [Prose that should be a script](#prose-that-should-be-a-script)
- [Do-nots that should be enforced](#do-nots-that-should-be-enforced)
- [Fork appropriateness](#fork-appropriateness)
- [Condensing a bloated skill](#condensing-a-bloated-skill)

## Prose that should be a script

English describing a fixed, mechanical procedure — count something, find something, format a value, rename a set of files, validate a path exists, run N steps in a specific order — costs tokens on every activation, is slower for the model to execute correctly than a script would be, and is a real place for a step to get skipped or reordered under context pressure. A model can *read* "count the lines in each file over 100KB and list the top 5" easily; a ten-line script does the same job in one deterministic call with zero chance of miscounting.

Read the body looking for: a numbered procedure with no ambiguity in any step (nothing here needs judgment — it's arithmetic, string manipulation, or file-system traversal wearing an instruction's clothes), a description of exact output formatting rules (column widths, sort order, a specific date format), or repeated phrasing like "for each X, do Y" over a collection the model would otherwise have to iterate by hand. Contrast with genuinely prose-appropriate content: anything requiring judgment about *this specific* input (is this description pushy enough, does this code look dangerous) stays prose — a script can't make that call, per this project's own degrees-of-freedom guidance (`references/writing-philosophy.md`).

If found: propose the script's interface (inputs, output shape) rather than just naming the problem — "this should be a script" without a sketch of what the script takes and returns isn't actionable feedback.

## Do-nots that should be enforced

A `SKILL.md` that says "never edit files outside `scripts/`" or "don't run destructive commands" in prose is asking the model to remember a rule under load, every single turn, for the life of the session — the same class of reliability problem `references/security-checklist.md` documents for security-relevant instructions specifically. Two real enforcement mechanisms exist instead: a `disallowed-tools` frontmatter entry (mechanically blocks the tool call, no reliance on the model remembering) or a hook event (runs regardless of whether the model "chose" to follow the rule that turn).

Read the body for absolute prohibition language ("never," "don't," "must not," "always confirm before") paired with an action a real Claude Code mechanism could enforce directly — a tool call, a file-path pattern, a command prefix. Not everything qualifies: a prohibition that depends on semantic judgment ("don't suggest a fix that changes public API behavior") has no mechanical enforcement point and correctly stays prose.

If found: name the specific mechanism (which tool to add to `disallowed-tools`, or which hook event and matcher) rather than just flagging that prose should become "something more enforced."

## Fork appropriateness

`context: fork` isolates a skill's execution from the main conversation — no access to prior turns, a clean context window, but also no memory of what the user already said, what other files are open, or decisions already made this session. Checkable mechanically (`audit.py`'s `architecture-declared` item reports whatever `context:` value is present); whether it's the *right* call for this specific skill is not.

A fork is appropriate when the skill's job is genuinely self-contained given its own arguments — a linter, an audit, a generator that takes explicit inputs and produces a report, none of which benefits from (or is correct with) conversation history. A fork is the wrong call when the skill needs to reference something the user said earlier in the session, build on a partially-completed task, or hand its result back into an ongoing conversation the main thread is tracking — forking silently discards all of that. Read the skill's own job description against this test: does its output depend only on its explicit inputs (arguments, the files it's pointed at), or does it implicitly depend on conversation state a fork can't see? The worked examples in `SKILL.md`'s own Decision Gate section are the canonical reference for borderline cases.

## Condensing a bloated skill

Actionable specifically when `body-size-limits` or `prose-density` above reports WARN or FAIL — this lens turns "the body is too long" into a concrete plan, not a restatement of the same finding. Read the full body and sort every section into one of three buckets: **delete** (the model already gets this right without being told — see `references/writing-philosophy.md`'s "keep it lean"), **move to a reference file** (detail that's only needed for edge cases, not every activation — progressive disclosure, not deletion), or **move to a script** (mechanical procedures per the first lens above, which stop costing body tokens once they're a script call instead of inline prose).

Propose a target line count (informed by `body-size-limits`' own 500-line PASS ceiling, not an arbitrary round number) and the specific delete/move-to-reference/move-to-script assignment for each section — a condense recommendation that just says "make this shorter" gives the author nothing to act on.
