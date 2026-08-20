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
    """Find every skill directory under each search path: any directory,
    at any depth, whose own `SKILL.md` exists, isn't reached through a
    symlink, and doesn't sit under an excluded intermediate directory.

    Architectural note (Phase 13 of the real-world audit pilot,
    `bobmatnyc/claude-mpm-skills`, 2026-08-20): through Phase 12, this
    function enumerated ten fixed glob patterns, each added incrementally as
    a new real-world packaging shape was found (a plugin's own `skills/`
    subdirectory, a nested mini-plugin one level deeper, a `plugins/` wrapper,
    platform sub-skills one or two levels beneath an already-discovered
    skill, a literal top-level `skills/` collection with two or three
    category levels, a `plugins/<product>/<version>/skills/<category>/<name>`
    shape — the full provenance for each lives in this project's git history
    and `benchmark/audit-pilot/RESULTS.md`, not repeated here). `bobmatnyc`
    broke that model outright: `universal/security/threat-modeling/SKILL.md`,
    `toolchains/php/frameworks/wordpress/wordpress-security-validation/SKILL.md`
    — plain category nesting at arbitrary depth, with no `skills/` marker
    directory anywhere to anchor a pattern against. No finite list of
    fixed-depth patterns can cover arbitrary depth; the fixed-pattern-list
    model had reached the shape of problem it can't solve. Replaced with a
    plain recursive walk (`rglob("SKILL.md")`), filtered by the same
    symlink-skip and intermediate-directory-exclusion logic already in place.
    **Verified safe before switching, not assumed**: run head-to-head against
    all nineteen corpora already vendored at the time (not sampled) —
    identical results everywhere except two, both confirmed improvements, not
    regressions: `bobmatnyc` itself (172 real skills recovered) and
    `aws-agent-toolkit-for-aws` (naturally recovers the single
    `agents-pay`-under-`packages`-under-`agents-pay` sub-package skill that
    Phase 9 had deliberately left undiscovered as "not worth a fifth
    single-purpose pattern" — the recursive walk needs no new pattern to
    reach it). Also faster in a direct timing comparison on the largest
    corpus (817 skills): ten overlapping glob passes versus one tree walk.

    Skips any match reached through a symlink, at any level — found via the
    audit pilot's Phase 6, alirezarezvani/claude-skills: some
    skills are packaged twice, once in a flat per-category `skills/`
    collection and again as a fully self-contained, individually-installable
    mini-plugin one level deeper. Checked exhaustively, not sampled, before
    adding this: 113 of 125 skills at this depth have *no* flat counterpart
    at all — genuinely unique content this discovery previously missed
    entirely, not redundant packaging of something already found; the same
    repo also symlink-mirrors every skill into four cross-tool directories
    (`.codex/`, `.gemini/`, `.hermes/`, `.vibe/`) for compatibility with
    other agent products, and `Path.glob()`/`rglob()` follow symlinks for
    ordinary path components — unfiltered, that inflated discovery from 785
    real skills to 1,140+, the same skill re-counted once per mirror.

    Excludes any match whose path (between the search root and the skill's
    own directory, exclusive of that directory's own name) passes through a
    directory named `assets`, `tests`, `fixtures`, or `example`. Each entry
    is backed by a confirmed real instance, not a guess: `assets`
    (`alirezarezvani-claude-skills`' `skill-tester/assets/sample-skill/`,
    Phase 8), `tests`/`fixtures`
    (`tripleyak-skillforge`'s `scripts/tests/fixtures/sample-skill/`, Phase 8;
    corroborated by `dotnet/skills`' `eng/skill-validator/tests/fixtures/`,
    Phase 12), `example` (`flutter/agent-plugins`'
    `tool/dart_skills_lint/example/skills/{valid,invalid}/`, Phase 12 — two
    deliberate linter test fixtures, both explicitly self-described as
    fixtures in their own body text and both carrying
    `metadata: {internal: true}`). Checked against every corpus already
    vendored each time a name was added: zero legitimate discoveries lost.

    Shared by dedup_search.py (searching for prior art) and audit.py's bulk
    mode (auditing a whole skills directory) — one implementation per the
    scripts/ discipline in references/script-design.md, not two copies that
    drift apart. Does not deduplicate by *content* — the same real-world
    check found 12 of 125 nested-layer skills (Phase 6) are byte-identical
    repackagings of a flat-layer sibling; a caller that cares about auditing
    each unique skill exactly once (like aggregate_findings.py) needs to
    dedup on top of this function's output, since deciding "these two paths
    are the same skill" is a judgment about content, not about directory
    structure, which is deliberately outside this function's job.
    """
    EXCLUDED_INTERMEDIATE_DIRS = {"assets", "tests", "fixtures", "example"}
    found = []
    for base in search_paths:
        if not base.is_dir():
            continue
        for skill_md in base.rglob("SKILL.md"):
            if skill_md.is_symlink():
                continue
            if any(p.is_symlink() for p in skill_md.parents if p != base and base in p.parents):
                continue
            skill_dir = skill_md.parent
            intermediate_parts = skill_dir.relative_to(base).parts[:-1]
            if any(part in EXCLUDED_INTERMEDIATE_DIRS for part in intermediate_parts):
                continue
            found.append(skill_dir)
    return sorted(set(found))
