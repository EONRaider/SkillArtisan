#!/usr/bin/env python3
"""Regression test for check_evals_present's evals.json shape handling.

Run: python3 -m unittest skill-artisan/tests/test_audit.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Found via the mattpocock/skills + daymade/claude-code-skills real-world
audit pilot (2026-08-20, see benchmark/audit-pilot/RESULTS.md): running
`audit.py`/`aggregate_findings.py` against all 92 skills in
daymade-claude-code-skills crashed outright on `github-sensitive-data-cleanup`,
whose evals/evals.json is a bare JSON list (not this project's
{"evals": [...]} wrapper) — `data.get("evals", [])` raised AttributeError
because a list has no `.get`. This is a real shape used in the wild, not a
hypothetical: the corpus's own meta.json for that skill documents adapting
it (benchmark/corpus/github-sensitive-data-cleanup/meta.json). Fixed by
accepting both shapes; anything else reports a clear FAIL instead of
crashing the whole audit run.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))

import audit  # noqa: E402


def check_with_evals_json(content) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        skill_path = Path(tmp)
        evals_dir = skill_path / "evals"
        evals_dir.mkdir()
        (evals_dir / "evals.json").write_text(json.dumps(content))
        return audit.check_evals_present(skill_path)


class TestCheckEvalsPresent(unittest.TestCase):
    def test_bare_list_shape_is_counted_not_crashed_on(self):
        result = check_with_evals_json([{"name": "case one"}, {"name": "case two"}, {"name": "case three"}])
        self.assertEqual(result["status"], "PASS")
        self.assertIn("3 eval case(s)", result["detail"])

    def test_wrapped_dict_shape_still_works(self):
        result = check_with_evals_json({"evals": [{"id": "e1"}, {"id": "e2"}, {"id": "e3"}]})
        self.assertEqual(result["status"], "PASS")
        self.assertIn("3 eval case(s)", result["detail"])

    def test_short_bare_list_warns_not_fails(self):
        result = check_with_evals_json([{"id": "only-one"}])
        self.assertEqual(result["status"], "WARN")

    def test_unexpected_scalar_shape_fails_cleanly(self):
        result = check_with_evals_json("not an object or a list")
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("bare str", result["detail"])


if __name__ == "__main__":
    unittest.main()
