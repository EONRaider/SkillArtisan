#!/usr/bin/env python3
"""Regression test for check_references_depth_and_toc's TOC-heading matching.

Run: python3 -m unittest skill-artisan/tests/test_audit_references_toc.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Found via the daymade/claude-code-skills real-world audit pilot
(2026-08-20, see benchmark/audit-pilot/RESULTS.md): the check only matched
the literal phrase "table of contents", so a file with a real, working
"## Contents" heading and anchor-link list still got flagged as missing a
TOC. This was the single highest-impact false positive found across both
real-world pilots — 59 of 92 daymade skills were flagged on this ground
alone, most of them with a working TOC just spelled differently. Fixed by
also accepting "## Contents", "## TOC", and "## Index" headings. This test
guards both directions: a real "## Contents"-style TOC is no longer
flagged, and a reference file with no TOC at all still is.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "skill-artisan" / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import audit  # noqa: E402


def toc_result_for(ref_content: str) -> dict:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        skill_path = Path(tmp)
        ref_dir = skill_path / "references"
        ref_dir.mkdir()
        (ref_dir / "long.md").write_text(ref_content)
        items = audit.check_references_depth_and_toc(skill_path)
        return next(i for i in items if i["id"] == "references-toc-for-long-files")


def long_body(heading: str | None) -> str:
    lines = []
    if heading:
        lines.append(heading)
    lines += [f"line {i}" for i in range(150)]
    return "\n".join(lines)


class TestReferencesTocDetection(unittest.TestCase):
    def test_contents_heading_counts_as_a_real_toc(self):
        result = toc_result_for(long_body("## Contents\n- [a](#a)\n- [b](#b)"))
        self.assertEqual(result["status"], "PASS")

    def test_index_heading_counts_as_a_real_toc(self):
        result = toc_result_for(long_body("## Index"))
        self.assertEqual(result["status"], "PASS")

    def test_literal_table_of_contents_phrase_still_works(self):
        result = toc_result_for(long_body("## Table of Contents"))
        self.assertEqual(result["status"], "PASS")

    def test_no_toc_heading_at_all_is_still_a_real_fail(self):
        result = toc_result_for(long_body("## General Principles"))
        self.assertEqual(result["status"], "FAIL")

    def test_short_file_never_needs_a_toc(self):
        result = toc_result_for("## General Principles\nshort file, only a few lines.")
        self.assertEqual(result["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
