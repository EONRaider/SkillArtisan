"""Shared helpers for SkillArtisan's scripts/ CLIs.

Not a script itself — nothing here has a __main__. Kept small and dependency-free
(stdlib only) so every script that imports it stays a tiny, single-purpose CLI
per the scripts/ discipline (see references/script-design.md).
"""

from __future__ import annotations

import math
import re
from pathlib import Path

FRONTMATTER_DELIM = "---"


def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:
    """Parse a SKILL.md file, returning (name, description, full_content).

    Handles both single-line and YAML block-scalar (`>`, `|`, `>-`, `|-`)
    description values, since the description optimizer round-trips through
    both forms.
    """
    skill_md = Path(skill_path) / "SKILL.md"
    content = skill_md.read_text()
    lines = content.split("\n")

    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        raise ValueError(f"{skill_md}: missing frontmatter (no opening ---)")

    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONTMATTER_DELIM:
            end_idx = i
            break
    if end_idx is None:
        raise ValueError(f"{skill_md}: missing frontmatter (no closing ---)")

    name = ""
    description = ""
    frontmatter_lines = lines[1:end_idx]
    i = 0
    while i < len(frontmatter_lines):
        line = frontmatter_lines[i]
        if line.startswith("name:"):
            name = line[len("name:"):].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            value = line[len("description:"):].strip()
            if value in (">", "|", ">-", "|-"):
                continuation: list[str] = []
                i += 1
                while i < len(frontmatter_lines) and (
                    frontmatter_lines[i].startswith("  ") or frontmatter_lines[i].startswith("\t")
                ):
                    continuation.append(frontmatter_lines[i].strip())
                    i += 1
                description = " ".join(continuation)
                continue
            description = value.strip('"').strip("'")
        i += 1

    return name, description, content


def parse_frontmatter_raw(skill_md_text: str) -> dict[str, str]:
    """Extract raw frontmatter key: value pairs (single-line values only).

    Used by validate.py for field-presence checks that don't need full YAML
    parsing. Multi-line block-scalar values collapse to a marker string
    rather than being reconstructed — callers that need the real value should
    use parse_skill_md instead.
    """
    lines = skill_md_text.split("\n")
    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        return {}
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONTMATTER_DELIM:
            end_idx = i
            break
    if end_idx is None:
        return {}

    fields: dict[str, str] = {}
    for line in lines[1:end_idx]:
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if match:
            key, value = match.groups()
            fields[key] = value.strip().strip('"').strip("'")
    return fields


def calculate_stats(values: list[float]) -> dict:
    """Mean, stddev (sample), min, max for a list of numeric values."""
    if not values:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}
    n = len(values)
    mean = sum(values) / n
    if n > 1:
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        stddev = math.sqrt(variance)
    else:
        stddev = 0.0
    return {
        "mean": round(mean, 4),
        "stddev": round(stddev, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
    }


# Trial-count presets (row 35, prior art: skillgrade). Named so authors don't
# have to remember magic numbers, and so eval_loop.py --ci can pick a sane
# default per context.
TRIAL_PRESETS = {
    "smoke": 5,       # quick capability check, e.g. every SKILL.md edit
    "reliable": 15,   # pre-review confidence
    "regression": 30,  # high-confidence regression detection before release
}


def find_skill_dirs(search_paths: list[Path]) -> list[Path]:
    """Find skill directories under each search path: the path itself if it
    directly contains a SKILL.md, one level down (marketplace/<skill>), or
    two levels down (plugin/<skill>, for marketplace/plugin-style layouts).

    Shared by dedup_search.py (searching for prior art) and audit.py's bulk
    mode (auditing a whole skills directory) — one implementation per the
    scripts/ discipline in references/script-design.md, not two copies that
    drift apart.
    """
    found = []
    for base in search_paths:
        if not base.is_dir():
            continue
        if (base / "SKILL.md").exists():
            found.append(base)
            continue
        for skill_md in base.glob("*/SKILL.md"):
            found.append(skill_md.parent)
        for skill_md in base.glob("*/*/SKILL.md"):
            found.append(skill_md.parent)
    return sorted(set(found))
