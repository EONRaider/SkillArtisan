#!/usr/bin/env python3
"""Regression test for the Claude Code frontmatter-field allowlist (issue #5).

Run: python3 -m unittest skill-artisan/tests/test_field_classification.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

The audit pilot's Phase 3 (daymade/claude-code-skills) found a real skill,
competitors-analysis, declaring `context: fork` together with
`agent: general-purpose` — and validate.py hard-FAILed it because `agent`
wasn't in CLAUDE_CODE_ONLY_FIELDS. The fix was deferred (issue #5) until it
could be confirmed whether `agent` is a real Claude Code field or a bespoke
author convention. It is real: https://code.claude.com/docs/en/skills.md
documents it ("Which subagent type to use when `context: fork` is set"),
along with seven more fields the allowlist was missing (`arguments`,
`disallowed-tools`, `model`, `effort`, `background`, `hooks`, `shell`).
This test pins the synced allowlist in both directions: every documented
field classifies as Claude Code-only (informational, not an error), and a
recorded true positive from Phase 5 — `user_invocable`, an underscore typo
for the real `user-invocable` — still lands in unknown and keeps erroring.
See benchmark/audit-pilot/RESULTS.md.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "skill-artisan" / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import validate  # noqa: E402

DOCUMENTED_CLAUDE_CODE_FIELDS = {
    "disable-model-invocation", "user-invocable", "context", "paths", "when_to_use", "argument-hint",
    "agent", "arguments", "disallowed-tools", "model", "effort", "background", "hooks", "shell",
}


class TestAllowlistSyncedToDocs(unittest.TestCase):
    def test_every_documented_field_is_allowlisted(self):
        missing = DOCUMENTED_CLAUDE_CODE_FIELDS - validate.CLAUDE_CODE_ONLY_FIELDS
        self.assertFalse(missing, f"documented Claude Code fields missing from allowlist: {sorted(missing)}")

    def test_competitors_analysis_frontmatter_shape_is_not_unknown(self):
        """The exact real-world shape that exposed the gap: context: fork + agent."""
        frontmatter = {"name": "competitors-analysis", "description": "d",
                       "context": "fork", "agent": "general-purpose"}
        classified = validate.classify_extended_fields(frontmatter)
        claude_only, unknown = classified[0], classified[-1]
        self.assertIn("agent", claude_only)
        self.assertIn("context", claude_only)
        self.assertNotIn("agent", unknown)

    def test_underscore_typo_still_errors(self):
        """Phase 5 true positive: `user_invocable` is a typo for the real
        `user-invocable` and must keep failing — the allowlist sync must not
        get so permissive it absorbs near-miss field names."""
        frontmatter = {"name": "x", "description": "y", "user_invocable": "true"}
        classified = validate.classify_extended_fields(frontmatter)
        unknown = classified[-1]
        self.assertIn("user_invocable", unknown)


if __name__ == "__main__":
    unittest.main()
