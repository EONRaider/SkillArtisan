#!/usr/bin/env python3
"""Regression test for _common.frontmatter_and_body, and for the
consolidation of audit.py's get_body and validate.py's validate() onto it.

Run: python3 -m unittest skill-artisan/tests/test_common_frontmatter_and_body.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Found via a solid-coding audit of skill-artisan/scripts/ (2026-09-20):
audit.py's get_body and validate.py's validate() each independently
reimplemented the identical frontmatter/body delimiter-boundary scan —
byte-identical except for a local variable name. This is exactly the
failure mode that already caused a real production bug once, documented
elsewhere in this project's history: two independently-drifted frontmatter
parsers silently disagreeing on a real SKILL.md's shape. Consolidated onto
one shared _common.frontmatter_and_body, matching the scripts/ discipline
in references/script-design.md.

The fallback path (no well-formed frontmatter block) was previously
untested through either get_body or validate() directly, despite being
live and load-bearing in validate() (it's what lets validate() degrade
gracefully and report an error, rather than crash, on a malformed
SKILL.md). This test pins that behavior for the shared helper directly,
plus both callers' actual current wiring.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))

from _common import frontmatter_and_body  # noqa: E402

WELL_FORMED = "---\nname: x\ndescription: y\n---\nBody line one.\nBody line two.\n"
NO_OPENING_DELIM = "name: x\ndescription: y\nBody line one.\n"
NO_CLOSING_DELIM = "---\nname: x\ndescription: y\nBody line one.\n"
EMPTY_FRONTMATTER = "---\n---\nBody line one.\n"


class TestFrontmatterAndBody(unittest.TestCase):
    def test_well_formed_splits_frontmatter_and_body(self):
        frontmatter, body = frontmatter_and_body(WELL_FORMED)
        self.assertEqual(frontmatter, {"name": "x", "description": "y"})
        self.assertEqual(body, "Body line one.\nBody line two.\n")

    def test_missing_opening_delimiter_falls_back_to_whole_content_as_body(self):
        frontmatter, body = frontmatter_and_body(NO_OPENING_DELIM)
        self.assertEqual(frontmatter, {})
        self.assertEqual(body, NO_OPENING_DELIM)

    def test_missing_closing_delimiter_falls_back_to_whole_content_as_body(self):
        frontmatter, body = frontmatter_and_body(NO_CLOSING_DELIM)
        self.assertEqual(frontmatter, {})
        self.assertEqual(body, NO_CLOSING_DELIM)

    def test_empty_frontmatter_block_yields_empty_dict_and_real_body(self):
        frontmatter, body = frontmatter_and_body(EMPTY_FRONTMATTER)
        self.assertEqual(frontmatter, {})
        self.assertEqual(body, "Body line one.\n")


class TestCallerWiring(unittest.TestCase):
    """Confirm audit.py's get_body and validate.py's validate() actually
    consume frontmatter_and_body correctly (in particular, get_body's own
    (body, frontmatter) return order, the reverse of frontmatter_and_body's
    (frontmatter, body) — a mismatch here would surface loudly, but is worth
    pinning directly rather than relying on it always failing loudly)."""

    def test_get_body_returns_body_then_frontmatter(self):
        import tempfile
        import audit  # noqa: E402

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "a-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(WELL_FORMED.replace("name: x", "name: a-skill"))
            body, frontmatter = audit.get_body(skill_dir)
            self.assertEqual(body, "Body line one.\nBody line two.\n")
            self.assertEqual(frontmatter["description"], "y")

    def test_validate_reports_an_error_instead_of_crashing_on_malformed_skill_md(self):
        import tempfile
        import validate  # noqa: E402

        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "malformed-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(NO_CLOSING_DELIM)
            # Must not raise -- validate() degrades gracefully on a
            # malformed SKILL.md (unlike parse_skill_md, which raises by
            # design for its own, different callers).
            result = validate.validate(skill_dir)
            self.assertFalse(result["valid"])


if __name__ == "__main__":
    unittest.main()
