---
name: user-invoked-fixture
description: Export the current fixture data to a formatted report file.
disable-model-invocation: true
---

# Exporting Fixture Report

This skill is invoked exclusively by the user (e.g. via a slash command)
and must never be auto-triggered from a description match. It exists only
as a test fixture for `skill-artisan/tests/test_disable_model_invocation.py`
— it doesn't need real trigger-context prose because
`disable-model-invocation: true` means there's no trigger to optimize.

1. Read the fixture data.
2. Write the formatted report to disk.
