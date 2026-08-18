# Axis 1 (checklist compliance) — pilot results

3 corpus skills × 4 authoring arms, scored via `audit.py report --json` against the
Synthesized Checklist, unmodified. No-skill baseline has no Axis 1 score (nothing to
checklist — it doesn't author a skill).

Each output was copied into a directory literally matching its own declared `name:`
frontmatter before auditing (`audited/<declared-name>/`), since `audit.py` checks
directory-name-matches-declared-name and the harness's raw `output/` directory would
otherwise fail that check for every arm uniformly — a harness artifact, not a real
finding, so it's controlled for rather than reported as a defect.

## Per-arm average pass rate (3 pilot skills)

| Arm | Avg pass rate |
|---|---|
| creating-skills | **97.9%** |
| skill-creator | 81.3% |
| daymade-fork | 77.3% |
| skillforge | 74.4% |

Per-skill breakdown and raw `passed/failed/warned/manual` counts: `axis1_summary.json`.
Full per-item PASS/FAIL/WARN/MANUAL detail: `<skill>__<arm>.json`.

## Two caveats before reading these numbers as final

**1. Several failing checklist items are creating-skills-specific conventions, not
universal skill-authoring failures.** `security-scan-marker-current` (no
`.security-scan-passed` file) and `lifecycle-classified` (no capability-uplift/
encoded-preference classification) each account for 3 of the ~3-4 failures per non-
creating-skills arm. These are real items in the Synthesized Checklist — which the
master spec explicitly designates as the Axis 1 scoring instrument — but a fair reading
is that skill-creator/daymade-fork/skillforge never had a reason to know these specific
conventions exist, since they're not part of *their* documented processes. This isn't
grounds to discount the score (the master spec is explicit that the Checklist is the
instrument, deliberately including things creating-skills does that others don't), but
it should be stated plainly in Phase 8's report rather than presented as if all four arms
were tested against a neutral, arm-agnostic standard.

**2. `evals-present` failed for `skillforge` on all 3 pilot skills despite skillforge
shipping real eval content every time** — `evals/triggers.json` + `evals/scenarios/*.md`,
confirmed present in every pilot output. The check likely looks for `evals/evals.json`
specifically (this project's own schema) and doesn't recognize SkillForge's differently-
named-and-shaped eval files as equivalent. This is a scoring-instrument blind spot, not
a real gap in skillforge's output — flag this specifically in Phase 8 rather than let it
silently depress skillforge's number for something it didn't actually fail to do.

## Common cross-arm failure (looks like a real, fair finding)

`references-toc-for-long-files` failed for skill-creator (2/3 skills), daymade-fork
(3/3), skillforge (3/3), and even creating-skills once (1/3) — a >100-line reference
file missing a table of contents. This one applies identically regardless of which
process authored the skill, so unlike the two caveats above, this looks like a genuine,
fair cross-arm signal rather than a scoring-instrument artifact.

## Status

Pilot-scale only (3 of 16 corpus skills). Not the full Best-in-Market Scorecard Axis 1
result — do not treat `creating-skills` clearing 90%+ here as satisfying the master
spec's checklist-compliance target bar, which requires the full corpus.
