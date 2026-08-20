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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402

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


class TestThirdPartyFieldFamilies(unittest.TestCase):
    """Issue #7: mukul975/Anthropic-Cybersecurity-Skills' consistent
    framework-mapping taxonomy (mitre_attack, nist_csf, domain, ...) FAILed
    frontmatter-valid on 817 of 817 skills — a real, coherent field family,
    not sloppy authoring. Recognized families now downgrade to a portability
    warning; anything outside a family stays a hard error."""

    MUKUL975_FRONTMATTER = {
        "name": "windows-event-log-analysis", "description": "d",
        "author": "mukul975", "domain": "forensics", "subdomain": "windows",
        "mitre_attack": "T1070", "nist_csf": "DE.AE", "tags": "dfir",
        "version": "1.0",
    }

    def test_family_fields_classify_as_known_third_party(self):
        claude_only, known, unknown = validate.classify_extended_fields(self.MUKUL975_FRONTMATTER)
        self.assertEqual(unknown, [], "family fields must not land in unknown (the hard-error bucket)")
        self.assertEqual(claude_only, [])
        self.assertIn("security-framework-taxonomy", known)
        self.assertIn("common-authoring-metadata", known)
        self.assertIn("mitre_attack", known["security-framework-taxonomy"])
        self.assertIn("author", known["common-authoring-metadata"])

    def test_mixed_frontmatter_fills_all_three_buckets(self):
        frontmatter = {"name": "x", "description": "y", "context": "fork",
                       "mitre_attack": "T1059", "totally_made_up_field": "z"}
        claude_only, known, unknown = validate.classify_extended_fields(frontmatter)
        self.assertEqual(claude_only, ["context"])
        self.assertEqual(known, {"security-framework-taxonomy": ["mitre_attack"]})
        self.assertEqual(unknown, ["totally_made_up_field"])

    def test_bespoke_conventions_still_error(self):
        """Recorded Phase 5/6 patterns deliberately kept OUT of the families."""
        for field in ("triggers", "command", "agents", "compatible_tools", "user_invocable"):
            _, known, unknown = validate.classify_extended_fields({"name": "x", field: "v"})
            self.assertIn(field, unknown, f"{field} must stay a hard error")
            self.assertEqual(known, {})

    def test_family_warning_text_avoids_the_audit_filter_word(self):
        """audit.py's check_frontmatter_and_paths buckets warnings by the
        substring 'gerund' — the family warning must never contain it, or it
        would be misattributed to the naming-convention checklist item."""
        for name, fields in validate.THIRD_PARTY_FIELD_FAMILIES.items():
            self.assertNotIn("gerund", name)
            for f in fields:
                self.assertNotIn("gerund", f)


if __name__ == "__main__":
    unittest.main()
