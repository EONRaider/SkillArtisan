#!/usr/bin/env python3
"""Regression test for has_lifecycle_markers' metadata-field false positive.

Run: python3 -m unittest skill-artisan/tests/test_lifecycle_metadata_false_positive.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

The `metadata` frontmatter field is reconstructed as one flat string by
_common.py's parser (no real YAML nesting), so `"lifecycle" in
metadata.lower()` matched any unrelated tag/category containing that
substring. Found live on real third-party content during audit-pilot
Phase 23: `terminalskills/skills`' `mlflow` skill (tagged `ml-lifecycle`,
about MLflow's ML-lifecycle management, nothing to do with this pipeline's
skill-lifecycle classification) and `sequenzy-email-marketing` (tagged
`lifecycle-email`, about email-campaign lifecycles) both misdetected as
first-party, drawing bogus evals-present/security-scan-marker-current FAILs.
Fixed with the same co-occurrence discipline the body-text check already
uses: a real lifecycle classification names its category
(references/lifecycle.md: capability-uplift, encoded-preference) or pairs
with "timelessness", so the metadata path now requires "lifecycle" alongside
one of those, not the bare substring alone.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))

import audit  # noqa: E402


class TestRealFalsePositivesFixed(unittest.TestCase):
    """Real frontmatter blocks pulled from the two misdetected corpus skills,
    not synthetic guesses."""

    def test_mlflow_ml_lifecycle_tag_no_longer_flips(self):
        frontmatter = {
            "metadata": (
                "\n  author: terminal-skills\n  version: 1.0.0\n  category: data-ai\n"
                "  tags:\n    - experiment-tracking\n    - model-registry\n"
                "    - ml-lifecycle\n    - deployment\n    - pipelines\n"
            )
        }
        self.assertFalse(audit.has_lifecycle_markers("", frontmatter))

    def test_sequenzy_lifecycle_email_tag_no_longer_flips(self):
        frontmatter = {
            "metadata": (
                '\n  author: Sequenzy\n  version: "1.0.0"\n  category: business\n'
                '  tags: ["email-marketing", "saas", "automation", "campaigns", "lifecycle-email"]\n'
            )
        }
        self.assertFalse(audit.has_lifecycle_markers("", frontmatter))


class TestGenuineMetadataMarkerStillDetected(unittest.TestCase):
    def test_metadata_with_timelessness_still_detected(self):
        frontmatter = {"metadata": "lifecycle: encoded-preference, timelessness 9/10"}
        self.assertTrue(audit.has_lifecycle_markers("", frontmatter))

    def test_metadata_with_capability_uplift_category_still_detected(self):
        frontmatter = {"metadata": "lifecycle classification: capability-uplift"}
        self.assertTrue(audit.has_lifecycle_markers("", frontmatter))

    def test_metadata_with_encoded_preference_category_still_detected(self):
        frontmatter = {"metadata": "lifecycle: encoded-preference"}
        self.assertTrue(audit.has_lifecycle_markers("", frontmatter))


class TestBodyTextPathUnaffected(unittest.TestCase):
    def test_body_lifecycle_and_timelessness_still_detected(self):
        body = "Lifecycle: encoded-preference, timelessness 10/10, last verified against claude-sonnet-5."
        self.assertTrue(audit.has_lifecycle_markers(body, {}))

    def test_body_lifecycle_alone_without_timelessness_not_detected(self):
        """Same discipline that already governed the body-text path — this
        test only pins existing behavior, not the fix."""
        body = "This skill manages the ML lifecycle for experiment tracking."
        self.assertFalse(audit.has_lifecycle_markers(body, {}))


if __name__ == "__main__":
    unittest.main()
