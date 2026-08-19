---
name: gha-fix-pr-smoke-test
description: Use when manually smoke-testing the GitHub Action's fix-PR path end to end. This is a disposable test fixture for skill-artisan's own CI, not a real user-facing skill, and is deliberately missing evals/lifecycle classification so the audit always finds FAIL items to fix.
---

# GitHub Action Fix-PR Smoke Test

Deliberately incomplete fixture used only by
`.github/workflows/self-test-action-fix-pr.yml` (manual, opt-in, requires
`ANTHROPIC_API_KEY`). It has no `evals/evals.json` and no lifecycle
classification, so `audit.py` always reports FAIL items here — giving the
fix-PR path something real to act on without touching any fixture the rest
of the test suite depends on.

1. Confirm the Action opens a PR with an additive-only diff for this fixture.
2. Discard/close that PR after inspecting it — it exists only to prove the
   pipeline works, not to be merged.
