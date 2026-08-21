#!/usr/bin/env python3
"""Regression test for description-pushy-imperative's non-Latin-script handling (issue #10).

Run: python3 -m unittest skill-artisan/tests/test_description_cjk_manual.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

TRIGGER_FRAMING_RE and the 40/100-char length floors are calibrated for
English text density. Phase 11 (nomadamas/k-skill, Korean) and Phase 16
(chaterm/terminal-skills, Chinese) both confirmed this two independent
ways on two independent corpora, verified against real descriptions:
Korean sentences with genuine trigger-framing content structurally can't
match an English "use when" regex (77% FAIL/WARN), and short CJK
descriptions carrying real semantic content get FAILed by a character-count
floor built for English word length (98%). Rather than guess at
per-language regex/thresholds with no linguistic verification, a
predominantly non-Latin-script description now gets MANUAL — an honest
"cannot verify" — instead of a confident, structurally-unreliable FAIL/WARN.
The 30% non-Latin-letter-fraction threshold was picked empirically: skills
whose description is actually written in English (even in a Korean- or
Chinese-authored repo) measure at 0% and are correctly unaffected by this
change; genuine CJK-script descriptions measure at a 47-67% median across
both corpora. See benchmark/audit-pilot/RESULTS.md's Phase 11/16 sections
and issue #10.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))

import audit  # noqa: E402


def quality_for(description: str) -> dict:
    return audit.check_description_quality({"name": "x", "description": description})


class TestRealCJKDescriptionsGetManual(unittest.TestCase):
    """Real strings pulled from the two audited corpora, not synthetic guesses."""

    def test_korean_description_with_no_english_framing_is_manual(self):
        # nomadamas/k-skill's assembly-bill-vote-search — a complete, purpose-
        # stating Korean sentence the English regex structurally cannot match.
        desc = ("열린국회정보 Open API를 k-skill-proxy 경유로 호출해 의안 검색·상세와 "
                "국회의원 본회의 표결정보를 조회한다. 조회 전용.")
        item = quality_for(desc)
        self.assertEqual(item["status"], "MANUAL")
        self.assertIn("non-Latin-script", item["detail"])

    def test_short_but_information_dense_korean_description_is_manual(self):
        # k-skill's daangn-cars-search, 61 chars — RESULTS.md verified this is
        # a complete, information-dense sentence, not a genuinely thin one;
        # the old 100-char floor would still WARN it as "short".
        desc = "당근중고차 공개 웹 데이터로 차량을 검색하고, 돌쇠에서는 공식 계정 표면에서 문의·찜·거래 준비까지 진행한다"
        item = quality_for(desc)
        self.assertEqual(item["status"], "MANUAL")

    def test_terse_chinese_description_is_manual_not_fail(self):
        # chaterm/terminal-skills' firewall skill — 5 characters, would FAIL
        # the old 40-char floor outright despite carrying real content.
        item = quality_for("防火墙配置")
        self.assertEqual(item["status"], "MANUAL")
        self.assertNotEqual(item["status"], "FAIL")


class TestEnglishDescriptionsInNonEnglishReposAreUnaffected(unittest.TestCase):
    def test_fully_english_description_from_korean_repo_scores_normally(self):
        # k-skill's building-register skill: written entirely in English even
        # though the repo and topic are Korean. 0% non-Latin letters — must
        # still go through the normal English-calibrated check, not MANUAL.
        desc = ("Use when the user asks to look up a Korean building-register "
                "title record by address, confirming ownership and encumbrances.")
        item = quality_for(desc)
        self.assertNotEqual(item["status"], "MANUAL")
        self.assertEqual(item["status"], "PASS")

    def test_pure_english_description_never_flagged_non_latin(self):
        desc = "Analyzes competitors. Use when the user asks for market analysis of a named company."
        item = quality_for(desc)
        self.assertNotEqual(item["status"], "MANUAL")


class TestThresholdBoundary(unittest.TestCase):
    def test_mostly_latin_with_a_few_non_latin_words_not_flagged(self):
        """A handful of non-Latin proper nouns inside an otherwise-English
        description must not cross the 30% fraction and misfire MANUAL."""
        desc = "Search and summarize 한국 news articles for the user's requested topic and date range, in English."
        item = quality_for(desc)
        self.assertLess(audit._non_latin_letter_fraction(desc), audit.NON_LATIN_SCRIPT_THRESHOLD)
        self.assertNotEqual(item["status"], "MANUAL")

    def test_non_latin_fraction_helper_on_pure_ascii(self):
        self.assertEqual(audit._non_latin_letter_fraction("plain english text, no accents"), 0.0)

    def test_non_latin_fraction_helper_on_pure_hangul(self):
        self.assertEqual(audit._non_latin_letter_fraction("한국어"), 1.0)


class TestManualExcludedFromPassRateAndRebuildGate(unittest.TestCase):
    def test_manual_status_excluded_from_pass_rate_denominator(self):
        items = [
            {"id": "description-pushy-imperative", "status": "MANUAL", "detail": ""},
            {"id": "a", "status": "PASS", "detail": ""},
            {"id": "b", "status": "FAIL", "detail": ""},
        ]
        s = audit.summarize(items)
        self.assertEqual(s["total_scored"], 2)
        self.assertEqual(s["manual"], 1)

    def test_manual_description_status_does_not_trigger_rebuild_via_frontmatter_combo(self):
        """decide_upgrade_vs_rebuild only special-cases an explicit FAIL on
        description-pushy-imperative combined with a frontmatter-valid FAIL;
        MANUAL must not accidentally satisfy that condition."""
        items = [
            {"id": "description-pushy-imperative", "status": "MANUAL", "detail": ""},
            {"id": "frontmatter-valid", "status": "FAIL", "detail": ""},
            {"id": "body-size-limits", "status": "PASS", "detail": ""},
        ]
        decision = audit.decide_upgrade_vs_rebuild(items, None, None)
        self.assertEqual(decision["decision"], "upgrade-in-place")


if __name__ == "__main__":
    unittest.main()
