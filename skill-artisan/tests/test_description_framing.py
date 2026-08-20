#!/usr/bin/env python3
"""Regression test for description-pushy-imperative's trigger-framing match (issue #6).

Run: python3 -m unittest skill-artisan/tests/test_description_framing.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

The check originally recognized only the literal substring "use when".
Five audit-pilot corpora showed equivalent trigger framing phrased
differently — "use whenever" / "use for X, Y, Z" / "use during authorized
red-team..." / "use this skill when..." — at incidence rates from 8.6%
(alirezarezvani, 30/349) to 82% (mukul975, 668/817), with daymade ~40%
sampled and glebis 55% in between. All of those WARNed despite carrying
exactly the authorial intent the check looks for. This test pins the
broadened TRIGGER_FRAMING_RE in both directions: the corpus-verified
variants PASS at real length, while a description with no trigger clause
at all — or a pushy "you MUST use this" that never says *when* — still
WARNs. It also guards the message fix: the old OR-phrased detail couldn't
tell an author whether framing or length was the problem (obra's
test-driven-development had "Use when" but was 72 chars).
See benchmark/audit-pilot/RESULTS.md and issue #6.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "skill-artisan" / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

import audit  # noqa: E402


def quality_for(description: str) -> dict:
    return audit.check_description_quality({"name": "x", "description": description})


def padded(prefix: str, length: int = 120) -> str:
    return (prefix + " covering competitor research, positioning analysis, and report generation tasks. ").ljust(length, "x")


class TestVariantFramingPasses(unittest.TestCase):
    def test_literal_use_when_still_passes(self):
        self.assertEqual(quality_for(padded("Analyzes competitors. Use when the user asks for market analysis"))["status"], "PASS")

    def test_use_whenever_passes(self):
        self.assertEqual(quality_for(padded("Analyzes competitors. Use whenever the user asks for market analysis"))["status"], "PASS")

    def test_use_for_passes(self):
        self.assertEqual(quality_for(padded("Threat modeling helper. Use for structured analysis of attack surfaces"))["status"], "PASS")

    def test_use_during_passes(self):
        self.assertEqual(quality_for(padded("Red-team playbook. Use during authorized red-team engagements"))["status"], "PASS")

    def test_use_this_skill_when_passes(self):
        self.assertEqual(quality_for(padded("Report builder. Use this skill when the user wants a competitor report"))["status"], "PASS")

    def test_use_if_passes(self):
        self.assertEqual(quality_for(padded("Migration helper. Use if the user mentions upgrading between versions"))["status"], "PASS")


class TestWeakDescriptionsStillWarn(unittest.TestCase):
    def test_no_trigger_clause_warns(self):
        item = quality_for(padded("A comprehensive helper for competitor analysis and reporting workflows"))
        self.assertEqual(item["status"], "WARN")
        self.assertIn("missing trigger framing", item["detail"])

    def test_pushy_must_use_without_when_warns(self):
        """obra-style imperative with no trigger clause: pushy, but never says
        *when* — must not slip through the broadened match."""
        item = quality_for(padded("You MUST use this before writing any implementation code in this repo"))
        self.assertEqual(item["status"], "WARN")
        self.assertIn("missing trigger framing", item["detail"])


class TestMessageNamesTheActualProblem(unittest.TestCase):
    def test_framed_but_short_reports_length_only(self):
        """obra's test-driven-development case: 'Use when' present, 72 chars."""
        desc = "Use when writing tests, before writing implementation code in a repo"
        item = quality_for(desc)
        self.assertEqual(item["status"], "WARN")
        self.assertIn("short", item["detail"])
        self.assertNotIn("missing trigger framing", item["detail"])

    def test_unframed_and_long_reports_framing_only(self):
        item = quality_for(padded("A comprehensive helper for competitor analysis and reporting workflows"))
        self.assertNotIn("short", item["detail"])

    def test_unframed_and_short_reports_both(self):
        desc = "Helps a lot with analyzing competitors and writing things down"
        item = quality_for(desc)
        self.assertEqual(item["status"], "WARN")
        self.assertIn("missing trigger framing", item["detail"])
        self.assertIn("short", item["detail"])


if __name__ == "__main__":
    unittest.main()
