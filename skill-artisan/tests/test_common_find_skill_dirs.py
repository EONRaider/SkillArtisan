#!/usr/bin/env python3
"""Regression test for find_skill_dirs' symlink handling and its nested-
mini-plugin / wrapped-plugin / sub-skill discovery patterns.

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

Phase 8 (anthropics/*, 2026-08-20) added two more real shapes on top of
that: `anthropics/financial-services` wraps the same category/plugin/skills
convention in one more `plugins/` directory (117 of 118 skills missed
entirely before this fix); `anthropics/knowledge-work-plugins`' zoom-plugin
nests platform-variant *sub-skills* one or two levels beneath an
already-discovered skill's own directory, each with real, independent
frontmatter, explicitly routed to from the parent skill's own body text
(not example or test content). The same phase confirmed two other vendored
corpora (`alirezarezvani-claude-skills`, `tripleyak-skillforge`) already
contain nested SKILL.md files that are genuinely *not* real skills —
`assets/sample-skill/` and `tests/fixtures/sample-skill/` — bundled example
content inside an unrelated skill's own directory. The new patterns are
anchored precisely enough (requiring the literal `skills` path component at
a specific depth) to recover the former without matching the latter; both
directions are tested below.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402

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

    def test_plugins_wrapper_over_nested_mini_plugin_is_discovered(self):
        """anthropics/financial-services: plugins/<category>/<plugin>/skills/<skill> —
        the same nested-mini-plugin shape as above, wrapped in one more `plugins/`
        directory. Missed 117 of 118 real skills before this pattern was added."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "plugins" / "partner-built" / "spglobal" / "skills" / "earnings-preview"
            make_skill(nested, "earnings-preview")

            found = find_skill_dirs([root])
            self.assertIn(nested, found)

    def test_platform_sub_skill_one_level_deeper_is_discovered(self):
        """anthropics/knowledge-work-plugins' zoom-plugin: a parent skill
        (contact-center) routes to platform-specific sub-skills nested one level
        beneath it (android/, ios/, web/), each a real, independent skill."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "partner-built" / "zoom-plugin" / "skills" / "contact-center"
            make_skill(parent, "build-zoom-contact-center-app")
            variant = parent / "android"
            make_skill(variant, "contact-center/android")

            found = find_skill_dirs([root])
            self.assertIn(parent, found)
            self.assertIn(variant, found)

    def test_platform_sub_skill_two_levels_deeper_is_discovered(self):
        """Same zoom-plugin corpus, meeting-sdk/web/client-view — one level deeper
        still than the single-platform-variant case above."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            variant = root / "partner-built" / "zoom-plugin" / "skills" / "meeting-sdk" / "web" / "client-view"
            make_skill(variant, "meeting-sdk/web/client-view")

            found = find_skill_dirs([root])
            self.assertIn(variant, found)

    def test_top_level_skills_dir_with_two_category_levels_is_discovered(self):
        """aws/agent-toolkit-for-aws: a literal top-level skills/ collection (not
        preceded by any wildcard, unlike every other pattern) with one category
        level before the skill's own directory: skills/core-skills/amazon-bedrock/."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "skills" / "core-skills" / "amazon-bedrock"
            make_skill(nested, "amazon-bedrock")

            found = find_skill_dirs([root])
            self.assertIn(nested, found)

    def test_top_level_skills_dir_with_three_category_levels_is_discovered(self):
        """Same aws/agent-toolkit-for-aws corpus, one level deeper still:
        skills/specialized-skills/database-skills/rds-db2/."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "skills" / "specialized-skills" / "database-skills" / "rds-db2"
            make_skill(nested, "rds-db2")

            found = find_skill_dirs([root])
            self.assertIn(nested, found)

    def test_bundled_example_skill_in_assets_dir_is_not_discovered(self):
        """alirezarezvani-claude-skills' skill-tester bundles a sample skill as
        test fixture content under assets/ — not a real, independently-loadable
        skill. `skills` doesn't sit at the depth the new patterns require here,
        so this must stay excluded."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "engineering" / "skills" / "skill-tester"
            make_skill(real, "skill-tester")
            fixture = real / "assets" / "sample-skill"
            make_skill(fixture, "sample-skill")

            found = find_skill_dirs([root])
            self.assertIn(real, found)
            self.assertNotIn(fixture, found)

    def test_bundled_example_skill_in_test_fixtures_dir_is_not_discovered(self):
        """tripleyak-skillforge bundles a sample skill under scripts/tests/fixtures/
        for its own test suite — same false-positive shape as above, different
        path, no `skills` component anywhere in it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "SKILL.md").write_text("---\nname: skillforge\ndescription: test\n---\nBody.\n")
            fixture = root / "scripts" / "tests" / "fixtures" / "sample-skill"
            make_skill(fixture, "sample-skill")

            found = find_skill_dirs([root])
            self.assertNotIn(fixture, found)

    def test_bundled_template_skill_in_assets_dir_matching_a_root_skills_pattern_is_not_discovered(self):
        """mims-harvard/tooluniverse (Phase 10): a fill-in-the-blanks skill-creation
        template at skills/create-tooluniverse-skill/assets/skill_template/SKILL.md
        structurally matches the Phase 9 skills/*/*/*/SKILL.md pattern (unlike the
        two assets/tests-fixtures cases above, which sit at a depth no pattern
        reaches) — the intermediate-directory exclusion is what catches this one."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "skills" / "create-tooluniverse-skill"
            make_skill(real, "create-tooluniverse-skill")
            template = real / "assets" / "skill_template"
            make_skill(template, "tooluniverse-[domain-name]")

            found = find_skill_dirs([root])
            self.assertIn(real, found)
            self.assertNotIn(template, found)


if __name__ == "__main__":
    unittest.main()
