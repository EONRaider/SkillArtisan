#!/usr/bin/env python3
"""Regression test for check_frontmatter_and_paths reading validate.py's
structured missing_references/missing_references_error keys, instead of
string-matching result["errors"] for a "Missing referenced files" prefix.

Run: python3 -m unittest skill-artisan/tests/test_audit_frontmatter_and_paths.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Found via a solid-coding audit of skill-artisan/scripts/ (2026-09-20):
audit.py classified a validate.py error as path-references-exist (vs.
frontmatter-valid) purely by `startswith("Missing referenced files")` on
free text, with no guard against that wording ever changing — unlike this
same codebase's own "gerund" substring match, which has an explicit
never-collide comment plus a dedicated regression test
(test_field_classification.py::test_family_warning_text_avoids_the_audit_filter_word).
Fixed by having validate.validate() expose the missing-reference list and
its exact formatted error string as their own dict keys, so audit.py
compares by identity instead of reconstructing the prefix text.

This test proves the coupling is actually gone, not just less likely to
collide: it monkeypatches the exact wording validate.py uses for the
missing-refs message and confirms check_frontmatter_and_paths still
classifies correctly — a naive prefix-matching implementation would break
under this change, since the patched wording no longer starts with
"Missing referenced files".
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))

import audit  # noqa: E402
import validate  # noqa: E402


def make_skill_with_broken_link(skill_dir: Path) -> None:
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: broken-link-skill\ndescription: a skill for testing\n---\n"
        "See [missing](nonexistent.md) for details.\n"
    )


class TestStructuredMissingReferences(unittest.TestCase):
    def test_validate_exposes_structured_missing_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "broken-link-skill"
            make_skill_with_broken_link(skill_dir)
            result = validate.validate(skill_dir)
            self.assertEqual(result["missing_references"], ["nonexistent.md"])
            self.assertIn("Missing referenced files", result["missing_references_error"])
            self.assertIn(result["missing_references_error"], result["errors"])

    def test_clean_skill_has_no_missing_references_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "clean-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: clean-skill\ndescription: a skill for testing\n---\nNo links here.\n"
            )
            result = validate.validate(skill_dir)
            self.assertEqual(result["missing_references"], [])
            self.assertIsNone(result["missing_references_error"])

    def test_check_frontmatter_and_paths_survives_a_changed_error_wording(self):
        """The actual regression guard: audit.py must classify correctly
        even if validate.py's message wording changes entirely, since the
        classification now goes through a structured key, not a substring
        match on this exact text."""
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "broken-link-skill"
            make_skill_with_broken_link(skill_dir)

            real_validate = validate.validate

            def patched_validate(skill_path):
                result = real_validate(skill_path)
                if result.get("missing_references_error"):
                    old = result["missing_references_error"]
                    new = "totally reworded message with no shared prefix at all"
                    result["errors"] = [new if e == old else e for e in result["errors"]]
                    result["missing_references_error"] = new
                return result

            with mock.patch.object(audit.validate, "validate", side_effect=patched_validate):
                items = audit.check_frontmatter_and_paths(skill_dir)

            by_id = {item["id"]: item for item in items}
            self.assertEqual(by_id["path-references-exist"]["status"], "FAIL")
            self.assertIn("totally reworded message", by_id["path-references-exist"]["detail"])
            # frontmatter-valid must NOT also fail on the reworded missing-refs
            # message -- it should be excluded by identity, same as before.
            self.assertEqual(by_id["frontmatter-valid"]["status"], "PASS")


class TestStructuredBashPermissionWarning(unittest.TestCase):
    """A solid-coding review found audit.py's script-references-need-bash-permission
    item substring-matching "Bash"/"permission" in validate.py's free text,
    the exact hazard class this file's other tests already guard against for
    missing_references. Fixed the same way: validate() exposes a structured
    bash_permission_warning key; audit.py reads it directly."""

    def make_skill_referencing_an_unguarded_script(self, skill_dir: Path) -> None:
        skill_dir.mkdir(parents=True)
        (skill_dir / "scripts").mkdir()
        (skill_dir / "scripts" / "run.sh").write_text("#!/bin/sh\n")
        (skill_dir / "SKILL.md").write_text(
            "---\nname: unguarded-script-skill\ndescription: a skill for testing\n---\n"
            "Run `${CLAUDE_SKILL_DIR}/scripts/run.sh` to do the thing.\n"
        )

    def test_validate_exposes_structured_bash_permission_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "unguarded-script-skill"
            self.make_skill_referencing_an_unguarded_script(skill_dir)
            result = validate.validate(skill_dir)
            self.assertIsNotNone(result["bash_permission_warning"])
            self.assertIn(result["bash_permission_warning"], result["warnings"])

    def test_check_frontmatter_and_paths_survives_a_changed_bash_warning_wording(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "unguarded-script-skill"
            self.make_skill_referencing_an_unguarded_script(skill_dir)

            real_validate = validate.validate

            def patched_validate(skill_path):
                result = real_validate(skill_path)
                if result.get("bash_permission_warning"):
                    old = result["bash_permission_warning"]
                    new = "a totally reworded warning with no shared keywords"
                    result["warnings"] = [new if w == old else w for w in result["warnings"]]
                    result["bash_permission_warning"] = new
                return result

            with mock.patch.object(audit.validate, "validate", side_effect=patched_validate):
                items = audit.check_frontmatter_and_paths(skill_dir)

            item = next(i for i in items if i["id"] == "script-references-need-bash-permission")
            self.assertEqual(item["status"], "WARN")
            self.assertIn("totally reworded warning", item["detail"])


if __name__ == "__main__":
    unittest.main()
