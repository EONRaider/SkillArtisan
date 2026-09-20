#!/usr/bin/env python3
"""Regression test for check_path_references and fenced-code-block handling.

Run: python3 -m unittest skill-artisan/tests/test_validate.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Found via the real-world audit pilot (2026-08-20, see
benchmark/audit-pilot/RESULTS.md), across five phases and the same root
cause each time: `check_path_references` treats anything link-shaped as a
real reference into the skill's own directory, when it's sometimes a
worked example (`wayfinder`, fenced), a cautionary example
(daymade skills, inline code span), a cross-skill dependency reference
naming another skill's expected installed location (`glebis/claude-skills`'
`agency-docs-updater`, a bare `~/`-prefixed path), an author-facing
authoring note inside an HTML comment showing what an optional collateral
link should look like (`anthropics/claude-for-legal`'s `cold-start-interview`,
Phase 8, a literal `[intro](URL)` placeholder inside `<!-- -->`, found 12
times across five plugin-specific copies of the same skill), or — most
recently — a `{baseDir}`-prefixed template variable
(`trailofbits/skills`, Phase 11): unlike every mechanism above, this one
IS a real, checkable reference (verified 41 of 41 resolve to real files
before fixing), so it's stripped and re-checked, not skipped outright — a
genuinely broken `{baseDir}/...` reference is still caught. Each mechanism
fixed as found; this test file guards all of them plus real broken/valid
links to make sure the fixes never regress.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import PLUGIN_ROOT, SCRIPTS_DIR  # noqa: E402

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

    def test_link_shaped_text_inside_an_html_comment_is_ignored(self):
        body = (
            "Wait for the user's pick.\n\n"
            "<!-- COLLATERAL LINKS: when onboarding collateral exists, prepend:\n"
            '     "Want a walkthrough? [Watch the intro](URL) or [read the guide](URL)." -->\n'
        )
        missing = validate.check_path_references(Path("/nonexistent"), body)
        self.assertEqual(missing, [])

    def test_base_dir_prefixed_reference_to_a_real_file_resolves(self):
        body = "See [validate.py]({baseDir}/scripts/validate.py) for the check itself.\n"
        missing = validate.check_path_references(PLUGIN_ROOT, body)
        self.assertEqual(missing, [])

    def test_base_dir_prefixed_reference_to_a_missing_file_is_still_caught(self):
        body = "See [ghost]({baseDir}/references/does-not-exist.md) for details.\n"
        missing = validate.check_path_references(Path("/nonexistent"), body)
        self.assertEqual(missing, ["references/does-not-exist.md"])

    def test_real_broken_link_outside_a_fenced_block_is_still_caught(self):
        body = "See [the reference doc](references/does-not-exist.md) for details.\n"
        missing = validate.check_path_references(Path("/nonexistent"), body)
        self.assertEqual(missing, ["references/does-not-exist.md"])

    def test_real_valid_link_outside_a_fenced_block_still_resolves(self, ):
        with_tmp = PLUGIN_ROOT
        body = "See [the scripts dir](scripts/validate.py) for details.\n"
        missing = validate.check_path_references(with_tmp, body)
        self.assertEqual(missing, [])


class TestCheckClaudeSkillDirRefs(unittest.TestCase):
    """check_path_references' own docstring names ${CLAUDE_SKILL_DIR} as a
    syntax it deliberately does NOT handle (its stripping pass runs before
    its regex, and this substitution overwhelmingly lives inside backticked
    shell snippets). This is the companion check that closes that gap,
    ported from a separate personal skill's linter, adapted to run on the
    raw content instead."""

    def test_dangling_reference_inside_a_code_span_is_caught(self):
        """The exact case check_path_references cannot see: a bundled-script
        reference inside inline code, which its own stripping pass removes
        before its regex ever runs."""
        content = "Run `${CLAUDE_SKILL_DIR}/scripts/does-not-exist.sh` to fix it.\n"
        missing = validate.check_claude_skill_dir_refs(Path("/nonexistent"), content)
        self.assertEqual(missing, ["scripts/does-not-exist.sh"])

    def test_real_reference_in_allowed_tools_frontmatter_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_path = Path(tmp)
            (skill_path / "scripts").mkdir()
            (skill_path / "scripts" / "run.sh").write_text("#!/bin/sh\necho hi\n")
            content = (
                "---\nname: x\nallowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/run.sh)\n---\n"
                "Run the bundled script.\n"
            )
            missing = validate.check_claude_skill_dir_refs(skill_path, content)
            self.assertEqual(missing, [])

    def test_dangling_reference_in_frontmatter_is_caught(self):
        content = "---\nname: x\nallowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/ghost.sh)\n---\nBody.\n"
        missing = validate.check_claude_skill_dir_refs(Path("/nonexistent"), content)
        self.assertEqual(missing, ["scripts/ghost.sh"])

    def test_trailing_punctuation_is_stripped_from_the_target(self):
        content = "See `${CLAUDE_SKILL_DIR}/scripts/does-not-exist.sh`, then fix it.\n"
        missing = validate.check_claude_skill_dir_refs(Path("/nonexistent"), content)
        self.assertEqual(missing, ["scripts/does-not-exist.sh"])


class TestCheckScriptsNeedBashPermission(unittest.TestCase):
    def test_script_mentioned_without_bash_permission_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_path = Path(tmp)
            (skill_path / "scripts").mkdir()
            (skill_path / "scripts" / "run.sh").write_text("#!/bin/sh\n")
            content = "Run `${CLAUDE_SKILL_DIR}/scripts/run.sh` to do the thing.\n"
            warning = validate.check_scripts_need_bash_permission(skill_path, {}, content)
            self.assertIsNotNone(warning)
            self.assertIn("run.sh", warning)
            self.assertIn("Bash", warning)
            self.assertIn("permission", warning)

    def test_script_mentioned_with_bash_permission_is_fine(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_path = Path(tmp)
            (skill_path / "scripts").mkdir()
            (skill_path / "scripts" / "run.sh").write_text("#!/bin/sh\n")
            content = "Run `${CLAUDE_SKILL_DIR}/scripts/run.sh` to do the thing.\n"
            frontmatter = {"allowed-tools": "Bash(${CLAUDE_SKILL_DIR}/scripts/run.sh)"}
            warning = validate.check_scripts_need_bash_permission(skill_path, frontmatter, content)
            self.assertIsNone(warning)

    def test_disallowed_tools_blocking_bash_still_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_path = Path(tmp)
            (skill_path / "scripts").mkdir()
            (skill_path / "scripts" / "run.sh").write_text("#!/bin/sh\n")
            content = "Run `${CLAUDE_SKILL_DIR}/scripts/run.sh` to do the thing.\n"
            frontmatter = {"allowed-tools": "Bash", "disallowed-tools": "Bash"}
            warning = validate.check_scripts_need_bash_permission(skill_path, frontmatter, content)
            self.assertIsNotNone(warning)

    def test_no_bundled_scripts_at_all_is_fine(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_path = Path(tmp)
            warning = validate.check_scripts_need_bash_permission(skill_path, {}, "Just prose, no scripts.\n")
            self.assertIsNone(warning)


if __name__ == "__main__":
    unittest.main()
