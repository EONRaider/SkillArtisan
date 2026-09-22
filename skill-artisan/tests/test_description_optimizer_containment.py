#!/usr/bin/env python3
"""Tests for description_optimizer.py's containment of what it spawns and moves.

Run: python3 -m unittest skill-artisan/tests/test_description_optimizer_containment.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Two properties, both about this script's side effects on the host machine
rather than on the description it is optimizing:

  - It spawns nested `claude -p` processes with the host project's cwd, so
    without explicit flags the child inherits that project's permission
    allowlist, hooks and MCP servers — and then receives the full body of the
    third-party skill under audit as prompt text. A skill body asking for a
    command to be run would be a request the child is configured to grant.

  - It moves the user's real installed skill aside for the duration of an
    eval and restores it in a `finally`. A `finally` does not run on SIGKILL,
    an OOM kill, or a container teardown, so the skill could be left silently
    uninstalled with nothing recording it.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))

import description_optimizer as do  # noqa: E402


class TestChildClaudeSafetyFlags(unittest.TestCase):
    def test_denies_prompting_so_nothing_is_auto_approved_by_the_host(self):
        flags = do.child_claude_safety_flags()
        self.assertIn("--permission-prompts", flags)
        self.assertEqual(flags[flags.index("--permission-prompts") + 1], "none")

    def test_does_not_inherit_the_host_projects_mcp_servers(self):
        self.assertIn("--strict-mcp-config", do.child_claude_safety_flags())

    def test_denies_the_execution_and_write_tools(self):
        flags = do.child_claude_safety_flags()
        self.assertIn("--disallowedTools", flags)
        denied = set(flags[flags.index("--disallowedTools") + 1:])
        for tool in ("Bash", "Write", "Edit", "WebFetch", "Task"):
            self.assertIn(tool, denied)

    def test_never_bypasses_permissions(self):
        flags = " ".join(do.child_claude_safety_flags())
        self.assertNotIn("dangerously-skip-permissions", flags)
        self.assertNotIn("bypassPermissions", flags)

    def test_the_flags_are_applied_to_every_claude_invocation_in_the_module(self):
        # A new call site that forgets them would reopen the hole silently.
        source = (SCRIPTS_DIR / "description_optimizer.py").read_text()
        spawn_sites = source.count('"claude", "-p"')
        applied = source.count("child_claude_safety_flags()")
        # One definition, one per call site.
        self.assertEqual(applied, spawn_sites + 1,
                         "a `claude -p` call site is missing child_claude_safety_flags()")


class TestHiddenSkillRecovery(unittest.TestCase):
    """The hide/restore cycle has to survive a process that never returns."""

    def _project(self, tmp: str, skill_name: str = "a-real-skill") -> tuple[Path, Path]:
        root = Path(tmp)
        skill = root / ".claude" / "skills" / skill_name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: a-real-skill\ndescription: d\n---\n")
        return root, skill

    def test_hiding_writes_a_sentinel_recording_where_the_skill_went(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, skill = self._project(tmp)
            hidden = do._hide_real_skill(root, "a-real-skill")
            self.assertFalse(skill.exists())
            record = json.loads(do._sentinel_path(root).read_text())
        self.assertEqual(record["skill_name"], "a-real-skill")
        self.assertEqual(record["hidden_path"], str(hidden))

    def test_normal_restore_puts_the_skill_back_and_clears_the_sentinel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, skill = self._project(tmp)
            hidden = do._hide_real_skill(root, "a-real-skill")
            do._restore_real_skill(hidden, "a-real-skill", root)
            self.assertTrue(skill.is_dir())
            self.assertFalse(do._sentinel_path(root).exists())

    def test_a_killed_run_is_recovered_on_the_next_startup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, skill = self._project(tmp)
            do._hide_real_skill(root, "a-real-skill")
            # No _restore_real_skill call at all — the process died here.
            self.assertFalse(skill.exists())

            message = do.recover_orphaned_hidden_skill(root)
            self.assertTrue(skill.is_dir(), "the user's skill must be put back")
            self.assertIn("Restored", message)
            self.assertFalse(do._sentinel_path(root).exists())

    def test_recovery_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, skill = self._project(tmp)
            do._hide_real_skill(root, "a-real-skill")
            do.recover_orphaned_hidden_skill(root)
            self.assertIsNone(do.recover_orphaned_hidden_skill(root))
            self.assertTrue(skill.is_dir())

    def test_no_sentinel_means_nothing_to_do(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, _ = self._project(tmp)
            self.assertIsNone(do.recover_orphaned_hidden_skill(root))

    def test_a_sentinel_written_before_a_crash_in_the_rename_gap_is_a_no_op(self):
        # Sentinel exists but the skill was never actually moved.
        with tempfile.TemporaryDirectory() as tmp:
            root, skill = self._project(tmp)
            do._write_hidden_sentinel(root, "a-real-skill",
                                      skill.with_name("a-real-skill.eval-hidden"))
            self.assertIsNone(do.recover_orphaned_hidden_skill(root))
            self.assertTrue(skill.is_dir(), "the un-moved skill must be left alone")
            self.assertFalse(do._sentinel_path(root).exists())

    def test_recovery_refuses_to_overwrite_a_reinstalled_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, skill = self._project(tmp)
            hidden = do._hide_real_skill(root, "a-real-skill")
            # The user reinstalled it while the orphan was sitting there.
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: a-real-skill\ndescription: new\n---\n")

            message = do.recover_orphaned_hidden_skill(root)
            self.assertIn("Warning", message)
            self.assertTrue(skill.is_dir())
            self.assertTrue(hidden.is_dir(), "neither copy may be destroyed")

    def test_a_corrupt_sentinel_is_discarded_rather_than_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, _ = self._project(tmp)
            sentinel = do._sentinel_path(root)
            sentinel.parent.mkdir(parents=True, exist_ok=True)
            sentinel.write_text("{not json")
            self.assertIsNone(do.recover_orphaned_hidden_skill(root))
            self.assertFalse(sentinel.exists())

    def test_hiding_nothing_leaves_no_sentinel(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude" / "skills").mkdir(parents=True)
            self.assertIsNone(do._hide_real_skill(root, "not-installed"))
            self.assertFalse(do._sentinel_path(root).exists())


if __name__ == "__main__":
    unittest.main()
