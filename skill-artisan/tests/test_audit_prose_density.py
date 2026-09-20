#!/usr/bin/env python3
"""Regression test for check_prose_density, ported from a separate personal
skill's linter ("skill-audit") — a broader lean/medium/heavy bloat scorer
than the existing check_degrees_of_freedom_proxy (which only catches bare
ALL-CAPS MUST/ALWAYS/NEVER, not case-insensitive absolutes or general
ALL-CAPS "shouting").

Run: python3 -m unittest skill-artisan/tests/test_audit_prose_density.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

The acronym whitelist was calibrated against this project's own
creating-skills/SKILL.md (self-validation, per this project's discipline of
verifying a check against real content before trusting it): an earlier
version flagged this project's own PASS/FAIL/WARN/MANUAL checklist-status
vocabulary, plus MCP/AI/CLI/POST, as "shouting" — all legitimate technical
vocabulary, not emphasis. This test pins that calibration directly.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))

import audit  # noqa: E402


class TestCheckProseDensity(unittest.TestCase):
    def test_short_plain_body_is_lean(self):
        item = audit.check_prose_density("A short skill body.\nDoes one thing.\n")
        self.assertEqual(item["status"], "PASS")
        self.assertIn("lean", item["detail"])

    def test_many_case_insensitive_absolute_words_trips_heavy(self):
        line = "You must always do this and never skip it, it is mandatory and critical.\n"
        body = line * 5  # well over 15 absolute-word hits
        item = audit.check_prose_density(body)
        self.assertEqual(item["status"], "WARN")
        self.assertIn("heavy", item["detail"])

    def test_lowercase_absolutes_are_still_counted_unlike_the_narrower_proxy(self):
        """The whole point of this check vs. check_degrees_of_freedom_proxy:
        that one only matches literal ALL-CAPS MUST/ALWAYS/NEVER, so lowercase
        "always"/"never"/"must" sail through it uncounted."""
        body = "always do this, never do that, you must comply, it is only mandatory. " * 4
        proxy = audit.check_degrees_of_freedom_proxy(body)
        density = audit.check_prose_density(body)
        self.assertEqual(proxy["status"], "PASS", "the narrower proxy is case-sensitive and misses these")
        self.assertEqual(density["status"], "WARN", "the broader check must still catch them")

    def test_whitelisted_acronyms_are_not_shouting(self):
        body = ("Use the API to fetch HTML/JSON over HTTP or HTTPS. See the CLI, the MCP "
                "server, and check PASS/FAIL/WARN/MANUAL status via a POST to the URL.\n")
        item = audit.check_prose_density(body)
        self.assertIn("0 shouting word(s)", item["detail"])

    def test_non_whitelisted_all_caps_word_counts_as_shouting(self):
        body = "SHOUTING " * 20
        item = audit.check_prose_density(body)
        self.assertIn("20 shouting word(s)", item["detail"])
        self.assertEqual(item["status"], "WARN")

    def test_long_body_by_line_count_alone_trips_at_least_medium(self):
        body = "\n".join(f"Line {i} of plain content." for i in range(80))
        item = audit.check_prose_density(body)
        self.assertIn(item["detail"].split(" ")[0], ("medium", "heavy"))
        self.assertEqual(item["status"], "WARN")

    def test_creating_skills_own_skill_md_has_no_shouting_false_positives(self):
        """Self-validation: this project's own checklist-status vocabulary
        (PASS/FAIL/WARN/MANUAL) and common tech acronyms (MCP/AI/CLI/POST)
        used throughout creating-skills/SKILL.md must not inflate the
        shouting count."""
        from _repo_paths import CREATING_SKILLS_DIR
        body, _ = audit.get_body(CREATING_SKILLS_DIR)
        shouting = [w for w in audit.SHOUTING_WORD_RE.findall(body) if w not in audit.SHOUTING_WHITELIST]
        self.assertNotIn("MCP", shouting)
        self.assertNotIn("PASS", shouting)
        self.assertNotIn("FAIL", shouting)
        self.assertNotIn("WARN", shouting)
        self.assertNotIn("MANUAL", shouting)


if __name__ == "__main__":
    unittest.main()
