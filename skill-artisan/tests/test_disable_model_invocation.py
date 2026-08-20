#!/usr/bin/env python3
"""Regression test for the disable-model-invocation authoring branch.

Run: python3 -m unittest skill-artisan/tests/test_disable_model_invocation.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

`disable-model-invocation: true` skills are user-invoked only (e.g. via a
slash command) and never auto-triggered from a description match. The
trigger-accuracy machinery in creating-skills (pushy-description guidance,
the description optimizer, audit.py's description-optimizer-run manual
item) exists to tune the model's auto-trigger decision, so none of it
applies to such skills. This test guards two things: the audit checklist
actually treats the two fixture skills below differently (user-invoked
fixture doesn't get flagged for trigger machinery it can't use; the
model-triggered control fixture still does), and the doc edits that
describe this branch are actually present in the source files.
"""
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "skill-artisan" / "scripts"
CREATING_SKILLS_DIR = REPO_ROOT / "skill-artisan" / "creating-skills"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
USER_INVOKED_FIXTURE = FIXTURES_DIR / "user-invoked-fixture"
MODEL_TRIGGERED_FIXTURE = FIXTURES_DIR / "model-triggered-fixture"

sys.path.insert(0, str(SCRIPTS_DIR))

import audit  # noqa: E402
import validate  # noqa: E402


def find_item(items: list[dict], item_id: str) -> dict:
    for item in items:
        if item["id"] == item_id:
            return item
    raise AssertionError(f"no checklist item with id {item_id!r} found")


class TestFieldClassification(unittest.TestCase):
    """validate.py still classifies disable-model-invocation as a Claude
    Code-only informational field, not an error — no regression from the
    doc/audit changes, which don't touch validate.py at all."""

    def test_disable_model_invocation_is_claude_code_only(self):
        self.assertIn("disable-model-invocation", validate.CLAUDE_CODE_ONLY_FIELDS)

    def test_classify_extended_fields_treats_it_as_informational(self):
        frontmatter = {"name": "x", "description": "y", "disable-model-invocation": "true"}
        claude_only, _known_third_party, unknown = validate.classify_extended_fields(frontmatter)
        self.assertIn("disable-model-invocation", claude_only)
        self.assertNotIn("disable-model-invocation", unknown)


class TestAuditChecklistBranch(unittest.TestCase):
    """audit.py's run_checklist must resolve description-optimizer-run
    differently for the two fixtures — conditional on the field, not a
    blanket removal."""

    def test_user_invoked_fixture_is_not_flagged_manual(self):
        items = audit.run_checklist(USER_INVOKED_FIXTURE)
        item = find_item(items, "description-optimizer-run")
        self.assertNotEqual(item["status"], "MANUAL",
                             "disable-model-invocation: true skill should not carry an unresolved "
                             "description-optimizer-run MANUAL item")
        self.assertIn("not applicable", item["detail"])

    def test_model_triggered_fixture_still_flagged_manual(self):
        items = audit.run_checklist(MODEL_TRIGGERED_FIXTURE)
        item = find_item(items, "description-optimizer-run")
        self.assertEqual(item["status"], "MANUAL",
                          "a normal, model-triggered skill should still get the manual "
                          "description-optimizer-run reminder")

    def test_user_invoked_fixture_description_quality_not_penalized_for_missing_use_when(self):
        items = audit.run_checklist(USER_INVOKED_FIXTURE)
        item = find_item(items, "description-pushy-imperative")
        self.assertEqual(item["status"], "PASS")

    def test_is_user_invoked_only_helper(self):
        self.assertTrue(audit.is_user_invoked_only({"disable-model-invocation": "true"}))
        self.assertFalse(audit.is_user_invoked_only({}))
        self.assertFalse(audit.is_user_invoked_only({"disable-model-invocation": "false"}))


class TestDocGatingLanguagePresent(unittest.TestCase):
    """Lightweight prose checks so a revert or drift of the doc edits shows
    up in the suite, since nothing else here reads SKILL.md/frontmatter-spec.md
    text directly."""

    def test_skill_md_gates_description_optimization_stage(self):
        text = (CREATING_SKILLS_DIR / "SKILL.md").read_text()
        section = text.split("### Description optimization", 1)[1]
        self.assertRegex(section, r"[Ss]kip this entire stage for `disable-model-invocation: true`")

    def test_skill_md_gates_frontmatter_writing_step(self):
        text = (CREATING_SKILLS_DIR / "SKILL.md").read_text()
        self.assertRegex(text, r"disable-model-invocation: true`\s+skill,\s+write a plain")

    def test_skill_md_gates_discovery_substage(self):
        text = (CREATING_SKILLS_DIR / "SKILL.md").read_text()
        discovery_line = next(line for line in text.splitlines() if line.strip().startswith("1. **Discovery**"))
        self.assertIn("disable-model-invocation: true", discovery_line)

    def test_frontmatter_spec_scopes_description_guidance(self):
        text = (CREATING_SKILLS_DIR / "references" / "frontmatter-spec.md").read_text()
        section = text.split("## The description field, in full", 1)[1]
        self.assertRegex(section, r"[Aa]pplies to model-triggered skills only")

    def test_surface_matrix_cross_references_the_branch(self):
        text = (CREATING_SKILLS_DIR / "references" / "surface-matrix.md").read_text()
        row = next(line for line in text.splitlines() if line.strip().startswith("| `disable-model-invocation`"))
        self.assertIn("skips", row.lower())


if __name__ == "__main__":
    unittest.main()
