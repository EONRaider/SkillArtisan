#!/usr/bin/env python3
"""Tests for gha_audit.py — the GitHub Action entrypoint. Fully offline: the
LLM-response parsing/validation is tested directly against fake response
strings (no network), and skill discovery/report rendering run against this
repo's existing test fixtures.

Run: python3 -m unittest skill-artisan/tests/test_gha_audit.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

sys.path.insert(0, str(SCRIPTS_DIR))

import audit  # noqa: E402
import gha_audit  # noqa: E402


class TestParseFixResponse(unittest.TestCase):
    def test_parses_well_formed_response(self):
        text = '{"summary": "fixed it", "files": [{"path": "SKILL.md", "content": "---\\nname: x\\n---\\n"}]}'
        result = gha_audit.parse_fix_response(text)
        self.assertEqual(result["summary"], "fixed it")
        self.assertEqual(result["files"][0]["path"], "SKILL.md")

    def test_strips_markdown_code_fences(self):
        text = '```json\n{"summary": "s", "files": [{"path": "SKILL.md", "content": "x"}]}\n```'
        result = gha_audit.parse_fix_response(text)
        self.assertEqual(result["summary"], "s")

    def test_rejects_invalid_json(self):
        with self.assertRaises(ValueError):
            gha_audit.parse_fix_response("not json at all")

    def test_rejects_missing_summary(self):
        with self.assertRaises(ValueError):
            gha_audit.parse_fix_response('{"files": [{"path": "a", "content": "b"}]}')

    def test_rejects_missing_files(self):
        with self.assertRaises(ValueError):
            gha_audit.parse_fix_response('{"summary": "s"}')

    def test_rejects_empty_files_list(self):
        with self.assertRaises(ValueError):
            gha_audit.parse_fix_response('{"summary": "s", "files": []}')

    def test_rejects_malformed_file_entry(self):
        with self.assertRaises(ValueError):
            gha_audit.parse_fix_response('{"summary": "s", "files": [{"path": "a"}]}')

    def test_rejects_absolute_path(self):
        with self.assertRaises(ValueError):
            gha_audit.parse_fix_response('{"summary": "s", "files": [{"path": "/etc/passwd", "content": "x"}]}')

    def test_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            gha_audit.parse_fix_response('{"summary": "s", "files": [{"path": "../../etc/passwd", "content": "x"}]}')


class TestApplyFixFiles(unittest.TestCase):
    def test_writes_files_inside_skill_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_path = Path(tmp) / "my-skill"
            skill_path.mkdir()
            gha_audit.apply_fix_files(skill_path, [{"path": "SKILL.md", "content": "hello"}])
            self.assertEqual((skill_path / "SKILL.md").read_text(), "hello")

    def test_writes_nested_new_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_path = Path(tmp) / "my-skill"
            skill_path.mkdir()
            gha_audit.apply_fix_files(skill_path, [{"path": "evals/evals.json", "content": "{}"}])
            self.assertEqual((skill_path / "evals" / "evals.json").read_text(), "{}")


class TestBuildFixPrompt(unittest.TestCase):
    def test_includes_skill_name_and_findings(self):
        fail_items = [{"id": "evals-present", "status": "FAIL", "detail": "no evals/evals.json"}]
        prompt = gha_audit.build_fix_prompt("my-skill", "---\nname: my-skill\n---\n", fail_items)
        self.assertIn("my-skill", prompt)
        self.assertIn("evals-present", prompt)
        self.assertIn("no evals/evals.json", prompt)
        self.assertIn("additive", prompt.lower())


class TestRenderMarkdownSummary(unittest.TestCase):
    def test_empty_reports(self):
        self.assertIn("No skills found", gha_audit.render_markdown_summary([], {}))

    def test_renders_table_row_per_skill(self):
        report = audit.audit_skill(FIXTURES_DIR / "model-triggered-fixture", None, None)
        summary = gha_audit.render_markdown_summary([report], {})
        self.assertIn("model-triggered-fixture", summary)
        self.assertIn(report["decision"]["decision"], summary)

    def test_includes_pr_result_column(self):
        report = audit.audit_skill(FIXTURES_DIR / "model-triggered-fixture", None, None)
        summary = gha_audit.render_markdown_summary([report], {report["skill_name"]: "PR opened"})
        self.assertIn("PR opened", summary)

    def test_renders_error_reports(self):
        summary = gha_audit.render_markdown_summary([{"skill_name": "broken", "skill_path": "/x", "error": "boom"}], {})
        self.assertIn("broken", summary)
        self.assertIn("boom", summary)


class TestSkillDiscovery(unittest.TestCase):
    def test_finds_fixture_skills(self):
        from _common import find_skill_dirs
        found = find_skill_dirs([FIXTURES_DIR])
        names = {p.name for p in found}
        self.assertIn("model-triggered-fixture", names)
        self.assertIn("user-invoked-fixture", names)


if __name__ == "__main__":
    unittest.main()
