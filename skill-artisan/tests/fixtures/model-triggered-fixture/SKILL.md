---
name: model-triggered-fixture
description: Use when the user wants to export fixture data to a formatted report, mentions exporting test data, or wants to generate a fixture report file, even if they don't say "report" explicitly. This is a test fixture for skill-artisan's own test suite, not a real user-facing skill.
---

# Exporting Fixture Report

Test fixture for `skill-artisan/tests/test_disable_model_invocation.py`,
used as the model-triggered control case (no `disable-model-invocation`
field, so normal trigger-optimization guidance should still apply).

1. Read the fixture data.
2. Write the formatted report to disk.
