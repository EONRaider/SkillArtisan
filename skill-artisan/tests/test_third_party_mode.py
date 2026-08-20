#!/usr/bin/env python3
"""Regression test for audit.py's third-party source mode (issue #4).

Run: python3 -m unittest skill-artisan/tests/test_third_party_mode.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Three checklist items (evals-present, security-scan-marker-current,
lifecycle-classified) verify artifacts only SkillArtisan's own pipeline
produces — its evals schema, its packaging tamper marker, its lifecycle
convention. Across all six audit-pilot corpora (1,418 skills) they FAILed
on effectively every skill not authored through the pipeline, regardless
of quality; RESULTS.md's conclusion was that this undercuts trust in the
real findings reported alongside them. The fix: a per-skill source
resolution (auto/first-party/third-party) that reports those three as a
new N/A status — informative detail, excluded from the pass-rate
denominator — when the skill is third-party. Detection is deliberately
"ANY pipeline artifact present -> first-party": requiring all artifacts
would let a fresh first-party draft silently reclassify as third-party
and skip the exact gate those checks exist to enforce; --source
first-party remains the explicit override for artifact-less drafts.
See benchmark/audit-pilot/RESULTS.md and issue #4.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "skill-artisan" / "scripts"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
THIRD_PARTY_FIXTURE = FIXTURES_DIR / "third-party-fixture"
USER_INVOKED_FIXTURE = FIXTURES_DIR / "user-invoked-fixture"
MODEL_TRIGGERED_FIXTURE = FIXTURES_DIR / "model-triggered-fixture"

sys.path.insert(0, str(SCRIPTS_DIR))

import audit  # noqa: E402

REFRAMED_IDS = ("evals-present", "security-scan-marker-current", "lifecycle-classified")


def find_item(items: list[dict], item_id: str) -> dict:
    for item in items:
        if item["id"] == item_id:
            return item
    raise AssertionError(f"no checklist item with id {item_id!r} found")


class TestSourceDetection(unittest.TestCase):
    def test_artifactless_fixture_detects_third_party(self):
        self.assertEqual(audit.detect_source(THIRD_PARTY_FIXTURE), "third-party")

    def test_pipeline_fixtures_detect_first_party(self):
        # user-invoked-fixture carries a lifecycle line and wrapped evals.json;
        # model-triggered-fixture carries wrapped evals.json.
        self.assertEqual(audit.detect_source(USER_INVOKED_FIXTURE), "first-party")
        self.assertEqual(audit.detect_source(MODEL_TRIGGERED_FIXTURE), "first-party")

    def test_foreign_marker_file_does_not_flip_to_first_party(self):
        """85 skills in the vendored daymade corpus ship a same-named
        .security-scan-passed in a different tool's plain-text format —
        detection must require this pipeline's JSON {"hash": ...} shape,
        while a stale-but-ours marker still counts (skill entered the
        pipeline; the stale hash is a real first-party finding)."""
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "third-party-fixture"
            shutil.copytree(THIRD_PARTY_FIXTURE, skill)
            marker = skill / ".security-scan-passed"
            marker.write_text("Security scan passed\nScanned at: 2026-07-05\nTool: gitleaks\n")
            self.assertEqual(audit.detect_source(skill), "third-party")
            marker.write_text('{"hash": "0000", "algorithm": "sha256"}')
            self.assertEqual(audit.detect_source(skill), "first-party")

    def test_resolve_source_honors_explicit_override(self):
        self.assertEqual(audit.resolve_source(THIRD_PARTY_FIXTURE, "first-party"), "first-party")
        self.assertEqual(audit.resolve_source(USER_INVOKED_FIXTURE, "third-party"), "third-party")
        self.assertEqual(audit.resolve_source(THIRD_PARTY_FIXTURE, "auto"), "third-party")


class TestThirdPartyReframing(unittest.TestCase):
    def test_three_items_are_na_in_third_party_mode(self):
        items = audit.run_checklist(THIRD_PARTY_FIXTURE, source="third-party")
        for item_id in REFRAMED_IDS:
            item = find_item(items, item_id)
            self.assertEqual(item["status"], "N/A", f"{item_id} should be N/A for a third-party skill")
            self.assertTrue(item["detail"], f"{item_id} N/A detail must still explain what was observed")

    def test_explicit_first_party_restores_the_gate(self):
        """The exact trap the design guards: a draft with zero artifacts must
        still be holdable to the full checklist via --source first-party."""
        items = audit.run_checklist(THIRD_PARTY_FIXTURE, source="first-party")
        for item_id in REFRAMED_IDS:
            self.assertEqual(find_item(items, item_id)["status"], "FAIL",
                             f"{item_id} must FAIL when first-party is explicit")

    def test_first_party_fixture_unaffected_by_default_auto(self):
        report = audit.audit_skill(USER_INVOKED_FIXTURE, None, None)
        self.assertEqual(report["source"], "first-party")
        for item_id in ("evals-present", "lifecycle-classified"):
            self.assertNotEqual(find_item(report["items"], item_id)["status"], "N/A")

    def test_other_checks_unaffected_by_source(self):
        third = audit.run_checklist(THIRD_PARTY_FIXTURE, source="third-party")
        first = audit.run_checklist(THIRD_PARTY_FIXTURE, source="first-party")
        for item_id in ("frontmatter-valid", "description-pushy-imperative", "body-size-limits",
                        "security-pattern-checks", "no-human-docs-in-skill-dir"):
            self.assertEqual(find_item(third, item_id)["status"], find_item(first, item_id)["status"],
                             f"{item_id} must not vary with source")


class TestSummaryExcludesNA(unittest.TestCase):
    def test_na_not_in_pass_rate_denominator(self):
        items = [{"id": "a", "status": "PASS", "detail": ""},
                 {"id": "b", "status": "N/A", "detail": ""},
                 {"id": "c", "status": "FAIL", "detail": ""}]
        s = audit.summarize(items)
        self.assertEqual(s["total_scored"], 2)
        self.assertEqual(s["not_applicable"], 1)
        self.assertEqual(s["pass_rate"], 0.5)

    def test_audit_skill_records_resolved_source(self):
        report = audit.audit_skill(THIRD_PARTY_FIXTURE, None, None)
        self.assertEqual(report["source"], "third-party")
        self.assertEqual(report["summary"]["not_applicable"], 3)


if __name__ == "__main__":
    unittest.main()
