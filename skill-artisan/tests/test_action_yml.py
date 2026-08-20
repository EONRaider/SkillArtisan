#!/usr/bin/env python3
"""Regression test for action.yml's top-level `description` field.

Run: python3 -m unittest skill-artisan/tests/test_action_yml.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

GitHub Marketplace's Action-publishing eligibility check hard-rejects any
description of 125 characters or more — found live on the "Edit release"
form's action.yml validation panel while preparing to publish `v2.4.3`
("Description must be less than 125 characters"). The original description
was a multi-line paragraph (~290 chars); nothing else in the repo's own
tooling would have caught that before an actual publish attempt failed.
This guards against a future edit growing it back past the limit.
action.yml lives one level above the plugin root (see _repo_paths.py) —
absent from an installed copy, since git-subdir only fetches the plugin
root — so these tests skip rather than fail when run from an install.
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import MONOREPO_ROOT  # noqa: E402

ACTION_YML = MONOREPO_ROOT / "action.yml" if MONOREPO_ROOT else None

# Matches only the top-level `description:` key (zero indentation) — the
# `inputs.*.description` fields are indented and must not match here.
TOP_LEVEL_DESCRIPTION_RE = re.compile(r'^description:\s*"?(.*?)"?\s*$', re.MULTILINE)


def get_top_level_description(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("description:"):
            match = TOP_LEVEL_DESCRIPTION_RE.match(line)
            if match:
                return match.group(1)
    raise AssertionError("no top-level 'description:' key found in action.yml")


class TestActionYmlDescription(unittest.TestCase):
    def test_description_under_marketplace_character_limit(self):
        if ACTION_YML is None:
            self.skipTest("action.yml lives one level above the plugin root — absent in an installed copy")
        text = ACTION_YML.read_text()
        description = get_top_level_description(text)
        self.assertLess(
            len(description), 125,
            f"action.yml's description is {len(description)} chars — GitHub Marketplace "
            "rejects anything >= 125 chars at publish time",
        )

    def test_description_is_non_empty(self):
        if ACTION_YML is None:
            self.skipTest("action.yml lives one level above the plugin root — absent in an installed copy")
        text = ACTION_YML.read_text()
        description = get_top_level_description(text)
        self.assertTrue(description.strip())


if __name__ == "__main__":
    unittest.main()
