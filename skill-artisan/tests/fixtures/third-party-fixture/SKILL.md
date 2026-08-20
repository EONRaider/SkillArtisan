---
name: third-party-fixture
description: Reviews dependency manifests for known-vulnerable version pins. Use when the user asks for a dependency security review or mentions vulnerable packages.
---

# Third-party fixture

A minimal stand-in for a skill authored entirely outside SkillArtisan's
pipeline: none of the pipeline's artifacts exist here — no scan marker
file, no `evals/` directory, and no classification line of the kind
`references` conventions add. (The artifacts are deliberately not named
in this prose: detection matches on content, and naming them here would
make this fixture read as first-party.) `audit.py`'s source auto-detection
must classify this as third-party.

## Workflow

1. Read the dependency manifest the user points at.
2. Compare each pin against the advisory list.
3. Report vulnerable pins with the fixed version to upgrade to.
