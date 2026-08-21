#!/usr/bin/env python3
"""Regression test for aggregate_findings.py's --source pass-through (issue #11).

Run: python3 -m unittest skill-artisan/tests/test_aggregate_findings_source.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Fourteen real skills across the audit pilot (Phases 16-29, issue #11)
independently converged on this pipeline's own evals.json shape closely
enough that audit.py's detect_source() misclassified them as first-party,
drawing bogus evals-present/security-scan-marker-current/lifecycle-classified
FAILs. Rather than weaken detect_source()'s auto-detection (which would
reopen issue #4's unfalsifiability trap for fresh first-party drafts),
aggregate_findings.py now accepts --source to force a fixed resolution for
every skill in a bulk-audit run -- the right tool for auditing a *known*
third-party corpus, where per-skill auto-detection was never the right
question to begin with. See benchmark/audit-pilot/RESULTS.md's Phase 16-29
sections and issue #11 for the full evidence trail.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
THIRD_PARTY_FIXTURE = FIXTURES_DIR / "third-party-fixture"

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark" / "audit-pilot"))

import aggregate_findings  # noqa: E402


def _find_item(items: list[dict], item_id: str) -> dict:
    for item in items:
        if item["id"] == item_id:
            return item
    raise AssertionError(f"no checklist item with id {item_id!r} found")


class TestSourcePassThrough(unittest.TestCase):
    """A skill carrying the real fluxcd/petekp/bmad-labs/atlassian-shaped
    evals.json (full `expectations` field match, the sub-case with zero
    discriminator signal available to detect_source()) -- confirms the CLI
    flag actually reaches audit.audit_skill(), not just that the flag parses."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.skill = Path(self.tmp) / "converged-schema-skill"
        shutil.copytree(THIRD_PARTY_FIXTURE, self.skill)
        evals_dir = self.skill / "evals"
        evals_dir.mkdir(exist_ok=True)
        (evals_dir / "evals.json").write_text(json.dumps({
            "skill_name": "converged-schema-skill",
            "evals": [{
                "id": 1, "prompt": "p", "expected_output": "e", "files": [],
                "expectations": ["a real, independently-authored expectations array"],
            }],
        }))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_default_auto_source_misdetects_as_first_party(self):
        """Pins the known false positive so this test fails loudly if
        detect_source() is ever changed in a way that accidentally fixes
        (or worsens) this — the point of this test is the --source
        override, not this misdetection itself. security-scan-marker-current
        is the item that demonstrates real damage: a bare evals-present WARN
        stays scored under third-party mode too (a present-but-thin evals
        file is real content regardless of source), but a missing
        .security-scan-passed marker is unconditionally reframed only when
        source correctly resolves to third-party."""
        reports = aggregate_findings.audit_source("test", self.skill, None, None)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["source"], "first-party")
        self.assertEqual(_find_item(reports[0]["items"], "security-scan-marker-current")["status"], "FAIL")

    def test_source_third_party_flag_overrides_the_misdetection(self):
        reports = aggregate_findings.audit_source("test", self.skill, None, None, source="third-party")
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["source"], "third-party")
        self.assertEqual(_find_item(reports[0]["items"], "security-scan-marker-current")["status"], "N/A")

    def test_source_first_party_flag_is_also_respected(self):
        """Explicit first-party must still work even on a skill with no
        artifacts at all -- issue #4's original anti-unfalsifiability
        guarantee, unaffected by this change."""
        bare = Path(self.tmp) / "bare-fixture"
        shutil.copytree(THIRD_PARTY_FIXTURE, bare)
        reports = aggregate_findings.audit_source("test", bare, None, None, source="first-party")
        self.assertEqual(reports[0]["source"], "first-party")
        self.assertEqual(_find_item(reports[0]["items"], "security-scan-marker-current")["status"], "FAIL")

    def test_cli_parses_source_choices(self):
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument("--source", choices=["auto", "first-party", "third-party"], default="auto")
        self.assertEqual(p.parse_args(["--source", "third-party"]).source, "third-party")
        self.assertEqual(p.parse_args([]).source, "auto")
        with self.assertRaises(SystemExit):
            p.parse_args(["--source", "bogus"])


if __name__ == "__main__":
    unittest.main()
