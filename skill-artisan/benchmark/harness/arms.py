"""Static registry of the Best-in-Market Scorecard's 5 comparison arms.

No CLI, no side effects — a small shared config module other harness scripts import,
per script-design.md's "tiny single-purpose CLIs" rule (this is the shared-data exception,
same role _common.py plays for the rest of scripts/).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

ARMS = {
    "no-skill": {
        "label": "No skill (baseline)",
        "kind": "baseline",
        "entry_point": None,
        "notes": "No authoring step. Used only in Phase 5 (Axis 2 task-success delta) "
        "as the floor — the executor attempts each corpus skill's own eval prompts with "
        "no skill available at all.",
    },
    "skill-creator": {
        "label": "Anthropic skill-creator",
        "kind": "authoring",
        "entry_point": Path(
            "~/.claude/plugins/marketplaces/claude-plugins-official/plugins/"
            "skill-creator/skills/skill-creator/SKILL.md"
        ).expanduser(),
        "notes": "Installed plugin, unmodified. The incumbent this project supersedes.",
    },
    "daymade-fork": {
        "label": "daymade/claude-code-skills fork",
        "kind": "authoring",
        "entry_point": REPO_ROOT
        / "benchmark/vendored/daymade-claude-code-skills/daymade-skill/skill-creator/SKILL.md",
        "notes": "Pinned d24f6d1 (user-confirmed). Entry point is daymade's own "
        "skill-creator fork, not the repo's other 68 pre-built skills (those were only "
        "a corpus-sourcing pool).",
    },
    "skillforge": {
        "label": "tripleyak/SkillForge",
        "kind": "authoring",
        "entry_point": REPO_ROOT / "benchmark/vendored/tripleyak-skillforge/SKILL.md",
        "notes": "Pinned tag v6.0.0 / commit ce70b56f (user-confirmed). v6 uses a "
        "RED/GREEN execution gate, not the panel-review model the master spec describes "
        "SkillForge by — see benchmark/vendored/README.md.",
    },
    "creating-skills": {
        "label": "creating-skills (this project)",
        "kind": "authoring",
        "entry_point": REPO_ROOT / "creating-skills/SKILL.md",
        "notes": "This plugin's own flagship skill.",
    },
}

AUTHORING_ARMS = [name for name, cfg in ARMS.items() if cfg["kind"] == "authoring"]


def validate_entry_points() -> dict[str, bool]:
    """Return {arm_name: entry_point_exists} for every authoring arm."""
    return {
        name: cfg["entry_point"].is_file()
        for name, cfg in ARMS.items()
        if cfg["kind"] == "authoring"
    }


if __name__ == "__main__":
    import sys

    ok = validate_entry_points()
    for name, exists in ok.items():
        print(f"{'OK ' if exists else 'MISSING'} {name}: {ARMS[name]['entry_point']}")
    sys.exit(0 if all(ok.values()) else 1)
