"""Shared path resolution for the test suite — correct whether tests run
from the full monorepo checkout or from an installed plugin copy.

Found via a live marketplace-install check (2026-08-20): every test file
computed `REPO_ROOT = Path(__file__).resolve().parents[2]`, then
`SCRIPTS_DIR = REPO_ROOT / "skill-artisan" / "scripts"`. That's correct
only in the dev checkout, where a test file sits at
`<monorepo-root>/skill-artisan/tests/test_x.py` — two parents up is
`<monorepo-root>`, and re-appending "skill-artisan" gets back to the
plugin root. `EONRaider/claude-plugins`' marketplace entry installs this
plugin via `git-subdir` with `path: "skill-artisan"`, which fetches only
that directory's contents, not the wrapping monorepo — so in an install,
a test file sits at `<plugin-root>/tests/test_x.py`, one level shallower.
`parents[2]` there lands on the plugins cache's package-name directory,
and re-appending "skill-artisan" resolves to a path that doesn't exist,
breaking every import that depends on it.

`PLUGIN_ROOT` sidesteps the ambiguity: a test file's *immediate* parent's
parent (`parents[1]`) is always the plugin root — "tests/"'s parent —
in both contexts, since that's exactly what `git-subdir`'s `path` fetches
and exactly what the dev checkout's `skill-artisan/` directory is.

A few files live one level further out, outside the plugin entirely:
`action.yml`, this monorepo's own root `README.md`, and the pre-2.5.1
root `.claude-plugin/marketplace.json`. Those are structurally absent
from any install — `git-subdir` never fetches them — so `MONOREPO_ROOT`
is `None` there, and any test needing one of those files must
`self.skipTest(...)` rather than fail when it's unset.
"""
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"
CREATING_SKILLS_DIR = PLUGIN_ROOT / "creating-skills"

# Detected, not assumed: action.yml only exists one level above the plugin
# root in the dev checkout, never in an install.
MONOREPO_ROOT = PLUGIN_ROOT.parent if (PLUGIN_ROOT.parent / "action.yml").is_file() else None
