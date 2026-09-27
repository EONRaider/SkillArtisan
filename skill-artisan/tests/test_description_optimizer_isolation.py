#!/usr/bin/env python3
"""Regression tests for how description_optimizer.py runs its `claude -p` children.

Run: python3 -m unittest skill-artisan/tests/test_description_optimizer_isolation.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

`claude` is replaced on PATH by tests/fixtures/fake_claude.py, which spends
no usage and records what each child saw. Four bugs, each found while
optimizing a real plugin skill's description:

  1. Every worker installed its candidate copy into ONE shared project root,
     so with --num-workers > 1 each child saw its siblings' identically-
     described copies. A trigger on a sibling's copy doesn't match the run's
     own randomized name and was scored as a miss.
  2. That shared root came from walking up from cwd to the first `.claude/`,
     which from a directory without one is HOME — so test copies were
     written into the user's own ~/.claude/skills/.
  3. After seeing the trigger the loop kept streaming until the child
     exited or timed out: every triggered query ran the whole skill, and a
     timeout then printed a "counted as not-triggered" warning for a run that
     returned True.
  4. A --model value the CLI rejects failed only at the first rewrite call,
     after a whole eval pass had been spent (and silently scored 0%).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import stat
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import PLUGIN_ROOT, SCRIPTS_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))

import description_optimizer as do  # noqa: E402

FAKE_CLAUDE = PLUGIN_ROOT / "tests" / "fixtures" / "fake_claude.py"


class FakeClaudeTestCase(unittest.TestCase):
    """Puts the fake `claude` first on PATH and gives each test a private
    temp dir, log dir and system temp dir (so isolated roots are created
    somewhere known and checkable)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name).resolve()
        self.addCleanup(self._tmp.cleanup)

        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        shim = bin_dir / "claude"
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE_CLAUDE}" "$@"\n')
        shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        self.log_dir = self.tmp / "log"
        self.log_dir.mkdir()
        self.system_tmp = self.tmp / "system-tmp"
        self.system_tmp.mkdir()

        env = mock.patch.dict(os.environ, {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "FAKE_CLAUDE_LOG_DIR": str(self.log_dir),
            "TMPDIR": str(self.system_tmp),
        })
        env.start()
        self.addCleanup(env.stop)
        tempdir = mock.patch.object(tempfile, "tempdir", str(self.system_tmp))
        tempdir.start()
        self.addCleanup(tempdir.stop)

    def set_mode(self, mode: str, **extra: str) -> None:
        values = {"FAKE_CLAUDE_MODE": mode}
        values.update({f"FAKE_CLAUDE_{k.upper()}": v for k, v in extra.items()})
        os.environ.update(values)

    def records(self) -> list[dict]:
        return [json.loads(p.read_text()) for p in sorted(self.log_dir.glob("*.json"))]

    def assert_no_isolated_roots_left(self) -> None:
        leftovers = list(self.system_tmp.glob(f"{do.ISOLATED_ROOT_PREFIX}*"))
        self.assertEqual(leftovers, [], "isolated project roots must be removed after use")


class TestParallelWorkersAreIsolated(FakeClaudeTestCase):
    """Bug 1: concurrent children must never see each other's candidates."""

    def test_concurrent_runs_each_see_only_their_own_candidate(self):
        # The fake model "thinks" long enough that all four children are
        # alive at the moment each one lists .claude/skills/ and picks the
        # first entry — exactly when a shared root exposed sibling copies.
        self.set_mode("trigger", think_seconds="2.5", skill_seconds="30")
        eval_set = [
            {"query": "tidy up this module", "should_trigger": True},
            {"query": "clean up dead code", "should_trigger": True},
        ]
        result = do.run_eval(eval_set, "cleanup", "Removes dead code.", num_workers=4, timeout=60,
                             runs_per_query=2)

        records = self.records()
        self.assertEqual(len(records), 4)
        # The scenario only proves anything if the children actually overlapped.
        latest_start = max(r["started"] for r in records)
        earliest_decision = min(r["decided"] for r in records)
        self.assertLess(latest_start, earliest_decision, "children did not run concurrently")

        for r in records:
            self.assertEqual(len(r["skills_seen"]), 1, f"a child saw sibling candidates: {r['skills_seen']}")
            self.assertTrue(r["skills_seen"][0].startswith("cleanup-skill-"))
        self.assertEqual(len({r["cwd"] for r in records}), 4, "each child needs its own project root")

        self.assertEqual(result["summary"]["passed"], 2)
        for r in result["results"]:
            self.assertEqual(r["triggers"], 2, r)
            self.assertEqual(r["trigger_rate"], 1.0, r)
        self.assert_no_isolated_roots_left()


class TestNothingIsWrittenOutsideTheIsolatedRoot(FakeClaudeTestCase):
    """Bug 2: HOME's .claude/ is the user config dir, never a test root."""

    def test_running_from_a_directory_under_home_leaves_home_untouched(self):
        home = self.tmp / "home"
        (home / ".claude" / "skills").mkdir(parents=True)
        work = home / "projects" / "no-claude-dir-here"
        work.mkdir(parents=True)
        self.set_mode("trigger")

        with mock.patch.dict(os.environ, {"HOME": str(home)}), _chdir(work):
            triggered = do.run_single_query("clean this up", "cleanup", "Removes dead code.", timeout=30)

        self.assertTrue(triggered)
        self.assertEqual(list((home / ".claude" / "skills").iterdir()), [])
        (record,) = self.records()
        cwd = Path(record["cwd"]).resolve()
        self.assertEqual(cwd.parent, self.system_tmp)
        self.assertTrue(cwd.name.startswith(do.ISOLATED_ROOT_PREFIX))
        self.assert_no_isolated_roots_left()

    def test_rewrite_calls_also_run_in_an_isolated_root(self):
        out = do._call_claude("rewrite this", "opus")
        self.assertIn("<new_description>", out)
        (record,) = self.records()
        self.assertEqual(Path(record["cwd"]).resolve().parent, self.system_tmp)
        self.assert_no_isolated_roots_left()

    def test_refuses_a_temp_dir_under_a_directory_with_its_own_claude_dir(self):
        home = self.tmp / "home"
        (home / ".claude").mkdir(parents=True)
        tmp_under_home = home / "tmp"
        tmp_under_home.mkdir()
        with mock.patch.object(tempfile, "tempdir", str(tmp_under_home)):
            with self.assertRaises(do.IsolationError) as ctx:
                do.make_isolated_project_root()
            with self.assertRaises(do.IsolationError):
                do.check_isolation()
        self.assertIn(str(home), str(ctx.exception))
        self.assertEqual(list(tmp_under_home.iterdir()), [], "a refused root must not be left behind")


class TestTriggerDetectionStopsTheChild(FakeClaudeTestCase):
    """Bug 3: stop as soon as the trigger is seen; warn only on a real timeout."""

    def test_returns_as_soon_as_the_skill_is_invoked_and_kills_the_child(self):
        self.set_mode("trigger", skill_seconds="60")
        stderr = io.StringIO()
        started = time.monotonic()
        with contextlib.redirect_stderr(stderr):
            triggered = do.run_single_query("clean this up", "cleanup", "Removes dead code.", timeout=45)
        elapsed = time.monotonic() - started

        self.assertTrue(triggered)
        self.assertLess(elapsed, 20, "the loop kept streaming after the trigger")
        (record,) = self.records()
        self.assertIn("invoked", record)
        self.assertNotIn("skill_finished", record, "the child was allowed to run the skill")
        self.assertNotIn("WARNING", stderr.getvalue())
        self.assert_no_isolated_roots_left()

    def test_a_real_timeout_without_a_trigger_warns(self):
        self.set_mode("hang")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            triggered = do.run_single_query("clean this up", "cleanup", "Removes dead code.", timeout=2)
        self.assertFalse(triggered)
        self.assertIn("timed out", stderr.getvalue())
        self.assert_no_isolated_roots_left()

    def test_a_clean_non_trigger_does_not_warn(self):
        self.set_mode("no-trigger")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            triggered = do.run_single_query("what's the weather", "cleanup", "Removes dead code.", timeout=30)
        self.assertFalse(triggered)
        self.assertEqual(stderr.getvalue(), "")

    def test_a_failing_child_is_reported_rather_than_silently_scored(self):
        self.set_mode("trigger")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            triggered = do.run_single_query("clean this up", "cleanup", "Removes dead code.", timeout=30,
                                            model="claude-not-a-model")
        self.assertFalse(triggered)
        self.assertIn("exited 1", stderr.getvalue())


class TestChildInvocationFlags(FakeClaudeTestCase):
    """Bug 4 of the report: user settings, plugins and MCP servers leaked in."""

    def _flag_value(self, argv: list[str], flag: str) -> str:
        self.assertIn(flag, argv)
        return argv[argv.index(flag) + 1]

    def test_trigger_runs_exclude_user_settings_and_restrict_tools(self):
        self.set_mode("no-trigger")
        do.run_single_query("q", "cleanup", "d", timeout=30)
        (record,) = self.records()
        argv = record["argv"]
        self.assertEqual(self._flag_value(argv, "--setting-sources"), "project,local")
        self.assertEqual(self._flag_value(argv, "--tools"), "Skill,Read,Glob,Grep")
        self.assertIn("--strict-mcp-config", argv)

    def test_rewrite_calls_get_no_tools(self):
        do._call_claude("rewrite this", None)
        (record,) = self.records()
        self.assertEqual(self._flag_value(record["argv"], "--tools"), "")
        self.assertEqual(self._flag_value(record["argv"], "--setting-sources"), "project,local")


class TestModelPreflight(FakeClaudeTestCase):
    """Bug 5 of the report: fail before the eval pass, not after it."""

    def _run_args(self, model: str) -> argparse.Namespace:
        skill = self.tmp / "cleanup"
        skill.mkdir()
        (skill / "SKILL.md").write_text("---\nname: cleanup\ndescription: Removes dead code.\n---\n\nBody.\n")
        eval_set = self.tmp / "evals.json"
        eval_set.write_text(json.dumps([{"query": "tidy up", "should_trigger": True}]))
        return argparse.Namespace(
            eval_set=str(eval_set), skill_path=str(skill), description=None, num_workers=1, timeout=30,
            max_iterations=2, runs_per_query=1, trigger_threshold=0.5, holdout=0.0, model=model,
            verbose=False, report="none", no_browser=True, results_dir=None,
        )

    def test_an_unknown_model_id_fails_before_any_trigger_run(self):
        self.set_mode("trigger")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            code = do.cmd_run(self._run_args("claude-opus-5-5"))
        self.assertNotEqual(code, 0)
        records = self.records()
        self.assertEqual(len(records), 1, "only the preflight call may run")
        self.assertEqual(records[0]["exit"], 1)
        self.assertIn("opus, sonnet, haiku", stderr.getvalue())

    def test_an_alias_passes_the_preflight(self):
        self.assertIsNone(do.preflight_model("opus"))


@contextlib.contextmanager
def _chdir(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
