#!/usr/bin/env python3
"""Regression test for check_path_references and fenced-code-block handling.

Run: python3 -m unittest skill-artisan/tests/test_validate.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Found via the real-world audit pilot (2026-08-20, see
benchmark/audit-pilot/RESULTS.md), across three phases and the same root
cause each time: `check_path_references` treats anything link-shaped as a
real reference into the skill's own directory, when it's sometimes a
worked example (`wayfinder`, fenced), a cautionary example
(daymade skills, inline code span), or — most recently — a cross-skill
dependency reference naming another skill's expected installed location
(`glebis/claude-skills`' `agency-docs-updater`, a bare `~/`-prefixed
path). Each mechanism fixed as found; this test file guards all of them
plus real broken/valid links to make sure the fixes never regress.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "skill-artisan" / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import validate  # noqa: E402


class TestCheckPathReferences(unittest.TestCase):
    def test_link_shaped_text_inside_a_fenced_example_is_ignored(self):
        body = (
            "Some prose.\n\n"
            "```markdown\n"
            "- [<closed ticket title>](link) — one-line gist\n"
            "```\n"
        )
        missing = validate.check_path_references(Path("/nonexistent"), body)
        self.assertEqual(missing, [])

    def test_link_shaped_text_inside_an_inline_code_span_is_ignored(self):
        body = (
            "Do NOT create markdown links to files that don't exist "
            "(e.g., `[doc.md](reviewed-document)`); use plain text instead.\n"
        )
        missing = validate.check_path_references(Path("/nonexistent"), body)
        self.assertEqual(missing, [])

    def test_tilde_prefixed_cross_skill_reference_is_ignored(self):
        body = "See [calendar-sync](~/.claude/skills/calendar-sync) for the companion skill.\n"
        missing = validate.check_path_references(Path("/nonexistent"), body)
        self.assertEqual(missing, [])

    def test_real_broken_link_outside_a_fenced_block_is_still_caught(self):
        body = "See [the reference doc](references/does-not-exist.md) for details.\n"
        missing = validate.check_path_references(Path("/nonexistent"), body)
        self.assertEqual(missing, ["references/does-not-exist.md"])

    def test_real_valid_link_outside_a_fenced_block_still_resolves(self, ):
        with_tmp = REPO_ROOT / "skill-artisan"
        body = "See [the scripts dir](scripts/validate.py) for details.\n"
        missing = validate.check_path_references(with_tmp, body)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
