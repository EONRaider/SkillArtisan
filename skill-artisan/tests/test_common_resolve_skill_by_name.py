#!/usr/bin/env python3
"""Regression test for _common.resolve_skill_by_name and
default_skill_search_roots — the skill-name-resolution utility ported from
a separate personal skill called "skill-audit" (its own linter searched
`${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills` plus ancestor `.claude/skills`
directories, disambiguating on multiple/fuzzy matches rather than guessing).
SkillArtisan's audit.py/validate.py previously required an exact path
argument only; this lets both accept a bare skill name too.

Run: python3 -m unittest skill-artisan/tests/test_common_resolve_skill_by_name.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))

from _common import SkillResolutionError, default_skill_search_roots, resolve_skill_by_name  # noqa: E402


def make_skill(path: Path, frontmatter_name: str) -> None:
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(f"---\nname: {frontmatter_name}\ndescription: test\n---\nBody.\n")


class TestDefaultSkillSearchRoots(unittest.TestCase):
    def test_walks_up_from_a_nested_start_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "a" / "b" / "c"
            nested.mkdir(parents=True)
            roots = default_skill_search_roots(start=nested)
            self.assertIn(root / ".claude" / "skills", roots)
            self.assertIn(nested / ".claude" / "skills", roots)
            self.assertIn(root / "a" / ".claude" / "skills", roots)

    def test_includes_config_dir_skills_and_plugin_paths(self):
        import os
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": tmp}):
                roots = default_skill_search_roots(start=Path(tmp))
                self.assertIn(Path(tmp) / "skills", roots)
                self.assertIn(Path(tmp) / "plugins" / "cache", roots)
                self.assertIn(Path(tmp) / "plugins" / "marketplaces", roots)

    def test_relative_config_dir_is_resolved_to_absolute(self):
        """A solid-coding review found a relative CLAUDE_CONFIG_DIR produced
        non-absolute search roots, unlike resolve_existing_dir (which always
        returns an absolute, resolved path) -- reproduced directly by
        chdir-ing into a temp dir and pointing CLAUDE_CONFIG_DIR at a
        relative path."""
        import os
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": "relative_config_dir"}):
                    roots = default_skill_search_roots(start=Path(tmp))
            finally:
                os.chdir(original_cwd)
            config_derived = [r for r in roots if "relative_config_dir" in r.parts]
            self.assertTrue(config_derived)
            for root in config_derived:
                self.assertTrue(root.is_absolute(), f"{root} should be absolute")


class TestResolveSkillByName(unittest.TestCase):
    def test_exact_directory_name_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_skill(root / "invoice-parser", "invoice-parser")
            make_skill(root / "other-skill", "other-skill")
            resolved = resolve_skill_by_name("invoice-parser", search_roots=[root])
            self.assertEqual(resolved, root / "invoice-parser")

    def test_exact_frontmatter_name_match_when_directory_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_skill(root / "old-dir-name", "invoice-parser")
            resolved = resolve_skill_by_name("invoice-parser", search_roots=[root])
            self.assertEqual(resolved, root / "old-dir-name")

    def test_no_match_raises_with_empty_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_skill(root / "unrelated-skill", "unrelated-skill")
            with self.assertRaises(SkillResolutionError) as ctx:
                resolve_skill_by_name("invoice-parser", search_roots=[root])
            self.assertEqual(ctx.exception.candidates, [])

    def test_multiple_exact_matches_raises_with_all_candidates_never_guesses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_skill(root / "team-a" / "invoice-parser", "invoice-parser")
            make_skill(root / "team-b" / "invoice-parser", "invoice-parser")
            with self.assertRaises(SkillResolutionError) as ctx:
                resolve_skill_by_name("invoice-parser", search_roots=[root])
            self.assertEqual(len(ctx.exception.candidates), 2)

    def test_fuzzy_only_match_raises_and_lists_candidates_instead_of_guessing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_skill(root / "invoice-parser-v2", "invoice-parser-v2")
            with self.assertRaises(SkillResolutionError) as ctx:
                resolve_skill_by_name("invoice-parser", search_roots=[root])
            self.assertEqual(ctx.exception.candidates, [root / "invoice-parser-v2"])

    def test_exact_match_wins_over_a_fuzzy_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_skill(root / "invoice-parser", "invoice-parser")
            make_skill(root / "invoice-parser-v2", "invoice-parser-v2")
            resolved = resolve_skill_by_name("invoice-parser", search_roots=[root])
            self.assertEqual(resolved, root / "invoice-parser")


if __name__ == "__main__":
    unittest.main()
