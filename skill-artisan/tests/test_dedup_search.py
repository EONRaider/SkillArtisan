#!/usr/bin/env python3
"""Tests for dedup_search.py — the per-fact (--fact) mode, plus the
whole-skill (--query) mode's behavior that mode must not change.

Run: python3 -m unittest skill-artisan/tests/test_dedup_search.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Motivated by a real drafting miss downstream: a new skill's first draft
restated a CI-job-to-local-command mapping a sibling skill in the same
skills directory already owned. The whole-skill gate (--query) had rightly
said "create new" — the skills did different jobs — and structurally
couldn't have caught it anyway, since it scores frontmatter descriptions
only and the mapping lived in the sibling's body. An independent
adversarial review found the duplicate later. The fixture below rebuilds
that shape: a sibling whose *description* says nothing about CI, with the
mapping table in its body.
"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))

import dedup_search  # noqa: E402

SIBLING_WITH_CI_TABLE = """\
---
name: preparing-pull-requests
description: Prepare a branch for review — title, description, and the checks a reviewer expects to see green.
---

# Preparing Pull Requests

Write the PR body before pushing.

## Reproducing CI locally

| CI job | Local command |
|---|---|
| lint | `ruff check .` |
| test | `python3 -m unittest discover -s tests` |

## Titles

Keep titles under 72 characters.
"""

UNRELATED_SIBLING = """\
---
name: brewing-coffee
description: Brew pour-over coffee to a fixed ratio.
---

Use a 1:16 ratio.
"""


def write_skill(skills_dir: Path, name: str, content: str) -> Path:
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(content)
    return skill_dir


def run_main(argv: list) -> tuple:
    """Run dedup_search.main in-process; returns (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with redirect_stdout(out), redirect_stderr(err):
        try:
            dedup_search.main(argv)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue(), err.getvalue()


class TestSplitBlocks(unittest.TestCase):
    def test_table_stays_one_block_under_its_heading(self):
        body = "Intro.\n\n## CI\n\n| a | b |\n|---|---|\n| x | y |\n\nAfter.\n"
        blocks = dedup_search.split_blocks(body)
        self.assertEqual([b["text"] for b in blocks], ["Intro.", "| a | b |\n|---|---|\n| x | y |", "After."])
        self.assertEqual([b["heading"] for b in blocks], ["", "CI", "CI"])

    def test_fenced_code_block_is_not_split_on_inner_blank_lines(self):
        body = "```bash\nruff check .\n\npytest\n```\nTrailing prose.\n"
        blocks = dedup_search.split_blocks(body)
        self.assertEqual(len(blocks), 1)
        self.assertIn("pytest", blocks[0]["text"])
        self.assertIn("Trailing prose.", blocks[0]["text"])

    def test_fence_closes_only_on_its_own_marker(self):
        body = "```\n~~~\n\n## not a heading\n```\n\nAfter.\n"
        blocks = dedup_search.split_blocks(body)
        self.assertEqual(len(blocks), 2)
        self.assertIn("## not a heading", blocks[0]["text"])
        self.assertEqual(blocks[1]["heading"], "")

    def test_heading_marker_inside_fence_is_not_a_heading(self):
        body = "## Real\n\n```\n# comment, not a heading\n```\n"
        blocks = dedup_search.split_blocks(body)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["heading"], "Real")

    def test_line_numbers_are_offset_into_the_real_file(self):
        blocks = dedup_search.split_blocks("\nFirst.\n\nSecond.\n", first_line=5)
        self.assertEqual([b["line"] for b in blocks], [6, 8])


class TestCoverage(unittest.TestCase):
    def test_coverage_is_asymmetric(self):
        fact = {"lint", "ruff"}
        block = {"lint", "ruff", "test", "unittest", "job", "local", "command"}
        self.assertEqual(dedup_search.coverage(fact, block), 1.0)
        self.assertLess(dedup_search.jaccard(fact, block), 0.5)

    def test_empty_fact_scores_zero(self):
        self.assertEqual(dedup_search.coverage(set(), {"anything"}), 0.0)


class TestSearchFacts(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.skills = Path(self._tmp.name) / "skills"
        self.sibling = write_skill(self.skills, "preparing-pull-requests", SIBLING_WITH_CI_TABLE)
        write_skill(self.skills, "brewing-coffee", UNRELATED_SIBLING)
        self.draft = write_skill(self.skills, "fixing-ci-failures", (
            "---\nname: fixing-ci-failures\ndescription: Diagnose red CI.\n---\n\n"
            "| CI job | Local command |\n|---|---|\n| lint | `ruff check .` |\n"))

    def tearDown(self):
        self._tmp.cleanup()

    def test_finds_body_fact_the_whole_skill_mode_cannot_see(self):
        fact = "CI lint job maps to local command ruff check"
        whole_skill = dedup_search.search(fact, [self.skills], dedup_search.DEFAULT_MIN_SCORE["query"],
                                          exclude=[self.draft])
        # At most a noise-level hit on a shared generic word ("check"), tiered
        # "low overlap" — nothing that would send a drafter to read the body.
        for candidate in whole_skill:
            if candidate["name"] == "preparing-pull-requests":
                self.assertEqual(candidate["suggested_tier"], "low overlap")

        hits = dedup_search.search_facts(fact, [self.skills], dedup_search.DEFAULT_MIN_SCORE["fact"],
                                         exclude=[self.draft])
        self.assertTrue(hits, "fact mode found nothing")
        top = hits[0]
        self.assertEqual(top["name"], "preparing-pull-requests")
        self.assertEqual(top["heading"], "Reproducing CI locally")
        self.assertEqual(top["path"], str(self.sibling / "SKILL.md"))
        lines = (self.sibling / "SKILL.md").read_text().split("\n")
        self.assertEqual(lines[top["line"] - 1], "| CI job | Local command |")
        self.assertIn("ruff", top["matched_terms"])

    def test_excluded_draft_never_matches_itself(self):
        hits = dedup_search.search_facts("CI lint job ruff check", [self.skills], 0.0,
                                         exclude=[self.draft], limit=None)
        self.assertNotIn("fixing-ci-failures", {h["name"] for h in hits})

    def test_unrelated_fact_yields_no_hits_at_default_floor(self):
        hits = dedup_search.search_facts("rotate kubernetes service account tokens", [self.skills],
                                         dedup_search.DEFAULT_MIN_SCORE["fact"], exclude=[self.draft])
        self.assertEqual(hits, [])

    def test_limit_caps_results_and_none_disables_the_cap(self):
        everything = dedup_search.search_facts("lint", [self.skills], 0.0, limit=None)
        self.assertGreater(len(everything), 1)
        self.assertEqual(len(dedup_search.search_facts("lint", [self.skills], 0.0, limit=1)), 1)

    def test_malformed_sibling_is_skipped_not_fatal(self):
        bad = self.skills / "broken"
        bad.mkdir()
        (bad / "SKILL.md").write_text("no frontmatter here, CI lint job ruff check\n")
        hits = dedup_search.search_facts("CI lint job ruff check", [self.skills], 0.0, limit=None)
        self.assertNotIn(str(bad / "SKILL.md"), {h["path"] for h in hits})


class TestCli(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.skills = Path(self._tmp.name) / "skills"
        write_skill(self.skills, "preparing-pull-requests", SIBLING_WITH_CI_TABLE)
        # The draft need not exist yet: --siblings-of only needs its parent.
        self.draft = self.skills / "fixing-ci-failures"

    def tearDown(self):
        self._tmp.cleanup()

    def test_fact_json_output_points_at_the_sibling(self):
        code, out, _ = run_main(["--fact", "CI lint job local command ruff check",
                                 "--siblings-of", str(self.draft), "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["fact"], "CI lint job local command ruff check")
        self.assertEqual(payload["hits"][0]["name"], "preparing-pull-requests")

    def test_fact_text_report_names_file_and_line(self):
        code, out, _ = run_main(["--fact", "CI lint job local command ruff check",
                                 "--siblings-of", str(self.draft)])
        self.assertEqual(code, 0)
        self.assertIn("preparing-pull-requests § Reproducing CI locally", out)
        self.assertIn("SKILL.md:", out)

    def test_query_and_fact_are_mutually_exclusive(self):
        code, _, err = run_main(["--query", "x", "--fact", "y", "--siblings-of", str(self.draft)])
        self.assertEqual(code, 2)
        self.assertIn("not allowed with", err)

    def test_one_of_query_or_fact_is_required(self):
        code, _, _ = run_main(["--siblings-of", str(self.draft)])
        self.assertEqual(code, 2)

    def test_negative_limit_is_rejected(self):
        code, _, err = run_main(["--fact", "x", "--siblings-of", str(self.draft), "--limit", "-1"])
        self.assertEqual(code, 2)
        self.assertIn("--limit", err)

    def test_missing_sibling_directory_exits_2(self):
        code, _, err = run_main(["--fact", "x", "--siblings-of", str(Path(self._tmp.name) / "nope" / "draft")])
        self.assertEqual(code, 2)
        self.assertIn("No search paths exist", err)

    def test_query_mode_still_scores_descriptions(self):
        code, out, _ = run_main(["--query", "prepare branch review title description checks green",
                                 "--siblings-of", str(self.draft), "--json"])
        self.assertEqual(code, 0)
        candidates = json.loads(out)["candidates"]
        self.assertEqual(candidates[0]["name"], "preparing-pull-requests")
        self.assertIn("lexical_overlap_score", candidates[0])


if __name__ == "__main__":
    unittest.main()
