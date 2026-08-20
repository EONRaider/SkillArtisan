#!/usr/bin/env python3
"""Regression test for find_skill_dirs' symlink handling and its nested-
mini-plugin discovery pattern.

Run: python3 -m unittest skill-artisan/tests/test_common_find_skill_dirs.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Found via the real-world audit pilot's Phase 6 (2026-08-20, see
benchmark/audit-pilot/RESULTS.md): `alirezarezvani/claude-skills`
symlink-mirrors every skill into four cross-tool directories (`.codex/`,
`.gemini/`, `.hermes/`, `.vibe/`) for compatibility with other agent
products. `Path.glob()` follows symlinks for ordinary path components, so
the unfiltered function re-discovered the same real skills hundreds of
times through their mirrors — inflating one real repo's skill count by
roughly 3x. This test guards two things: a symlinked SKILL.md (or a
symlinked directory anywhere between the search root and the file) is
never returned, and the newer nested-mini-plugin pattern
(category/plugin/skills/name/SKILL.md) still finds real, non-symlinked
skills at that depth.
"""
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "skill-artisan" / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

from _common import find_skill_dirs  # noqa: E402


def make_skill(path: Path, name: str) -> None:
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(f"---\nname: {name}\ndescription: test\n---\nBody.\n")


class TestFindSkillDirsSymlinks(unittest.TestCase):
    def test_symlinked_skill_md_file_is_not_returned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real-skill"
            make_skill(real, "real-skill")
            mirror = root / ".codex" / "skills" / "real-skill"
            mirror.mkdir(parents=True)
            (mirror / "SKILL.md").symlink_to(real / "SKILL.md")

            found = find_skill_dirs([root])
            self.assertIn(real, found)
            self.assertNotIn(mirror, found)

    def test_symlinked_intermediate_directory_is_not_traversed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "domain" / "skills" / "real-skill"
            make_skill(real, "real-skill")
            mirror_dir = root / ".gemini" / "skills"
            mirror_dir.mkdir(parents=True)
            (mirror_dir / "real-skill").symlink_to(real, target_is_directory=True)

            found = find_skill_dirs([root])
            self.assertIn(real, found)
            self.assertNotIn(mirror_dir / "real-skill", found)

    def test_nested_mini_plugin_depth_is_discovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "engineering" / "some-plugin" / "skills" / "some-skill"
            make_skill(nested, "some-skill")

            found = find_skill_dirs([root])
            self.assertIn(nested, found)


if __name__ == "__main__":
    unittest.main()
