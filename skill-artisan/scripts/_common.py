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

# A key line's value is a block scalar (literal content, quotes not special)
# when it's exactly one of these markers with nothing else on the line.
BLOCK_SCALAR_MARKERS = (">", "|", ">-", "|-")


def _consume_indented_continuation(lines: list[str], start: int) -> tuple[str, int]:
    """Consume lines starting at `start` that are indented (2+ spaces or a
    tab) and non-blank, space-joining their stripped content. Returns
    (joined_text, next_index_to_resume_from) — a blank or unindented line
    ends the continuation, same as YAML's own indentation rule.
    """
    parts: list[str] = []
    i = start
    while i < len(lines) and lines[i] and (lines[i].startswith("  ") or lines[i].startswith("\t")):
        parts.append(lines[i].strip())
        i += 1
    return " ".join(parts), i


def _parse_frontmatter_lines(frontmatter_lines: list[str]) -> dict[str, str]:
    """Shared by parse_skill_md and parse_frontmatter_raw: walk frontmatter
    lines and reconstruct each key's full value, handling three YAML shapes
    for the value that follows a `key:`:

      1. `key: value` — value on the same line (the common case).
      2. `key: >` / `key: |` (+ `-` chomping variants) — an explicit
         block-scalar marker, continuation lines indented below it.
      3. `key:` with nothing after the colon, continuation lines indented
         below it — a plain or quoted multi-line scalar with NO block
         marker at all. Real example that motivated this case: a skill's
         `description:` wrapped across several lines as a bare quoted
         string (`description:\n  "Solve competition math problems...`) —
         neither parser previously looked past the empty same-line value,
         so the description silently came back as "", which cascaded into
         a false "triggering logic is broken" verdict in audit.py.

    Case 2's continuation is literal (quotes aren't stripped); case 3's is,
    since a quoted plain scalar's quotes are syntax, not content.
    """
    fields: dict[str, str] = {}
    i = 0
    while i < len(frontmatter_lines):
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", frontmatter_lines[i])
        if not match:
            i += 1
            continue
        key, value = match.groups()
        value = value.strip()
        if value in BLOCK_SCALAR_MARKERS:
            fields[key], i = _consume_indented_continuation(frontmatter_lines, i + 1)
            continue
        if value == "":
            joined, i = _consume_indented_continuation(frontmatter_lines, i + 1)
            fields[key] = joined.strip('"').strip("'")
            continue
        fields[key] = value.strip('"').strip("'")
        i += 1
    return fields


def _frontmatter_lines(content: str) -> list[str] | None:
    """Slice out the lines between the opening and closing --- delimiters,
    or None if the frontmatter block isn't well-formed."""
    lines = content.split("\n")
    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        return None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == FRONTMATTER_DELIM:
            return lines[1:i]
    return None


def parse_skill_md(skill_path: Path) -> tuple[str, str, str]:
    """Parse a SKILL.md file, returning (name, description, full_content).

    Handles single-line values, YAML block-scalar (`>`, `|`, `>-`, `|-`)
    values, and a bare multi-line value with no block marker at all (see
    _parse_frontmatter_lines) — the description optimizer round-trips
    through all three forms.
    """
    skill_md = Path(skill_path) / "SKILL.md"
    content = skill_md.read_text()
    lines = content.split("\n")

    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        raise ValueError(f"{skill_md}: missing frontmatter (no opening ---)")
    closing_idx = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == FRONTMATTER_DELIM), None)
    if closing_idx is None:
        raise ValueError(f"{skill_md}: missing frontmatter (no closing ---)")

    fields = _parse_frontmatter_lines(lines[1:closing_idx])
    return fields.get("name", ""), fields.get("description", ""), content


def parse_frontmatter_raw(skill_md_text: str) -> dict[str, str]:
    """Extract frontmatter key: value pairs, including multi-line values
    (block-scalar or bare) reconstructed in full — see
    _parse_frontmatter_lines. Used by validate.py and audit.py for
    field-presence and field-quality checks that don't need full YAML
    parsing.
    """
    frontmatter_lines = _frontmatter_lines(skill_md_text)
    if frontmatter_lines is None:
        return {}
    return _parse_frontmatter_lines(frontmatter_lines)


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
    directly contains a SKILL.md, one level down (marketplace/<skill>), two
    levels down (marketplace/plugin/<skill>), a plugin's own `skills/`
    subdirectory (marketplace/plugin/skills/<skill> — the real Claude Code
    plugin convention, verified directly: every installed plugin under
    ~/.claude/plugins/marketplaces/*/plugins/ on the machine this was built
    on uses <plugin>/skills/<skill>/SKILL.md, not the flatter <plugin>/<skill>
    shape the two-level glob alone assumes), or a *nested* plugin one level
    deeper still (category/plugin-name/skills/<skill> — found via the
    real-world audit pilot's Phase 6, alirezarezvani/claude-skills: some
    skills are packaged twice, once in a flat per-category `skills/`
    collection and again as a fully self-contained, individually-installable
    mini-plugin one level deeper. Checked exhaustively, not sampled, before
    adding this: 113 of 125 skills at this depth have *no* flat counterpart
    at all — genuinely unique content this discovery previously missed
    entirely, not redundant packaging of something already found), or one of
    two shapes found via the audit pilot's Phase 8 (anthropics/*, 2026-08-20):
    a `plugins/` wrapper directory adding one more level ahead of the
    existing category/plugin/skills/<skill> shape
    (`plugins/category/plugin/skills/<skill>` — anthropics/financial-services,
    117 of 118 skills live at exactly this depth, missed entirely before this
    fix), and platform/surface *sub-skills* nested one or two levels beneath
    an already-discovered skill's own directory
    (`.../skills/<skill>/<variant>/SKILL.md` and one level deeper still —
    anthropics/knowledge-work-plugins' zoom-plugin: a parent skill
    (`contact-center/SKILL.md`) explicitly routes to `android/SKILL.md`,
    `ios/SKILL.md`, `web/SKILL.md` as distinct, individually-loadable
    sub-skills via its own body text, not example/test content — confirmed
    by checking the parent's actual prose before adding this pattern, and by
    confirming neither pattern collides with two known false-positive shapes
    already present in other vendored corpora at different depths
    (`assets/sample-skill/SKILL.md`, `tests/fixtures/sample-skill/SKILL.md` —
    both intentionally excluded since neither has "skills" as a path
    component at the depth these new patterns require).

    Shared by dedup_search.py (searching for prior art) and audit.py's bulk
    mode (auditing a whole skills directory) — one implementation per the
    scripts/ discipline in references/script-design.md, not two copies that
    drift apart. Does not deduplicate by *content* — the same real-world
    check found 12 of 125 nested-layer skills are byte-identical repackagings
    of a flat-layer sibling; a caller that cares about auditing each unique
    skill exactly once (like aggregate_findings.py) needs to dedup on top of
    this function's output, since deciding "these two paths are the same
    skill" is a judgment about content, not about directory structure, which
    is deliberately outside this function's job.

    Skips any match reached through a symlink, at any level — found the hard
    way on the same repo, same phase: `Path.glob()` follows symlinks for
    ordinary (non-`**`) path components, and alirezarezvani/claude-skills
    symlink-mirrors every skill into four cross-tool directories
    (`.codex/`, `.gemini/`, `.hermes/`, `.vibe/`) for compatibility with
    other agent products. Unfiltered, that inflated discovery from 785 real
    skills to 1,140+ — the same skill re-counted once per mirror. `git`'s own
    tree API doesn't have this problem (it tracks a symlink as an opaque
    blob, never traverses into it), which is why this was invisible during
    planning (verified via the GitHub API) and only surfaced once skills
    were actually being discovered on a real local filesystem.
    """
    found = []
    for base in search_paths:
        if not base.is_dir():
            continue
        if (base / "SKILL.md").exists():
            found.append(base)
            continue
        for pattern in (
            "*/SKILL.md",
            "*/*/SKILL.md",
            "*/skills/*/SKILL.md",
            "*/*/skills/*/SKILL.md",
            "*/*/*/skills/*/SKILL.md",
            "*/*/skills/*/*/SKILL.md",
            "*/*/skills/*/*/*/SKILL.md",
        ):
            for skill_md in base.glob(pattern):
                if skill_md.is_symlink():
                    continue
                if any(p.is_symlink() for p in skill_md.parents if p != base and base in p.parents):
                    continue
                found.append(skill_md.parent)
    return sorted(set(found))
