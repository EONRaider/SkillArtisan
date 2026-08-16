---
name: drafting-changelog-entries
description: Draft a CHANGELOG.md entry for SkillArtisan by cross-referencing what was actually built against the master spec's Gap Table, so nothing gets marked closed that isn't verifiably true of the repo. Use when a build session (or a stage/prompt) has finished and it's time to record what shipped, when asked to "update the changelog," "draft release notes," "write up what we just built," or "check what's still open," or when preparing a version bump (major = v-stage boundary per this project's semver interpretation, minor = new capability within a stage, patch = a fix). Use even without the word "changelog" — "what's left before this ships," "summarize this session for the log," "did we close row 12."
---

# Drafting Changelog Entries

Turn a finished build session into an accurate `CHANGELOG.md` entry — accurate meaning every "Added" line is checked against the actual repo state, not against what was intended or what a build prompt asked for. Intent and outcome drift, especially across a long session; this skill exists specifically to catch that drift before it ships as a false claim in a changelog.

## Why this matters here specifically

SkillArtisan's own build process (the master spec + the Stage 1-4/5-6 build prompts) explicitly warns against exactly this failure mode: "don't mark anything done that isn't verifiably true of the repo." A changelog entry is a public claim about what a version does. Writing "Added: X" when X was planned but not actually finished — or was finished differently than planned — is the same category of error the master spec's own release checkpoint guards against, just at the documentation layer instead of the code layer.

## Process

1. **Gather what actually happened.** Prefer `git log`/`git diff` against the previous release tag if this is a git repo; otherwise, work from the session's own record of what was built (files created/edited, scripts run, tests passed). Don't work from the build prompt's task list alone — a task list describes intent, not outcome.

2. **Cross-reference against the Gap Table**, not just against the task list. Read the relevant Gap Table rows (`skill-artisan-master-spec.md`'s "Gap Table" section, or whatever this project's current gap-analysis/tracking document is called if the spec has moved) for the stage that just shipped. For each row the stage claims to close:
   - Find the actual file(s) that should implement it.
   - Spot-check that the file genuinely does what the row describes — read it, don't just confirm it exists. A stub file with the right name is not a closed row.
   - Where feasible, run the thing rather than trust the code by inspection alone (a validator, a scanner, a test skill through the actual pipeline) — reading code correctly predicts intent, not always behavior; a live run catches what reading misses. This is exactly how two real bugs were caught during SkillArtisan's own v1 build: reading `skill-creator`'s trigger-detection script looked correct, but running it against a live session surfaced that its `.claude/commands/` registration path doesn't produce a triggerable skill in current Claude Code.

3. **Classify each item honestly**: shipped as designed, shipped with a deviation worth noting (say what changed and why), or not shipped. Anything planned but not shipped moves to `[Unreleased]`'s "Planned for X" list — never drop it silently. This project's own `CHANGELOG.md` header states this discipline explicitly; follow it.

4. **Format per this project's actual conventions**, not generic Keep a Changelog defaults — read `CHANGELOG.md`'s own header before writing anything, since it redefines semver locally: a **major** bump marks a v-stage boundary specifically (not just "something breaking changed"), **minor** is new capability within a stage that doesn't break existing usage, **patch** is fixes. Get the version number right by checking which of these three the actual change represents, not by defaulting to patch.

5. **Note anything discovered but not asked for.** If verifying an "Added" claim surfaced a real bug (as in the trigger-detection example above), the changelog entry should say so — a fixed bug found during verification is real, changelog-worthy content, and burying it inside a generic "Added: eval engine" line loses information a future reader (including a future version of this same process) would want.

6. **Write the entry**, dated, under the correct version heading. Keep line-item granularity consistent with the existing changelog's style — this project's `[1.0.0]` entry groups related sub-deliverables into single bullet points rather than one bullet per file; match that density rather than defaulting to either extreme (one giant paragraph, or one bullet per commit).

## Worked check: does this entry earn its claims?

Before finalizing, read every "Added" line back and ask: *is there a file I can point to, and have I actually looked at what's in it?* If the answer to either is no for any line, that line isn't ready to ship — go verify it or cut it, don't soften the wording and hope. A hedge like "partial support for X" is still a claim; it still needs the same verification, just of a narrower claim.

## Lifecycle

Encoded-preference, timelessness 8/10, last verified against claude-sonnet-5 (2026-08). This skill encodes a fixed process for *this specific project* — cross-reference the Gap Table, apply this repo's local semver interpretation, match the existing changelog's line-item density — not a capability gap a smarter model closes on its own; a future model still benefits from being told to check the Gap Table before claiming a row closed. Scored a point below `creating-skills`' own 9/10 because part of its durability depends on `skill-artisan-master-spec.md` and its Gap Table continuing to exist under those names — a narrower, project-specific dependency than a plugin's own self-contained rules.
