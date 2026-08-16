#!/usr/bin/env python3
"""Validate a skill directory: wraps the official skills-ref validator with a
Claude-specific layer on top.

Base layer (row 1, 19, 20): shells out to the agentskills.io reference
validator (`skills-ref validate <path>`, github.com/agentskills/agentskills)
for spec-level frontmatter checks — name/description constraints, no
consecutive hyphens, directory-name match. Verified directly against the
real tool while building this: skills-ref does NOT check for "claude" in the
name, does NOT enforce gerund naming, and does NOT check path references —
those three are genuinely this layer's job, not duplicated effort.

Claude-specific layer on top:
  - reserved words ("anthropic"/"claude") in `name` — hard error
  - gerund-form naming — warning + suggested alternative (not a hard spec
    rule; skills-ref accepts non-gerund names, so this can't be a failure)
  - extended Claude Code frontmatter fields — informational, not an error;
    skills-ref rejects these as "Unexpected fields" because it only knows
    the six portable fields, so this script strips them before invoking
    skills-ref (checking the six-field baseline is still correct) and
    reports them separately as "Claude Code only — will hard-error on
    spec-only surfaces" (row 22, see references/surface-matrix.md)
  - path-reference existence (row 29): every relative markdown link/image
    target in the SKILL.md body must resolve to a real file under the skill
    directory

Usage:
    python scripts/validate.py <skill_path>
    python scripts/validate.py <skill_path> --json
    python scripts/validate.py --suggest-compatibility claude-code,messages-api

The last form (row 22) populates the `compatibility` frontmatter field from
the target surface(s) instead of leaving it to prose — see
references/surface-matrix.md for what each surface name means in full.

Exit codes: 0 clean (warnings allowed), 1 validation errors, 2 skill not
found, 3 skills-ref unavailable (not on PATH and npx failed/unavailable).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from _common import parse_frontmatter_raw

SKILLS_REF_VERSION = "0.1.5"  # pinned — see references/script-design.md on pinning one-off runners

RESERVED_WORDS = ("anthropic", "claude")

# The six fields agentskills.io's spec (and skills-ref) actually accept.
PORTABLE_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}

# Claude Code extensions (references/surface-matrix.md documents these in full).
CLAUDE_CODE_ONLY_FIELDS = {
    "disable-model-invocation", "user-invocable", "context", "paths", "when_to_use", "argument-hint",
}

GERUND_SUFFIXES = ("ing", "ing-")


def find_skills_ref_cmd() -> list[str] | None:
    """Prefer a locally-installed skills-ref; fall back to a pinned npx run."""
    if shutil.which("skills-ref"):
        return ["skills-ref"]
    if shutil.which("npx"):
        return ["npx", "--yes", f"skills-ref@{SKILLS_REF_VERSION}"]
    return None


def run_skills_ref(skill_path: Path, frontmatter: dict[str, str], body_after_frontmatter: str) -> tuple[bool, list[str]]:
    """Run skills-ref against a stripped copy (portable fields only) so
    legitimate Claude Code extensions don't produce false spec failures.

    Returns (valid, error_lines).
    """
    cmd = find_skills_ref_cmd()
    if cmd is None:
        raise RuntimeError("skills-ref not found: install it (`npm install -g skills-ref`) or ensure npx is on PATH")

    portable = {k: v for k, v in frontmatter.items() if k in PORTABLE_FIELDS}
    with tempfile.TemporaryDirectory() as tmp:
        # Directory name must match `name` for skills-ref's own check to be meaningful;
        # use the real skill directory's name, not the frontmatter name, so a
        # genuine mismatch is still caught.
        stripped_dir = Path(tmp) / skill_path.name
        stripped_dir.mkdir()
        fm_lines = "\n".join(f"{k}: {v}" for k, v in portable.items())
        (stripped_dir / "SKILL.md").write_text(f"---\n{fm_lines}\n---\n{body_after_frontmatter}")

        try:
            result = subprocess.run(cmd + ["validate", str(stripped_dir)], capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            raise RuntimeError("skills-ref timed out")
        except FileNotFoundError:
            raise RuntimeError("skills-ref not found: install it (`npm install -g skills-ref`) or ensure npx is on PATH")

    output = (result.stdout + result.stderr).strip()
    if result.returncode == 0:
        return True, []
    errors = [line.strip().lstrip("- ").strip() for line in output.splitlines() if line.strip().startswith("-")]
    if not errors and output:
        errors = [output]
    return False, errors


def check_reserved_words(name: str) -> list[str]:
    lowered = name.lower()
    return [f"name contains reserved word '{word}'" for word in RESERVED_WORDS if word in lowered]


def check_gerund_form(name: str) -> str | None:
    """Warning only — skills-ref doesn't enforce this, it's an official
    recommendation, not a hard constraint."""
    first_segment = name.split("-")[0]
    if first_segment.endswith("ing"):
        return None
    return (
        f"name '{name}' isn't in gerund form (verb+-ing). Official recommendation, not a hard requirement — "
        f"consider a form like '{first_segment}ing-...' if there's a natural verb for what this skill does."
    )


def classify_extended_fields(frontmatter: dict[str, str]) -> tuple[list[str], list[str]]:
    """Split non-portable fields into (claude_code_only, genuinely_unknown)."""
    non_portable = [k for k in frontmatter if k not in PORTABLE_FIELDS]
    claude_only = [k for k in non_portable if k in CLAUDE_CODE_ONLY_FIELDS]
    unknown = [k for k in non_portable if k not in CLAUDE_CODE_ONLY_FIELDS]
    return claude_only, unknown


LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")


def check_path_references(skill_path: Path, body: str) -> list[str]:
    """Every relative markdown link/image target in the body must resolve to
    a real file under the skill directory."""
    missing = []
    for match in LINK_RE.finditer(body):
        target = match.group(1).strip()
        if not target or target.startswith(SKIP_PREFIXES) or "://" in target:
            continue
        target = target.split("#")[0].split(" ")[0]  # drop anchors and markdown title text
        if not target:
            continue
        if not (skill_path / target).exists():
            missing.append(target)
    return sorted(set(missing))


def validate(skill_path: Path) -> dict:
    result: dict = {"skill_path": str(skill_path), "errors": [], "warnings": [], "info": [], "valid": True}

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        result["errors"].append(f"No SKILL.md found at {skill_md}")
        result["valid"] = False
        return result

    content = skill_md.read_text()
    frontmatter = parse_frontmatter_raw(content)
    name = frontmatter.get("name", "")

    # Body after the closing --- (used both for skills-ref's stripped copy and path-ref checks)
    lines = content.split("\n")
    body_after_frontmatter = content
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                body_after_frontmatter = "\n".join(lines[i + 1:])
                break

    try:
        skills_ref_valid, skills_ref_errors = run_skills_ref(skill_path, frontmatter, body_after_frontmatter)
    except RuntimeError as e:
        result["errors"].append(str(e))
        result["valid"] = False
        result["skills_ref_unavailable"] = True
        return result

    if not skills_ref_valid:
        result["errors"].extend(f"[skills-ref] {e}" for e in skills_ref_errors)

    if name:
        result["errors"].extend(check_reserved_words(name))
        gerund_warning = check_gerund_form(name)
        if gerund_warning:
            result["warnings"].append(gerund_warning)

    claude_only, unknown = classify_extended_fields(frontmatter)
    if claude_only:
        result["info"].append(
            f"Claude Code-only fields present: {', '.join(sorted(claude_only))}. "
            f"These hard-error on spec-only surfaces (Claude.ai, Messages API, generic cross-vendor clients) — "
            f"fine if Claude Code is a target surface, see references/surface-matrix.md."
        )
    if unknown:
        result["errors"].append(f"Unrecognized frontmatter field(s): {', '.join(sorted(unknown))}")

    missing_refs = check_path_references(skill_path, body_after_frontmatter)
    if missing_refs:
        result["errors"].append(f"Missing referenced files: {', '.join(missing_refs)}")

    result["valid"] = len(result["errors"]) == 0
    return result


def print_report(result: dict) -> None:
    print(f"Validating: {result['skill_path']}")
    for e in result["errors"]:
        print(f"  ERROR: {e}")
    for w in result["warnings"]:
        print(f"  WARNING: {w}")
    for i in result["info"]:
        print(f"  INFO: {i}")
    if result["valid"]:
        print("Result: VALID" + (" (with warnings)" if result["warnings"] else ""))
    else:
        print("Result: INVALID")


# Row 22: compatibility auto-population by target surface. Full surface
# semantics documented in references/surface-matrix.md — these are the short
# forms meant to go directly into a `compatibility:` frontmatter value.
SURFACE_COMPATIBILITY = {
    "claude-code": "Claude Code (subagents, Bash, filesystem access)",
    "claude-ai": "Claude.ai (six portable fields only; no subagents, no CLI)",
    "cowork": "Cowork (subagents available; no browser/display — use --static viewer output)",
    "claude-tag": "Claude Tag (git-repo layout; discovered at .claude/skills/<name>/SKILL.md, session-start only)",
    "messages-api": "Messages API (code-execution container; no network access, no runtime package installs — declare required packages explicitly)",
    "cross-vendor": "Generic cross-vendor (agentskills.io-compliant clients; six portable fields only, no Claude-specific assumptions)",
}


def suggest_compatibility(surfaces: list[str]) -> str:
    unknown = [s for s in surfaces if s not in SURFACE_COMPATIBILITY]
    if unknown:
        raise ValueError(f"Unknown surface(s): {', '.join(unknown)}. Known: {', '.join(SURFACE_COMPATIBILITY)}")
    value = "; ".join(SURFACE_COMPATIBILITY[s] for s in surfaces)
    if len(value) > 500:
        raise ValueError(f"Suggested compatibility value is {len(value)} chars, over the 500-char limit — narrow the surface list")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a skill directory (skills-ref + Claude-specific checks)")
    parser.add_argument("skill_path", nargs="?", help="Path to the skill directory (not needed with --suggest-compatibility)")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON to stdout instead of a text report")
    parser.add_argument(
        "--suggest-compatibility", metavar="SURFACES",
        help=f"Comma-separated target surfaces; prints a ready-to-use compatibility field value and exits. "
             f"Known surfaces: {', '.join(SURFACE_COMPATIBILITY)}",
    )
    args = parser.parse_args()

    if args.suggest_compatibility:
        try:
            print(suggest_compatibility([s.strip() for s in args.suggest_compatibility.split(",") if s.strip()]))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if not args.skill_path:
        print("Error: skill_path is required unless --suggest-compatibility is given", file=sys.stderr)
        sys.exit(2)

    skill_path = Path(args.skill_path).resolve()
    if not skill_path.is_dir():
        print(f"Error: not a directory: {skill_path}", file=sys.stderr)
        sys.exit(2)

    result = validate(skill_path)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)

    if result.get("skills_ref_unavailable"):
        sys.exit(3)
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
