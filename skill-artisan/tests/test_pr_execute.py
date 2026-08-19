#!/usr/bin/env python3
"""Tests for pr_execute.py's pure/mockable logic — no real git or gh
invocations. Covers the additive-only hard invariant, the deterministic
branch-naming idempotency key, and the same-repo-vs-fork branch filter for
finding an existing PR, since these are exactly the properties the
GitHub Action's fix-PR path depends on.

Run: python3 -m unittest skill-artisan/tests/test_pr_execute.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "skill-artisan" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pr_execute  # noqa: E402


class TestVerifyAdditiveOnly(unittest.TestCase):
    def test_pure_addition_passes(self):
        ok, violations = pr_execute.verify_additive_only([("A ", "SKILL.md"), ("??", "new-file.md")])
        self.assertTrue(ok)
        self.assertEqual(violations, [])

    def test_in_place_modification_passes(self):
        ok, violations = pr_execute.verify_additive_only([(" M", "SKILL.md")])
        self.assertTrue(ok)

    def test_deletion_is_rejected(self):
        ok, violations = pr_execute.verify_additive_only([(" D", "SKILL.md")])
        self.assertFalse(ok)
        self.assertIn("D SKILL.md", violations)

    def test_rename_is_rejected(self):
        ok, violations = pr_execute.verify_additive_only([("R ", "old.md -> new.md")])
        self.assertFalse(ok)

    def test_deletion_in_index_column_is_rejected(self):
        ok, violations = pr_execute.verify_additive_only([("D ", "SKILL.md")])
        self.assertFalse(ok)

    def test_mixed_changes_reports_only_violations(self):
        ok, violations = pr_execute.verify_additive_only([("A ", "new.md"), (" D", "old.md"), (" M", "SKILL.md")])
        self.assertFalse(ok)
        self.assertEqual(len(violations), 1)


class TestBranchNameFor(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(pr_execute.branch_name_for("my-skill"), pr_execute.branch_name_for("my-skill"))

    def test_safe_characters_only(self):
        name = pr_execute.branch_name_for("My Skill! (v2)")
        self.assertRegex(name, r"^[a-z0-9._-]+$")

    def test_has_expected_prefix(self):
        self.assertTrue(pr_execute.branch_name_for("x").startswith("skillartisan-audit-fix-"))


class TestFindExistingPr(unittest.TestCase):
    def test_direct_push_uses_bare_branch_name(self):
        with patch.object(pr_execute, "run_gh") as mock_gh:
            mock_gh.return_value.stdout = ""
            pr_execute.find_existing_pr("owner/repo", "owner", "skillartisan-audit-fix-x", direct_push=True)
        args = mock_gh.call_args[0][0]
        head_index = args.index("--head")
        self.assertEqual(args[head_index + 1], "skillartisan-audit-fix-x")

    def test_forked_push_uses_owner_prefixed_branch(self):
        with patch.object(pr_execute, "run_gh") as mock_gh:
            mock_gh.return_value.stdout = ""
            pr_execute.find_existing_pr("owner/repo", "forker", "skillartisan-audit-fix-x", direct_push=False)
        args = mock_gh.call_args[0][0]
        head_index = args.index("--head")
        self.assertEqual(args[head_index + 1], "forker:skillartisan-audit-fix-x")

    def test_returns_none_for_empty_result(self):
        with patch.object(pr_execute, "run_gh") as mock_gh:
            mock_gh.return_value.stdout = "  "
            result = pr_execute.find_existing_pr("owner/repo", "owner", "branch", direct_push=True)
        self.assertIsNone(result)

    def test_returns_url(self):
        with patch.object(pr_execute, "run_gh") as mock_gh:
            mock_gh.return_value.stdout = "https://github.com/owner/repo/pull/1\n"
            result = pr_execute.find_existing_pr("owner/repo", "owner", "branch", direct_push=True)
        self.assertEqual(result, "https://github.com/owner/repo/pull/1")


class TestNormalizeRepoSlug(unittest.TestCase):
    def test_bare_slug_unchanged(self):
        self.assertEqual(pr_execute.normalize_repo_slug("owner/repo"), "owner/repo")

    def test_ssh_url(self):
        self.assertEqual(pr_execute.normalize_repo_slug("git@github.com:owner/repo.git"), "owner/repo")

    def test_https_url(self):
        self.assertEqual(pr_execute.normalize_repo_slug("https://github.com/owner/repo.git"), "owner/repo")

    def test_https_url_no_dotgit(self):
        self.assertEqual(pr_execute.normalize_repo_slug("https://github.com/owner/repo"), "owner/repo")

    def test_case_insensitive(self):
        self.assertEqual(pr_execute.normalize_repo_slug("Owner/Repo"), "owner/repo")


class TestIsSameRepo(unittest.TestCase):
    def test_true_when_origin_matches_upstream(self):
        with patch.object(pr_execute, "get_current_remote_url", return_value="git@github.com:EONRaider/SkillArtisan.git"):
            self.assertTrue(pr_execute.is_same_repo(Path("/tmp/x"), "EONRaider/SkillArtisan"))

    def test_false_when_origin_differs(self):
        with patch.object(pr_execute, "get_current_remote_url", return_value="git@github.com:someone-else/other.git"):
            self.assertFalse(pr_execute.is_same_repo(Path("/tmp/x"), "EONRaider/SkillArtisan"))

    def test_false_when_no_remote(self):
        with patch.object(pr_execute, "get_current_remote_url", return_value=""):
            self.assertFalse(pr_execute.is_same_repo(Path("/tmp/x"), "EONRaider/SkillArtisan"))


class TestHasPushAccess(unittest.TestCase):
    def test_same_repo_short_circuits_without_gh_call(self):
        with patch.object(pr_execute, "is_same_repo", return_value=True), \
                patch.object(pr_execute, "run_gh") as mock_gh:
            result = pr_execute.has_push_access(Path("/tmp/x"), "EONRaider/SkillArtisan")
        self.assertTrue(result)
        mock_gh.assert_not_called()

    def test_falls_back_to_viewer_permission_for_third_party_repo(self):
        with patch.object(pr_execute, "is_same_repo", return_value=False), \
                patch.object(pr_execute, "run_gh") as mock_gh:
            mock_gh.return_value.returncode = 0
            mock_gh.return_value.stdout = '{"viewerPermission":"WRITE"}'
            result = pr_execute.has_push_access(Path("/tmp/x"), "someone-else/other")
        self.assertTrue(result)

    def test_read_only_permission_is_false(self):
        with patch.object(pr_execute, "is_same_repo", return_value=False), \
                patch.object(pr_execute, "run_gh") as mock_gh:
            mock_gh.return_value.returncode = 0
            mock_gh.return_value.stdout = '{"viewerPermission":"READ"}'
            result = pr_execute.has_push_access(Path("/tmp/x"), "someone-else/other")
        self.assertFalse(result)


class TestEnsureFork(unittest.TestCase):
    def test_same_repo_skips_fork_entirely(self):
        with patch.object(pr_execute, "has_push_access", return_value=True) as mock_access, \
                patch.object(pr_execute, "run_gh") as mock_gh:
            ok, owner = pr_execute.ensure_fork(Path("/tmp/x"), "EONRaider/SkillArtisan")
        self.assertTrue(ok)
        self.assertEqual(owner, "EONRaider")
        mock_access.assert_called_once()
        mock_gh.assert_not_called()

    def test_third_party_without_login_fails_clearly(self):
        with patch.object(pr_execute, "has_push_access", return_value=False), \
                patch.object(pr_execute, "get_authenticated_login", return_value=None):
            ok, error = pr_execute.ensure_fork(Path("/tmp/x"), "someone-else/other")
        self.assertFalse(ok)
        self.assertIn("could not determine", error)


class TestGetChangeStatus(unittest.TestCase):
    def test_parses_porcelain_output(self):
        with patch.object(pr_execute, "run_git") as mock_git:
            mock_git.return_value.stdout = " M SKILL.md\n?? new-file.md\n"
            changes = pr_execute.get_change_status(Path("/tmp/does-not-matter"))
        self.assertEqual(changes, [(" M", "SKILL.md"), ("??", "new-file.md")])

    def test_skips_blank_lines(self):
        with patch.object(pr_execute, "run_git") as mock_git:
            mock_git.return_value.stdout = "\n M SKILL.md\n\n"
            changes = pr_execute.get_change_status(Path("/tmp/does-not-matter"))
        self.assertEqual(changes, [(" M", "SKILL.md")])


if __name__ == "__main__":
    unittest.main()
