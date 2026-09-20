#!/usr/bin/env python3
"""Regression test for the blocking-interactive-input pattern check.

Run: python3 -m unittest skill-artisan/tests/test_security_scan.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Found via the mattpocock/skills real-world audit pilot (2026-08-20, see
benchmark/audit-pilot/RESULTS.md): the `input(`-matching pattern flagged an
ordinary English comment ("Visible input (non-secret).") as a HIGH-severity
blocking-interactive-input finding, because `\\binput\\s*\\(` matches that
prose just as readily as a real Python `input(...)` call. Fixed by skipping
lines that are entirely a `#` comment for this check. This test guards two
things at once: the false positive is gone, and a real interactive-input
call (in code, not a comment) still gets caught.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))

import security_scan  # noqa: E402


def findings_for(filename: str, content: str) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        skill_path = Path(tmp)
        (skill_path / filename).write_text(content)
        return security_scan.run_pattern_checks(skill_path)


class TestMarkdownCodeSpanExemption(unittest.TestCase):
    """Regression test for issue #20: a markdown doc *teaching* about a
    dangerous pattern or an absolute-path shape — inside a fenced block or
    an inline `code span` — isn't a live instance of it. Mirrors
    validate.py's check_path_references, which already strips exactly this
    for its own false-positive shape. Guards both directions: the
    documentation examples are no longer flagged, and the same patterns
    written outside backticks in a .md file still are.
    """

    def test_inline_code_span_dangerous_pattern_is_not_flagged(self):
        content = (
            "| Check | Pattern |\n"
            "|---|---|\n"
            "| Dangerous code patterns: `os.system(`, `pickle.load(` | HIGH |\n"
        )
        findings = findings_for("security-checklist.md", content)
        checks = [f["check"] for f in findings]
        self.assertNotIn("dangerous-code-pattern", checks)

    def test_inline_code_span_absolute_path_is_not_flagged(self):
        content = "Never `C:\\Users\\...` — paths break across platforms.\n"
        findings = findings_for("writing-philosophy.md", content)
        checks = [f["check"] for f in findings]
        self.assertNotIn("absolute-user-path", checks)

    def test_fenced_code_block_dangerous_pattern_is_not_flagged(self):
        content = (
            "Don't do this:\n"
            "```python\n"
            "os.system(user_input)\n"
            "```\n"
        )
        findings = findings_for("example.md", content)
        checks = [f["check"] for f in findings]
        self.assertNotIn("dangerous-code-pattern", checks)

    def test_real_dangerous_pattern_outside_code_span_still_flagged(self):
        content = "os.system(user_input)\n"
        findings = findings_for("notes.md", content)
        matches = [f for f in findings if f["check"] == "dangerous-code-pattern"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["line"], 1)

    def test_real_absolute_path_outside_code_span_still_flagged(self):
        content = "Config lives at /home/attacker/.ssh/id_rsa on that box.\n"
        findings = findings_for("notes.md", content)
        matches = [f for f in findings if f["check"] == "absolute-user-path"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["line"], 1)

    def test_dangerous_pattern_in_python_file_is_unaffected_by_backticks(self):
        # Backtick isn't valid Python 3 syntax; this only confirms non-.md
        # files never go through the markdown-code-span exemption.
        content = "os.system(f'`{user_input}`')\n"
        findings = findings_for("run.py", content)
        matches = [f for f in findings if f["check"] == "dangerous-code-pattern"]
        self.assertEqual(len(matches), 1)


class TestBlockingInteractiveInput(unittest.TestCase):
    def test_prose_mentioning_input_in_a_comment_is_not_flagged(self):
        content = (
            "#!/usr/bin/env bash\n"
            "# ask KEY \"Prompt\" — read a value into $KEY. Offers the existing .env\n"
            "# value as a default on re-runs (Enter keeps it). Visible input (non-secret).\n"
            "ask() { :; }\n"
        )
        findings = findings_for("template.sh", content)
        checks = [f["check"] for f in findings]
        self.assertNotIn("blocking-interactive-input", checks)

    def test_prose_mentioning_input_in_a_docstring_is_not_flagged(self):
        content = (
            "def apply_input_cell(ws, row, col, value):\n"
            '    """Style a cell as user input (blue font, green fill)."""\n'
            "    pass\n"
        )
        findings = findings_for("format_cell.py", content)
        checks = [f["check"] for f in findings]
        self.assertNotIn("blocking-interactive-input", checks)

    def test_real_python_input_call_is_still_flagged(self):
        content = "value = input('Enter your API key: ')\n"
        findings = findings_for("collect.py", content)
        matches = [f for f in findings if f["check"] == "blocking-interactive-input"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["line"], 1)

    def test_real_bash_read_dash_p_is_still_flagged(self):
        content = "#!/usr/bin/env bash\nread -p 'Enter value: ' value\n"
        findings = findings_for("collect.sh", content)
        matches = [f for f in findings if f["check"] == "blocking-interactive-input"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["line"], 2)


if __name__ == "__main__":
    unittest.main()
