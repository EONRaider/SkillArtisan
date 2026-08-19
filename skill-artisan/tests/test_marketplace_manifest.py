#!/usr/bin/env python3
"""Guards against marketplace.json / plugin.json drift.

Run: python3 -m unittest skill-artisan/tests/test_marketplace_manifest.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

These two files are edited independently but must stay consistent for
`claude plugin marketplace add` / `claude plugin install` to work at all.
Nothing else enforces that today -- a version bump or rename in one file
with the other left behind breaks installs silently until a user reports it.
"""
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def load_json(path: Path):
    with path.open() as f:
        return json.load(f)


class TestMarketplaceManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.marketplace = load_json(MARKETPLACE_JSON)

    def test_marketplace_json_is_valid_json(self):
        self.assertIsInstance(self.marketplace, dict)

    def test_marketplace_has_required_fields(self):
        for field in ("name", "owner", "plugins"):
            self.assertIn(field, self.marketplace, f"marketplace.json missing '{field}'")
        self.assertIsInstance(self.marketplace["plugins"], list)
        self.assertGreater(len(self.marketplace["plugins"]), 0, "marketplace.json has no plugins")

    def test_owner_has_name(self):
        self.assertIn("name", self.marketplace["owner"])

    def test_each_plugin_source_resolves_to_a_valid_plugin(self):
        for entry in self.marketplace["plugins"]:
            with self.subTest(plugin=entry.get("name")):
                self.assertIn("source", entry)
                source_dir = (MARKETPLACE_JSON.parent.parent / entry["source"]).resolve()
                self.assertTrue(source_dir.is_dir(), f"source dir does not exist: {source_dir}")

                plugin_json_path = source_dir / ".claude-plugin" / "plugin.json"
                self.assertTrue(
                    plugin_json_path.is_file(),
                    f"no .claude-plugin/plugin.json under source: {source_dir}",
                )
                plugin_json = load_json(plugin_json_path)

                for field in ("name", "version", "description", "author"):
                    self.assertIn(field, plugin_json, f"{plugin_json_path} missing '{field}'")

                self.assertEqual(
                    entry.get("name"),
                    plugin_json["name"],
                    f"marketplace.json plugin name '{entry.get('name')}' != "
                    f"{plugin_json_path}'s name '{plugin_json['name']}' -- "
                    "`claude plugin install <name>@<marketplace>` will break",
                )
                self.assertEqual(
                    entry.get("version"),
                    plugin_json["version"],
                    f"marketplace.json version '{entry.get('version')}' != "
                    f"{plugin_json_path}'s version '{plugin_json['version']}' -- "
                    "keep these in sync on every release",
                )


if __name__ == "__main__":
    unittest.main()
