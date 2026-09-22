#!/usr/bin/env python3
"""Tests for the eval viewer's port reclamation and its embedded data block.

Run: python3 -m unittest skill-artisan/tests/test_generate_review.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Two separate concerns, both about the viewer doing something on the user's
machine that it was never asked to do:

  - _kill_port used to SIGTERM every PID holding the requested port. The
    viewer picks a default port, so "whatever is on 8765" is frequently
    somebody else's dev server, not a stale viewer. It now terminates only
    processes it can positively identify as its own prior instances.

  - generate_html embeds eval output — raw model text, plus the contents of
    whatever third-party skill is under review — into a <script> block. A
    literal `</script>` in that data closed the element early and turned the
    rest into live HTML in a page the viewer auto-opens in a browser,
    same-origin with the server's file-writing POST /api/feedback.
"""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import PLUGIN_ROOT  # noqa: E402

# generate_review.py lives in eval-viewer/, which isn't an importable package
# name (the hyphen), so the directory goes on sys.path directly.
sys.path.insert(0, str(PLUGIN_ROOT / "eval-viewer"))

import generate_review  # noqa: E402


def _cmdline(*argv: str) -> str:
    """Build a /proc/<pid>/cmdline payload: NUL-separated, NUL-terminated."""
    return "\0".join(argv) + "\0"


class TestIsOwnProcess(unittest.TestCase):
    SCRIPT = str(Path(generate_review.__file__).resolve())

    def test_matches_this_script_by_resolved_path(self):
        reader = lambda pid: _cmdline("/usr/bin/python3", self.SCRIPT, "/tmp/ws")  # noqa: E731
        self.assertTrue(generate_review._is_own_process(4242, reader))

    def test_matches_this_script_by_bare_filename(self):
        # Invoked via a relative path or a different-but-equivalent path.
        reader = lambda pid: _cmdline("python3", "eval-viewer/generate_review.py", "ws")  # noqa: E731
        self.assertTrue(generate_review._is_own_process(4242, reader))

    def test_unrelated_process_is_not_ours(self):
        reader = lambda pid: _cmdline("/usr/bin/node", "server.js", "--port", "8765")  # noqa: E731
        self.assertFalse(generate_review._is_own_process(4242, reader))

    def test_similarly_named_script_is_not_ours(self):
        reader = lambda pid: _cmdline("python3", "/opt/other/generate_review_helper.py")  # noqa: E731
        self.assertFalse(generate_review._is_own_process(4242, reader))

    def test_unreadable_cmdline_is_not_verified(self):
        # Permission denied, process already gone, no /proc — all the same
        # answer, and that answer must be "no", never "assume yes".
        def reader(pid):
            return None
        self.assertFalse(generate_review._is_own_process(4242, reader))

    def test_empty_cmdline_is_not_verified(self):
        self.assertFalse(generate_review._is_own_process(4242, lambda pid: ""))
        self.assertFalse(generate_review._is_own_process(4242, lambda pid: "\0\0"))

    def test_real_reader_on_a_nonexistent_pid_returns_false(self):
        # Exercises the default reader rather than an injected one. PID 0 is
        # never a readable /proc entry on any platform.
        self.assertFalse(generate_review._is_own_process(0))


class TestKillPort(unittest.TestCase):
    def _lsof(self, stdout: str):
        return mock.patch.object(
            generate_review.subprocess, "run",
            return_value=mock.Mock(stdout=stdout, stderr="", returncode=0),
        )

    def test_verified_own_pid_is_killed(self):
        killed = []
        with self._lsof("4242\n"), \
                mock.patch.object(generate_review.os, "kill", lambda pid, sig: killed.append((pid, sig))), \
                mock.patch.object(generate_review.time, "sleep", lambda s: None):
            generate_review._kill_port(8765, is_own_process=lambda pid: True)
        self.assertEqual(killed, [(4242, generate_review.signal.SIGTERM)])

    def test_multiple_verified_pids_are_all_killed(self):
        killed = []
        with self._lsof("101\n102\n103\n"), \
                mock.patch.object(generate_review.os, "kill", lambda pid, sig: killed.append(pid)), \
                mock.patch.object(generate_review.time, "sleep", lambda s: None):
            generate_review._kill_port(8765, is_own_process=lambda pid: True)
        self.assertEqual(killed, [101, 102, 103])

    def test_unrecognized_pid_is_refused_and_never_signalled(self):
        killed = []
        with self._lsof("999\n"), \
                mock.patch.object(generate_review.os, "kill", lambda pid, sig: killed.append(pid)), \
                mock.patch("sys.stderr") as err:
            with self.assertRaises(SystemExit) as ctx:
                generate_review._kill_port(8765, is_own_process=lambda pid: False)
        self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(killed, [], "an unidentified process must never be signalled")
        printed = "".join(str(c) for c in err.write.call_args_list)
        self.assertIn("999", printed, "the refusal must name the PIDs holding the port")

    def test_one_unrecognized_pid_blocks_the_whole_operation(self):
        # Killing the verified ones and then failing would leave the port
        # still held and a process needlessly terminated.
        killed = []
        with self._lsof("101\n999\n"), \
                mock.patch.object(generate_review.os, "kill", lambda pid, sig: killed.append(pid)), \
                mock.patch("sys.stderr"):
            with self.assertRaises(SystemExit):
                generate_review._kill_port(8765, is_own_process=lambda pid: pid == 101)
        self.assertEqual(killed, [])

    def test_non_integer_lsof_line_is_tolerated(self):
        # Some lsof builds emit warnings on stdout. One unparseable line must
        # not crash the function or block reclaiming the real PID.
        killed = []
        with self._lsof("lsof: WARNING: can't stat() nfs file system\n4242\n"), \
                mock.patch.object(generate_review.os, "kill", lambda pid, sig: killed.append(pid)), \
                mock.patch.object(generate_review.time, "sleep", lambda s: None):
            generate_review._kill_port(8765, is_own_process=lambda pid: True)
        self.assertEqual(killed, [4242])

    def test_free_port_does_nothing(self):
        killed = []
        with self._lsof(""), \
                mock.patch.object(generate_review.os, "kill", lambda pid, sig: killed.append(pid)):
            generate_review._kill_port(8765, is_own_process=lambda pid: True)
        self.assertEqual(killed, [])

    def test_already_exited_pid_does_not_propagate(self):
        def boom(pid, sig):
            raise ProcessLookupError()
        with self._lsof("4242\n"), \
                mock.patch.object(generate_review.os, "kill", boom), \
                mock.patch.object(generate_review.time, "sleep", lambda s: None):
            generate_review._kill_port(8765, is_own_process=lambda pid: True)  # must not raise

    def test_missing_lsof_is_a_note_not_a_failure(self):
        with mock.patch.object(generate_review.subprocess, "run", side_effect=FileNotFoundError), \
                mock.patch("sys.stderr"):
            generate_review._kill_port(8765, is_own_process=lambda pid: True)  # must not raise

    def test_no_proc_filesystem_gets_a_distinct_message(self):
        # On a platform without /proc nothing can ever be verified, so the
        # user needs to be told that rather than being told the holder is
        # "not ours" — the check never ran.
        real_is_dir = Path.is_dir

        def fake_is_dir(self):
            return False if str(self) == "/proc" else real_is_dir(self)

        with self._lsof("999\n"), \
                mock.patch.object(Path, "is_dir", fake_is_dir), \
                mock.patch.object(generate_review.os, "kill", mock.Mock()) as killer, \
                mock.patch("sys.stderr") as err:
            with self.assertRaises(SystemExit):
                generate_review._kill_port(8765, is_own_process=lambda pid: False)
        killer.assert_not_called()
        printed = "".join(str(c) for c in err.write.call_args_list)
        self.assertIn("cannot be verified on this platform", printed)


class TestEmbeddedDataEscaping(unittest.TestCase):
    PAYLOAD = "</script><script>alert(1)</script>"

    def test_closing_script_tag_in_data_does_not_close_the_block(self):
        rendered = generate_review._json_for_script_block({"output": self.PAYLOAD})
        self.assertNotIn("</script>", rendered)
        self.assertNotIn("<script", rendered)
        self.assertNotIn("<", rendered)

    def test_payload_round_trips_through_json_parse(self):
        rendered = generate_review._json_for_script_block({"output": self.PAYLOAD})
        self.assertEqual(json.loads(rendered)["output"], self.PAYLOAD)

    def test_html_comment_opener_is_escaped(self):
        rendered = generate_review._json_for_script_block({"output": "<!-- <!--"})
        self.assertNotIn("<", rendered)
        self.assertEqual(json.loads(rendered)["output"], "<!-- <!--")

    def test_js_line_separators_survive_as_escapes(self):
        value = "line one two"
        rendered = generate_review._json_for_script_block({"output": value})
        self.assertNotIn(" ", rendered)
        self.assertNotIn(" ", rendered)
        self.assertEqual(json.loads(rendered)["output"], value)

    def test_rendered_page_has_no_literal_closing_tag_in_the_data_block(self):
        run = {"id": "run-1", "outputs": [{"name": "out.txt", "content": self.PAYLOAD}]}
        html = generate_review.generate_html([run], skill_name=self.PAYLOAD)

        start = html.index("const EMBEDDED_DATA = ")
        block = html[start:html.index("\n", start)]
        self.assertNotIn("</script>", block)

        literal = block[len("const EMBEDDED_DATA = "):].rstrip().rstrip(";")
        parsed = json.loads(literal)
        self.assertEqual(parsed["skill_name"], self.PAYLOAD)
        self.assertEqual(parsed["runs"][0]["outputs"][0]["content"], self.PAYLOAD)

        # And the page as a whole still has exactly the script tags the
        # template itself defines — the data contributed none.
        template = (Path(generate_review.__file__).parent / "viewer.html").read_text()
        self.assertEqual(html.count("</script>"), template.count("</script>"))


if __name__ == "__main__":
    unittest.main()
