# Best-in-Market Scorecard — Benchmark Corpus

Fixed, reproducible test-skill corpus for the master spec's "Best-in-Market Scorecard"
(`skill-artisan-master-spec.md`). Not cherry-picked per run — every arm is measured
against the same 16 entries below, every time this benchmark is re-run.

## Layout per entry

```
corpus/<skill-name>/
  meta.json                 category, source (scratch|daymade), and — for daymade-sourced
                             entries — the origin skill name and whether its evals were
                             reused as-is or rewritten to remove a live external dependency
  seed.md                   the rough draft / blank-slate ask fed to every arm's authoring
                             or improvement workflow (methodology's step (1): "starting
                             from the same rough draft or blank slate")
  evals/evals.json          8-10 task-success cases, schema per
                             creating-skills/references/schemas.md
  evals/trigger-evals.json  8-10/8-10 should/should-not-trigger queries, schema per
                             scripts/description_optimizer.py (list of {query, should_trigger})
  evals/files/               optional fixture files evals.json entries reference via `files`
```

## Categories (4 per category, 16 total)

- **Document/data processing**: `excel-automation`, `repomix-safe-mixer`, `repomix-unmixer`, `structured-data-diff` (from scratch)
- **Dev tooling**: `auto-repo-setup`, `debugging-network-issues`, `github-sensitive-data-cleanup`, `git-safety-net`
- **Research/analysis**: `bilibili-source`, `fact-checker`, `deep-research`, `dataset-bias-auditor` (from scratch)
- **Creative/design**: `frontend-visual-qa`, `design-style-picker`, `ui-designer`, `narrative-arc-builder` (from scratch)

13 adapted from `daymade/claude-code-skills` at commit `d24f6d1`, 3 built from scratch
(`structured-data-diff`, `dataset-bias-auditor`, `narrative-arc-builder`). Each entry has
8 task-success cases (`evals/evals.json`) and an 8-10/8-10 should/should-not trigger split
(`evals/trigger-evals.json`); `frontend-visual-qa` and `excel-automation`/`bilibili-source`
run slightly above 8 where the source material justified it. Every entry validated:
valid JSON, `meta.json` present, `seed.md` present.

### Live-dependency entries (flagged in `meta.json`, not excluded)

`bilibili-source`, `fact-checker`, `deep-research`, and `design-style-picker` each
genuinely depend on a live capability (a real API fetch, live web search, or image
generation) that a frozen "golden answer" can't meaningfully pin down. Per the confirmed
external-dependency policy, none were excluded or given a mock server; instead each one's
`evals.json` expectations grade **process fidelity** (did it actually fetch/search/generate
rather than guess, did it cite/timestamp appropriately, did it avoid fabricating on
failure) rather than a specific frozen value. Phase 3's harness should cap rep count
against these four specifically rather than treating them like the 12 fully offline
entries.

## Source policy

- **Adapted (13 entries)**: sourced from `daymade/claude-code-skills` at commit
  `d24f6d13f57688d8436b78647519f0ae49b37adf` ("chore(ci): upgrade GitHub Actions to Node
  24 (#300)", 2026-08-17 01:59:05 +0800) — **user-confirmed and locked 2026-08-16**. No
  tags exist in that repo, so this is a HEAD-SHA pin. At confirmation time, `origin/main`
  had already advanced one commit to `ebea45c71d8c6cf57312ef74862795d4c4a94760` (docs-only:
  `claude-code-hooks/references/hook_pitfalls.md`, `CHANGELOG.md`, `marketplace.json` —
  verified via `git diff --stat d24f6d1 origin/main`, none of the 13 sourced skills
  touched); `d24f6d1` was kept as the pin specifically because it's the commit actually
  read while authoring these 13 entries, not because it was the latest available. Use this
  exact SHA when cloning the repo into `benchmark/vendored/` in Phase 2. The origin skill's
  real purpose and scope inform `seed.md` and `evals.json`; existing eval material is
  reused where it was both present and self-contained, rewritten where present but
  live-dependent, and authored fresh where absent.
- **From scratch (3 entries)**: built specifically for this benchmark so results aren't
  biased toward a skill any one arm's authors already know how to handle.

## External-dependency policy

Confirmed with the user (2026-08-16): any daymade skill whose evals require a **live**
external service to grade correctly — real-time Bilibili metrics, an actual WeCom webhook
send, live GitHub PR/repo state — is adapted to a synthetic or local fixture instead of
excluded or run live. Running Axis 2 (task-success delta) means dozens of runs per skill
across 5 arms; live calls at that scale would be non-reproducible (violates the "fixed
corpus" requirement), rate-limit-risky, and in the WeCom case would mean actually sending
hundreds of real messages to a live chat. Each affected entry's `meta.json` documents
exactly what was synthesized and why.

## Status

Phase 1 (corpus construction) complete: 16/16 entries, 4/4 per category, all JSON
validated. See `skill-artisan/CHANGELOG.md` `[Unreleased]` and this session's task list
for where Phase 2 onward stands.
