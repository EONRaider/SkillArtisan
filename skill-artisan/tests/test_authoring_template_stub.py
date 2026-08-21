#!/usr/bin/env python3
"""Regression test for issue #12: authoring-template stubs get discovered
and audited as if they were real skills, drawing a misleading rebuild/FAIL
verdict on content that's supposed to look unfilled.

Run: python3 -m unittest skill-artisan/tests/test_authoring_template_stub.py -v
(or `python3 -m unittest discover -s skill-artisan/tests` from anywhere)

Six real instances confirmed across the audit pilot (Phases 13, 19x2, 20,
22, 24 — nodnarbnitram/claude-code-extensions, secondsky/claude-skills,
skymavis/skills, skillscatalog/registry, acedatacloud/skills, aws-samples/
sample-well-architected-skills-and-steering). A `find_skill_dirs`-level
directory-name exclusion was checked and rejected (102 real skills across
two corpora legitimately use `templates/skills/<name>/` as real storage —
see benchmark/vendored/README.md's Phase 19 entry) — this fix instead adds
a narrow, content-based check inside audit.py: template-syntax in the
`name` field ({{...}}, [TODO:...]) or one of a handful of specific,
verbatim self-declaring phrasings pulled directly from the six real
instances in the `description` field. Detection suppresses the misleading
upgrade-vs-rebuild verdict rather than excluding the skill from discovery
at all — zero risk of silently dropping real content, the exact regression
`EXCLUDED_INTERMEDIATE_DIRS` would have risked.

A full sweep of this fix against all ~10,200 real skills already vendored
across the pilot found exactly 6 hits — the six known instances, all
correctly reasoned about, zero false positives — plus a seventh, previously
unknown instance sitting undetected in `nickcrew/claude-cortex` (Phase 15)
since it was first audited: `skills/template-skill`, genuinely the same
pattern, uncaught until this check existed.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_paths import SCRIPTS_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS_DIR))

import audit  # noqa: E402


class TestRealInstancesDetected(unittest.TestCase):
    """Every frontmatter block below is copied verbatim from the real
    corpus skill it names, not a synthetic approximation."""

    def test_nodnarbnitram_mustache_name_syntax(self):
        fm = {"name": "{{SKILL_NAME}}", "description": "{{DESCRIPTION}}"}
        self.assertIsNotNone(audit.detect_authoring_template_stub(fm))

    def test_secondsky_bracketed_todo_name_syntax(self):
        fm = {"name": "[TODO: lowercase-hyphen-case-name]",
              "description": "[TODO: Write comprehensive description in third-person...]"}
        self.assertIsNotNone(audit.detect_authoring_template_stub(fm))

    def test_skymavis_rename_this_skills_folder(self):
        fm = {"name": "skill-name",
              "description": "One sentence on what this skill does, then when to use it. The description "
                              "is the trigger surface an agent matches against, so be specific and write it "
                              "in the third person. Rename this skill's folder and set name to match (kebab-case)."}
        self.assertIsNotNone(audit.detect_authoring_template_stub(fm))

    def test_skillscatalog_brief_description_boilerplate(self):
        fm = {"name": "my-skill-name", "description": "A brief description of what this skill does"}
        self.assertIsNotNone(audit.detect_authoring_template_stub(fm))

    def test_acedatacloud_template_for_creating(self):
        fm = {"name": "template-skill",
              "description": "A template for creating new AceDataCloud Agent Skills. Copy this directory and customize."}
        self.assertIsNotNone(audit.detect_authoring_template_stub(fm))

    def test_aws_samples_never_use_directly(self):
        fm = {"name": "example-skill",
              "description": "Example skill template used for the CreateHub template. You should never use "
                              "this skill directly as it is just a template."}
        self.assertIsNotNone(audit.detect_authoring_template_stub(fm))

    def test_nickcrew_previously_unknown_seventh_instance(self):
        """Found live by this fix's own full-corpus sweep, not previously
        tracked on issue #12 — sitting mis-graded in nickcrew/claude-cortex
        since Phase 15 until this check existed."""
        fm = {"name": "template-skill",
              "description": "A template for creating new skills. Use when initializing a new skill to "
                              "ensure proper structure and metadata."}
        self.assertIsNotNone(audit.detect_authoring_template_stub(fm))


class TestRealSkillsUnaffected(unittest.TestCase):
    def test_ordinary_skill_not_flagged(self):
        fm = {"name": "competitor-analysis",
              "description": "Use when the user wants to analyze competitor pricing data across multiple "
                              "e-commerce platforms and generate a comparison report."}
        self.assertIsNone(audit.detect_authoring_template_stub(fm))

    def test_real_skill_literally_named_template_something_is_not_flagged_by_name_alone(self):
        """A real skill about a templating topic must not be swept up just
        because its name mentions the concept — only literal placeholder
        SYNTAX in the name field (braces, bracketed TODO/FIXME) counts, and
        only a specific, narrow set of self-declaring phrases in the
        description — not the bare word 'template'."""
        fm = {"name": "docx-template-generator",
              "description": "Use when the user asks to create a reusable Word document template with "
                              "placeholder fields for names, dates, and addresses."}
        self.assertIsNone(audit.detect_authoring_template_stub(fm))

    def test_real_skill_discussing_todo_lists_is_not_flagged(self):
        fm = {"name": "todo-list-manager",
              "description": "Use when the user wants to create, track, or prioritize TODO items across projects."}
        self.assertIsNone(audit.detect_authoring_template_stub(fm))


class TestChecklistItemAndDecisionSuppression(unittest.TestCase):
    def test_check_function_returns_warn_with_reason(self):
        fm = {"name": "{{SKILL_NAME}}", "description": "x"}
        item = audit.check_authoring_template_stub(fm)
        self.assertEqual(item["id"], "authoring-template-detected")
        self.assertEqual(item["status"], "WARN")
        self.assertIn("{{SKILL_NAME}}", item["detail"])

    def test_check_function_passes_ordinary_skill(self):
        fm = {"name": "real-skill", "description": "Use when the user needs X to happen."}
        item = audit.check_authoring_template_stub(fm)
        self.assertEqual(item["status"], "PASS")

    def test_warn_surfaces_in_review_queue_shape(self):
        """WARN, not MANUAL, is the deliberate choice — it's what makes this
        appear inside aggregate_findings.py's review-queue entry alongside
        the FAIL/WARN items it exists to explain, per the design note in
        audit.py. Confirmed here rather than just asserted."""
        fm = {"name": "{{SKILL_NAME}}", "description": "x"}
        item = audit.check_authoring_template_stub(fm)
        self.assertIn(item["status"], ("FAIL", "WARN"),
                      "must be a status aggregate_findings.py's review-queue filter picks up")

    def test_decision_suppressed_even_with_other_severe_failures(self):
        """A template stub's frontmatter is *supposed* to look broken —
        both a FAIL-shaped frontmatter-valid and description-pushy-imperative
        (the exact combination that would otherwise trigger 'triggering
        logic is fundamentally broken') must not produce a rebuild verdict
        once authoring-template-detected has fired."""
        items = [
            {"id": "authoring-template-detected", "status": "WARN", "detail": "template syntax detected"},
            {"id": "frontmatter-valid", "status": "FAIL", "detail": "..."},
            {"id": "description-pushy-imperative", "status": "FAIL", "detail": "..."},
            {"id": "body-size-limits", "status": "FAIL", "detail": "..."},
        ]
        decision = audit.decide_upgrade_vs_rebuild(items, None, None)
        self.assertEqual(decision["decision"], "upgrade-in-place")
        self.assertIn("authoring template", decision["reasons"][0])

    def test_decision_normal_when_not_a_template(self):
        """Confirms the suppression is conditional, not accidentally
        disabling the rebuild gate altogether."""
        items = [
            {"id": "authoring-template-detected", "status": "PASS", "detail": "no signal"},
            {"id": "frontmatter-valid", "status": "FAIL", "detail": "..."},
            {"id": "description-pushy-imperative", "status": "FAIL", "detail": "..."},
        ]
        decision = audit.decide_upgrade_vs_rebuild(items, None, None)
        self.assertEqual(decision["decision"], "rebuild")


if __name__ == "__main__":
    unittest.main()
