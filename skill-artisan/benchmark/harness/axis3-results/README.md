# Axis 3 (security posture) — pilot results

3 corpus skills × 4 authoring arms, scored via `security_scan.py --verbose --json`
against each pilot output (the same correctly-named `audited/<declared-name>/` copies
Axis 1 uses). No-skill baseline has no Axis 3 score — nothing to scan.

## Results

- **Gitleaks-clean rate: 12/12 = 100%.**
- **11/12 clean on the full bar** (gitleaks + CRITICAL + HIGH pattern findings).
- The one exception, `excel-automation`/`daymade-fork`, is a confirmed false positive,
  not a real finding — see below.

Per-arm/per-skill breakdown: `axis3_summary.json`. Full per-finding detail:
`<skill>__<arm>.json`.

## The one HIGH finding is a false positive, verified directly

`daymade-fork`'s `excel-automation` output flagged `blocking-interactive-input` (HIGH)
at `scripts/create_formatted_excel.py:105`. The actual matched text:

```python
"""Style a cell as user input (blue font, green fill)."""
```

A docstring describing a cell-formatting helper, matched purely because the phrase
"user input" appears in it — not an actual `input()`/`read -p` call. Confirmed by
reading the flagged line directly. This is exactly the kind of keyword-matching false
positive the security-checklist's own documentation warns is a real ceiling on automated
scanning; not evidence of a real blocking-input defect in this arm's output. The
remaining MEDIUM findings across all arms (`insecure-http-url` matches against
`http://schemas.openxmlformats.org/...` namespace URIs, required literal strings in the
OOXML/XLSX file format spec, not fetched endpoints) are the same known false-positive
class, informational-only, and don't affect the clean/not-clean verdict either way.

## Two real bugs found and fixed while producing this data

Neither is a security-scan-methodology issue — both are script bugs in existing,
already-shipped project code (`scripts/security_scan.py`), found because this was the
first time this project ran `--json` mode at real scale across many skills in one sitting:

1. **`--json` mode printed human-readable text to stdout after the JSON on every clean
   scan** (`Clean scan — wrote .security-scan-passed.` + the sanitization-checklist
   reminder), violating this project's own stdout/stderr convention
   (`references/script-design.md`) and breaking strict JSON parsing for 11 of the first
   12 scans run this way (the one dirty scan happened to parse fine, since it had no
   clean-scan text appended — that asymmetry is what surfaced the bug). Fixed: that text
   now goes to stderr when `--json` is set.
2. Not a `security_scan.py` bug, but found in the same pass: the harness's own
   `audited/<name>` directory listing needed to explicitly exclude the sibling
   `axis2-scratch/` directory Axis 2's trigger scorer creates — an easy harness-side
   mistake, not a scanner defect, noted here since it lives in the same aggregation step.

## Status

Pilot-scale only (3 of 16 corpus skills). The master spec's Axis 3 target bar is
"100% gitleaks-clean and zero critical findings across the **entire corpus**" — this
pilot clears that bar on its own 3-skill subset, but 3/16 does not satisfy "entire
corpus." Do not cite this as having cleared the target bar.
