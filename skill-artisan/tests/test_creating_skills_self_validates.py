#!/usr/bin/env python3
"""Regression test: SkillArtisan's own shipped skill must pass its own validator.

Run: python3 -m unittest skill-artisan/tests/test_creating_skills_self_validates.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Found via a live marketplace-install check (2026-08-20), not a synthetic
test: after `claude plugin install skillartisan@eonraider` against the
real EONRaider/claude-plugins marketplace, running `audit.py report` on
the installed `creating-skills` skill — exactly what SKILL.md tells
Claude to do when auditing a skill — returned `frontmatter-valid: FAIL`.
Its own `compatibility` field was 530 characters, over skills-ref's
500-character limit. This had shipped since commit ac282ce (2026-08-19,
before the 119-test suite existed in its current form) with zero
coverage: nothing in the suite ever ran validate.py's real skills-ref
check against creating-skills/SKILL.md itself, only against fixtures.
This test closes that specific gap by calling validate.validate()
against the real shipped skill directory, the same way an install-time
audit does — not a mock, not a fixture standing in for it.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import CREATING_SKILLS_DIR, SCRIPTS_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))

import validate  # noqa: E402


class TestCreatingSkillsSelfValidates(unittest.TestCase):
    def test_shipped_skill_passes_its_own_validator(self):
        result = validate.validate(CREATING_SKILLS_DIR)
        self.assertTrue(result["valid"], f"creating-skills fails its own validate.py: {result['errors']}")

    def test_compatibility_field_under_skills_ref_limit(self):
        from _common import parse_frontmatter_raw
        frontmatter = parse_frontmatter_raw((CREATING_SKILLS_DIR / "SKILL.md").read_text())
        compat = frontmatter.get("compatibility", "")
        self.assertLessEqual(len(compat), 500,
                             f"compatibility field is {len(compat)} chars — skills-ref's hard limit is 500")


if __name__ == "__main__":
    unittest.main()
