#!/usr/bin/env python3
"""Regression test for the four judgment-lens MANUAL_ONLY_ITEMS entries and
their backing reference/audit-judgment-lenses.md file — ported from a
separate personal skill's audit process (skill-audit), which had no
equivalent anywhere in this project's audit.py before.

Run: python3 -m unittest skill-artisan/tests/test_audit_judgment_lenses.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import CREATING_SKILLS_DIR, SCRIPTS_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))

import audit  # noqa: E402

REFERENCE_FILE = CREATING_SKILLS_DIR / "references" / "audit-judgment-lenses.md"

NEW_JUDGMENT_ITEM_IDS = (
    "prose-should-be-script",
    "prose-should-be-hook-or-disallowed-tools",
    "condensed-version-proposed",
)


def manual_item_ids() -> set[str]:
    return {item["id"] for item in audit.MANUAL_ONLY_ITEMS}


class TestJudgmentLensItemsRegistered(unittest.TestCase):
    def test_three_new_items_present(self):
        ids = manual_item_ids()
        for item_id in NEW_JUDGMENT_ITEM_IDS:
            self.assertIn(item_id, ids)

    def test_fork_appropriateness_item_upgraded_not_duplicated(self):
        """The existing inline-vs-fork-decision-correct item gets its detail
        upgraded to point at the new reference file, not duplicated into a
        second, near-identical MANUAL item."""
        ids = [item["id"] for item in audit.MANUAL_ONLY_ITEMS]
        self.assertEqual(ids.count("inline-vs-fork-decision-correct"), 1)
        item = next(i for i in audit.MANUAL_ONLY_ITEMS if i["id"] == "inline-vs-fork-decision-correct")
        self.assertIn("audit-judgment-lenses.md", item["detail"])

    def test_all_four_items_appear_in_a_real_checklist_run(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            skill_path = Path(tmp)
            (skill_path / "SKILL.md").write_text(
                "---\nname: a-test-skill\ndescription: a test skill\n---\nBody.\n"
            )
            items = audit.run_checklist(skill_path)
            ids = {item["id"] for item in items}
            self.assertIn("inline-vs-fork-decision-correct", ids)
            for item_id in NEW_JUDGMENT_ITEM_IDS:
                self.assertIn(item_id, ids)


class TestReferenceFileBacksEveryDetailAnchor(unittest.TestCase):
    """Every references/audit-judgment-lenses.md#<anchor> cited in
    MANUAL_ONLY_ITEMS' detail text must resolve to a real ## heading in that
    file — a dangling anchor is exactly the kind of thing check_path_references
    can't catch (frontmatter-only), so this pins it directly."""

    def test_reference_file_exists(self):
        self.assertTrue(REFERENCE_FILE.is_file())

    def test_every_cited_anchor_has_a_matching_heading(self):
        content = REFERENCE_FILE.read_text()
        headings = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)
        slugs = {h.lower().replace(" ", "-") for h in headings}
        cited_anchors = set()
        for item in audit.MANUAL_ONLY_ITEMS:
            for m in re.finditer(r"audit-judgment-lenses\.md#([a-z0-9-]+)", item["detail"]):
                cited_anchors.add(m.group(1))
        self.assertTrue(cited_anchors, "expected at least one cited anchor in MANUAL_ONLY_ITEMS")
        for anchor in cited_anchors:
            self.assertIn(anchor, slugs, f"references/audit-judgment-lenses.md has no '## {anchor}'-shaped heading")

    def test_reference_file_has_no_dangling_claude_skill_dir_references(self):
        """Self-validation guard: this file must never accidentally trip
        validate.py's check_claude_skill_dir_refs by describing the
        ${CLAUDE_SKILL_DIR} convention with a literal example path."""
        self.assertNotIn("CLAUDE_SKILL_DIR", REFERENCE_FILE.read_text())


if __name__ == "__main__":
    unittest.main()
