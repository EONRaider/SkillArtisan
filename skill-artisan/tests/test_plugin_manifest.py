#!/usr/bin/env python3
"""Guards plugin.json validity and version-pin drift, post-marketplace split.

Run: python3 -m unittest skill-artisan/tests/test_plugin_manifest.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Successor to test_marketplace_manifest.py. This repo used to self-host a
root .claude-plugin/marketplace.json declaring the "eonraider" marketplace,
and that test guarded marketplace/plugin version sync. That declaration
collided with EONRaider/foreman declaring the SAME marketplace name — only
one "eonraider" marketplace can be registered per install — so the
marketplace-level manifest moved to the dedicated EONRaider/claude-plugins
repo, which references this repo externally (git-subdir, path
"skill-artisan", ref "master"). The cross-repo half of the old sync
invariant can't be tested from here; what remains testable locally is:
(1) plugin.json is valid and carries the fields installs need, (2) the
version pins that still live in this repo (plugin.json + README's Action
pin and "Current version" line) agree, and (3) the root marketplace.json
does not silently come back and recreate the name collision.

The README/root-marketplace.json checks need the wrapping monorepo, which
git-subdir installs never fetch (see _repo_paths.py) — they skip, not
fail, when running from an install. plugin.json itself is always present
either way, so the field-validity check always runs.
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import MONOREPO_ROOT, PLUGIN_ROOT  # noqa: E402

PLUGIN_JSON = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
README = MONOREPO_ROOT / "README.md" if MONOREPO_ROOT else None


class TestPluginManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with PLUGIN_JSON.open() as f:
            cls.plugin = json.load(f)
        cls.readme = README.read_text() if README else None

    def test_plugin_json_has_required_fields(self):
        for field in ("name", "version", "description", "author"):
            self.assertIn(field, self.plugin, f"plugin.json missing '{field}'")
        self.assertEqual(self.plugin["name"], "skillartisan",
                         "renaming the plugin breaks `claude plugin install skillartisan@eonraider` "
                         "and the EONRaider/claude-plugins marketplace entry")

    def test_readme_version_pins_match_plugin_json(self):
        if MONOREPO_ROOT is None:
            self.skipTest("README.md lives one level above the plugin root — absent in an installed copy")
        version = self.plugin["version"]
        action_pins = re.findall(r"EONRaider/SkillArtisan@v(\S+)", self.readme)
        self.assertTrue(action_pins, "README lost its GitHub Action pin (`- uses: EONRaider/SkillArtisan@vX.Y.Z`)")
        for pin in action_pins:
            self.assertEqual(pin, version,
                             f"README Action pin v{pin} != plugin.json version {version} — "
                             "bump both on every release")
        current_line = re.search(r"Current version: `([^`]+)`", self.readme)
        self.assertIsNotNone(current_line, "README lost its 'Current version' line")
        self.assertEqual(current_line.group(1), version,
                         f"README 'Current version' {current_line.group(1)} != plugin.json {version}")

    def test_no_self_hosted_marketplace_manifest(self):
        """The root marketplace.json moved to EONRaider/claude-plugins because
        two repos declaring the same "eonraider" marketplace name collide.
        Reintroducing it here silently recreates that collision."""
        if MONOREPO_ROOT is None:
            self.skipTest("no wrapping monorepo to check in an installed copy — "
                          "git-subdir only ever fetches the plugin root, so this collision "
                          "can't recur from an install regardless")
        self.assertFalse((MONOREPO_ROOT / ".claude-plugin" / "marketplace.json").exists(),
                         "root .claude-plugin/marketplace.json is back — the 'eonraider' marketplace "
                         "is canonically hosted in EONRaider/claude-plugins now")

    def test_readme_points_at_unified_marketplace(self):
        if MONOREPO_ROOT is None:
            self.skipTest("README.md lives one level above the plugin root — absent in an installed copy")
        self.assertIn("claude plugin marketplace add EONRaider/claude-plugins", self.readme,
                      "README install instructions must point at the unified marketplace repo")
        self.assertNotIn("marketplace add eonraider/SkillArtisan", self.readme,
                         "README still tells users to add this repo directly as a marketplace — "
                         "that path no longer hosts a marketplace.json")


if __name__ == "__main__":
    unittest.main()
