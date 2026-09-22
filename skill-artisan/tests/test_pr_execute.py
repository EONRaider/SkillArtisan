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
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402
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

    def test_only_queries_open_prs_not_all_states(self):
        with patch.object(pr_execute, "run_gh") as mock_gh:
            mock_gh.return_value.stdout = ""
            pr_execute.find_existing_pr("owner/repo", "owner", "branch", direct_push=True)
        args = mock_gh.call_args[0][0]
        state_index = args.index("--state")
        self.assertEqual(args[state_index + 1], "open",
                          "a closed PR must not count as 'already exists' — the fix never landed, "
                          "so a later run should get a fresh attempt, not a permanent no-op")

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
    """Fixtures are NUL-separated because the parser reads `--porcelain -z`.

    Line-based porcelain C-quotes any path with a space, a quote, or a
    non-ASCII byte, so the path read back out isn't the path on disk. That
    was harmless while these strings were only printed; they are now handed
    to `git add` as the exact set to stage.
    """

    def _status(self, stdout: str):
        with patch.object(pr_execute, "run_git") as mock_git:
            mock_git.return_value.stdout = stdout
            return pr_execute.get_change_status(Path("/tmp/does-not-matter"))

    def test_parses_porcelain_output(self):
        changes = self._status(" M SKILL.md\0?? new-file.md\0")
        self.assertEqual(changes, [(" M", "SKILL.md"), ("??", "new-file.md")])

    def test_skips_blank_entries(self):
        self.assertEqual(self._status("\0 M SKILL.md\0\0"), [(" M", "SKILL.md")])

    def test_path_with_a_space_is_not_quoted_or_truncated(self):
        changes = self._status(" M references/my notes.md\0")
        self.assertEqual(changes, [(" M", "references/my notes.md")])

    def test_non_ascii_path_survives_intact(self):
        changes = self._status(" M references/café.md\0")
        self.assertEqual(changes, [(" M", "references/café.md")])

    def test_rename_source_field_is_not_read_as_a_separate_entry(self):
        # `R  new\0old\0` — the source path follows as its own field.
        changes = self._status("R  new.md\0old.md\0?? extra.md\0")
        self.assertEqual(changes, [("R ", "new.md"), ("??", "extra.md")])


class TestStagePaths(unittest.TestCase):
    """Staging must be the verified set, never `git add -A`.

    -A stages whatever is in the tree when it runs: wider than the set the
    caller inspected (untracked files pass verify_additive_only, which only
    rejects deletions and renames), and later than it (anything written in
    between is picked up). Either way a stray file could be force-pushed to
    a repository this plugin doesn't own.
    """

    def _run(self, paths, returncode=0, stderr=""):
        calls = []

        def fake_git(repo_path, args):
            calls.append(args)
            return SimpleNamespace(returncode=returncode, stdout="", stderr=stderr)

        with patch.object(pr_execute, "run_git", fake_git):
            ok, err = pr_execute.stage_paths(Path("/tmp/x"), paths)
        return ok, err, calls

    def test_stages_exactly_the_given_paths(self):
        ok, _, calls = self._run(["SKILL.md", "references/a.md"])
        self.assertTrue(ok)
        self.assertEqual(calls, [["add", "--", "SKILL.md", "references/a.md"]])

    def test_never_uses_add_dash_a(self):
        _, _, calls = self._run(["SKILL.md"])
        flat = [arg for call in calls for arg in call]
        self.assertNotIn("-A", flat)
        self.assertNotIn("--all", flat)

    def test_uses_a_double_dash_so_a_path_cannot_be_read_as_an_option(self):
        ok, _, calls = self._run(["--cached"])
        self.assertTrue(ok)
        self.assertEqual(calls[0][:2], ["add", "--"])

    def test_large_change_sets_are_batched(self):
        paths = [f"f{i}.md" for i in range(450)]
        ok, _, calls = self._run(paths)
        self.assertTrue(ok)
        self.assertEqual(len(calls), 3)
        staged = [a for call in calls for a in call[2:]]
        self.assertEqual(staged, paths)

    def test_a_failing_add_is_reported(self):
        ok, err, _ = self._run(["SKILL.md"], returncode=1, stderr="fatal: pathspec")
        self.assertFalse(ok)
        self.assertIn("pathspec", err)

    def test_empty_path_list_is_refused(self):
        ok, err, calls = self._run([])
        self.assertFalse(ok)
        self.assertEqual(calls, [])


class TestPushUsesLease(unittest.TestCase):
    """--force would overwrite a remote branch whatever is on it, including
    commits this run never saw. --force-with-lease keeps the
    reset-my-own-branch case working and fails the clobber case loudly."""

    def _push(self, results):
        calls = []
        seq = list(results)

        def fake_git(repo_path, args):
            calls.append(args)
            if args[0] == "push":
                return SimpleNamespace(returncode=seq.pop(0), stdout="", stderr="stale info: refusing")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with patch.object(pr_execute, "run_git", fake_git), \
                patch.object(pr_execute, "stage_paths", return_value=(True, "")), \
                patch.object(pr_execute, "is_same_repo", return_value=True):
            ok, err = pr_execute.create_branch_commit_push(
                Path("/tmp/x"), "br", "msg", "owner", "repo", ["SKILL.md"]
            )
        return ok, err, calls

    def test_push_uses_force_with_lease_and_never_bare_force(self):
        ok, _, calls = self._push([0])
        self.assertTrue(ok)
        pushes = [c for c in calls if c[0] == "push"]
        self.assertTrue(all("--force-with-lease" in c for c in pushes))
        self.assertTrue(all("--force" not in c for c in pushes))

    def test_a_fetch_establishes_the_lease_baseline_before_pushing(self):
        _, _, calls = self._push([0])
        verbs = [c[0] for c in calls]
        self.assertLess(verbs.index("fetch"), verbs.index("push"))

    def test_a_refused_lease_is_explained_rather_than_retried_with_force(self):
        ok, err, calls = self._push([1])
        self.assertFalse(ok)
        self.assertIn("moved since this run last saw it", err)
        self.assertTrue(all("--force-with-lease" in c for c in calls if c[0] == "push"))


class TestReadPrBodyFile(unittest.TestCase):
    """The body file's contents get published to a repo this plugin doesn't
    own, so the path is neither trusted nor unbounded."""

    def test_reads_a_file_inside_the_clone(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            body = repo / "body.md"
            body.write_text("Fixes a thing.\n")
            self.assertEqual(pr_execute.read_pr_body_file(str(body), repo), "Fixes a thing.\n")

    def test_a_path_outside_the_clone_and_cwd_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            outside = Path(other) / "id_rsa"
            outside.write_text("PRIVATE KEY\n")
            with self.assertRaises(ValueError) as ctx:
                pr_execute.read_pr_body_file(str(outside), Path(tmp))
        self.assertIn("must live inside", str(ctx.exception))

    def test_a_symlink_escaping_the_clone_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            secret = Path(other) / "secret.txt"
            secret.write_text("secret\n")
            link = Path(tmp) / "body.md"
            try:
                link.symlink_to(secret)
            except OSError:
                self.skipTest("symlinks unavailable")
            with self.assertRaises(ValueError):
                pr_execute.read_pr_body_file(str(link), Path(tmp))

    def test_an_oversized_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            big = repo / "body.md"
            big.write_text("x" * (pr_execute.MAX_PR_BODY_BYTES + 1))
            with self.assertRaises(ValueError) as ctx:
                pr_execute.read_pr_body_file(str(big), repo)
        self.assertIn("maximum", str(ctx.exception))

    def test_a_file_exactly_at_the_cap_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            body = repo / "body.md"
            body.write_text("x" * pr_execute.MAX_PR_BODY_BYTES)
            self.assertEqual(len(pr_execute.read_pr_body_file(str(body), repo)),
                             pr_execute.MAX_PR_BODY_BYTES)

    def test_a_missing_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                pr_execute.read_pr_body_file(str(Path(tmp) / "nope.md"), Path(tmp))

    def test_a_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                pr_execute.read_pr_body_file(tmp, Path(tmp))


if __name__ == "__main__":
    unittest.main()
