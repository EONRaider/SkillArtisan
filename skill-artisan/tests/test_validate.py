#!/usr/bin/env python3
"""Regression test for check_path_references and fenced-code-block handling.

Run: python3 -m unittest skill-artisan/tests/test_validate.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Found via the mattpocock/skills real-world audit pilot (2026-08-20, see
benchmark/audit-pilot/RESULTS.md): `wayfinder`'s SKILL.md includes a
```markdown fenced template example containing a worked-example link,
`[<closed ticket title>](link)` — the literal word "link" isn't a real
path, but `check_path_references` matched it anyway and reported a false
"missing file" finding. Fixed by stripping fenced code blocks before
scanning for links. This test guards two things: the fenced-example false
positive is gone, and a real, non-fenced broken link is still caught.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "skill-artisan" / "scripts"

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

    def test_real_broken_link_outside_a_fenced_block_is_still_caught(self):
        body = "See [the reference doc](references/does-not-exist.md) for details.\n"
        missing = validate.check_path_references(Path("/nonexistent"), body)
        self.assertEqual(missing, ["references/does-not-exist.md"])

    def test_real_valid_link_outside_a_fenced_block_still_resolves(self, ):
        with_tmp = REPO_ROOT / "skill-artisan"
        body = "See [the scripts dir](scripts/validate.py) for details.\n"
        missing = validate.check_path_references(with_tmp, body)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
