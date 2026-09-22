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
found, 3 skills-ref unavailable (no copy on PATH, no vendored copy, and no
opt-in npx fallback).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from _common import frontmatter_and_body, resolve_skill_path_or_name

SKILLS_REF_VERSION = "0.1.5"  # the vendored release; also the pin for the opt-in npx fallback

# The vendored skills-ref, shipped with the plugin so validation needs no
# network and no npm install. See vendor/README.md for provenance and the
# registry integrity hash that lets this copy be re-verified byte for byte.
VENDORED_SKILLS_REF = Path(__file__).resolve().parent.parent / "vendor" / "skills-ref" / "dist" / "cli.js"

# Opt-in escape hatch for resolution step 3 — see find_skills_ref_cmd().
ALLOW_NPX_FETCH_ENV = "SKILLS_REF_ALLOW_NPX_FETCH"

SKILLS_REF_MISSING_MSG = (
    "skills-ref not found: the vendored copy under vendor/skills-ref/ is missing or `node` is not on "
    "PATH. Install Node.js, or install skills-ref globally (`npm install -g skills-ref`)."
)

RESERVED_WORDS = ("anthropic", "claude")

# The six fields agentskills.io's spec (and skills-ref) actually accept.
# CRITICAL (issue #9): a third-party `tools` field (a YAML list of tool
# names used as descriptive/cataloging metadata, distinct from this file's
# own `allowed-tools`) must never be added here and must never be aliased to
# `allowed-tools` — `allowed-tools` has real runtime permission-bypass
# semantics (tools Claude can use without asking during the turn that
# invokes this skill), and `PORTABLE_FIELDS` feeds run_skills_ref()'s
# portable-field passthrough below. Doing either would grant real,
# unintended permission-bypass behavior to skills whose authors never asked
# for that. `tools` only ever goes through the WARN-level
# THIRD_PARTY_FIELD_FAMILIES path (see `tool-usage-metadata` below), same as
# every other non-portable field.
PORTABLE_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}

# Claude Code extensions (references/surface-matrix.md documents these in full).
# Synced against the official frontmatter reference at
# https://code.claude.com/docs/en/skills.md — the pre-sync list was missing
# eight documented fields, which made validate.py hard-FAIL real skills using
# them (issue #5's `agent: general-purpose` alongside `context: fork` was the
# corpus find that exposed this).
CLAUDE_CODE_ONLY_FIELDS = {
    "disable-model-invocation", "user-invocable", "context", "paths", "when_to_use", "argument-hint",
    "agent", "arguments", "disallowed-tools", "model", "effort", "background", "hooks", "shell",
}

# Known third-party metadata field families (issue #7). Real, coherent
# taxonomies observed in the wild that aren't portable and aren't Claude Code
# fields, but also aren't authoring mistakes — flagging them as hard errors
# on 817/817 skills of a corpus (mukul975/Anthropic-Cybersecurity-Skills)
# taught nothing. Fields here downgrade to a portability warning naming the
# family. Deliberately NOT included, so they keep hard-erroring: recorded
# true positives (`user_invocable` — an underscore typo for the real
# `user-invocable`) plus `command`, `agents`, `compatible_tools` from the
# Phase 5/6 pilot notes. `triggers` was originally grouped with those three as
# a "bespoke one-off convention" too, but issue #8 found it independently and
# consistently used across five unrelated authorship models (Anthropic's own
# zoom-plugin, NVIDIA, an academic genomics project, and two more) — real
# corroborated convention, not a one-off, so it moved to `routing-metadata`
# below. Any other still-undecided candidate raised only once in an issue
# thread (`type`, a progressive-disclosure cluster, a marketing-metadata
# family, `requirements`, a governance taxonomy — see issue #9's comments)
# stays deliberately unresolved: one data point isn't enough to name/size a
# family without risking the same speculative-guess problem this discipline
# exists to avoid.
THIRD_PARTY_FIELD_FAMILIES: dict[str, set[str]] = {
    "security-framework-taxonomy": {
        "mitre_attack", "nist_csf", "d3fend_techniques", "mitre_f3",
        "atlas_techniques", "nist_ai_rmf", "domain", "subdomain",
    },
    "common-authoring-metadata": {"author", "tags", "version"},
    # Issue #8: a YAML list of trigger phrases. Corroborated across five
    # independent authorship models (anthropics/knowledge-work-plugins,
    # mims-harvard/tooluniverse, aitytech/agentkits-marketing, and two more) —
    # not the one-off it was originally characterized as.
    "routing-metadata": {"triggers"},
    # Issue #9 (nvidia/skills, Phase 9): a real, consistently-used internal
    # ownership/review-date triplet, e.g. `owner: "NVIDIA CORPORATION"`,
    # `service: "auto-magic-calib"`, `reviewed: "2026-06-15"` (8 skills).
    "governance-metadata": {"owner", "service", "reviewed"},
    # Issue #9 (nvidia/skills, Phase 9): a YAML list of tool names used as
    # descriptive/cataloging metadata (16 skills, e.g. `tools: [Read, Glob]`).
    # This family name is a proposal open for maintainer confirmation — the
    # issue explicitly left it unnamed pending explicit sign-off.
    # `tools` must never be aliased to `allowed-tools` or added to
    # PORTABLE_FIELDS — see the guardrail comment above PORTABLE_FIELDS.
    "tool-usage-metadata": {"tools"},
}

GERUND_SUFFIXES = ("ing", "ing-")


def find_skills_ref_cmd() -> list[str] | None:
    """Resolve how to invoke skills-ref, preferring the author's own copy.

    Order:
      1. A `skills-ref` already on PATH — a deliberate local install is a
         choice to respect, and it lets an author test against a newer
         validator than the one vendored here.
      2. The vendored copy under `vendor/skills-ref/`, run through `node`.
         This is the normal path: it needs no network and no npm state, so
         validation behaves identically on a laptop, in CI, and inside a
         sandbox with egress blocked.
      3. A pinned `npx` fetch — only when SKILLS_REF_ALLOW_NPX_FETCH=1 is
         set. Fetching a package from a public registry at validate time
         means executing third-party code that nothing on the machine has
         vetted, on every run; a version pin bounds *which* release that is
         but does not make it reviewed. Since the vendored copy makes the
         fetch unnecessary, it stays available for the case where an author
         deliberately wants a registry round-trip, and is off by default.
    """
    if shutil.which("skills-ref"):
        return ["skills-ref"]
    if VENDORED_SKILLS_REF.is_file() and shutil.which("node"):
        return ["node", str(VENDORED_SKILLS_REF)]
    if os.environ.get(ALLOW_NPX_FETCH_ENV) == "1" and shutil.which("npx"):
        return ["npx", "--yes", f"skills-ref@{SKILLS_REF_VERSION}"]
    return None


def run_skills_ref(skill_path: Path, frontmatter: dict[str, str], body_after_frontmatter: str) -> tuple[bool, list[str]]:
    """Run skills-ref against a stripped copy (portable fields only) so
    legitimate Claude Code extensions don't produce false spec failures.

    Returns (valid, error_lines).
    """
    cmd = find_skills_ref_cmd()
    if cmd is None:
        raise RuntimeError(SKILLS_REF_MISSING_MSG)

    portable = {k: v for k, v in frontmatter.items() if k in PORTABLE_FIELDS}
    with tempfile.TemporaryDirectory() as tmp:
        # Directory name must match `name` for skills-ref's own check to be meaningful;
        # use the real skill directory's name, not the frontmatter name, so a
        # genuine mismatch is still caught.
        stripped_dir = Path(tmp) / skill_path.name
        stripped_dir.mkdir()
        # json.dumps produces a YAML-valid double-quoted scalar (YAML's
        # double-quoted flow style is a superset of JSON string syntax) —
        # escapes any character that would otherwise break the reconstructed
        # line (a leading `"`, an embedded `:` or `#`, a backslash). Naive
        # f"{k}: {v}" interpolation broke on a real value that itself started
        # with a literal quote character: a legitimately-parsed description
        # was re-serialized into invalid YAML, so skills-ref rejected a
        # genuinely valid skill. Every value here is always a plain string
        # (parse_frontmatter_raw never returns anything else), so this is a
        # safe, unconditional escape, not a special case.
        fm_lines = "\n".join(f"{k}: {json.dumps(v)}" for k, v in portable.items())
        (stripped_dir / "SKILL.md").write_text(f"---\n{fm_lines}\n---\n{body_after_frontmatter}")

        try:
            result = subprocess.run(cmd + ["validate", str(stripped_dir)], capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            raise RuntimeError("skills-ref timed out")
        except FileNotFoundError:
            raise RuntimeError(SKILLS_REF_MISSING_MSG)

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


def classify_extended_fields(frontmatter: dict[str, str]) -> tuple[list[str], dict[str, list[str]], list[str]]:
    """Split non-portable fields into (claude_code_only, known_third_party,
    genuinely_unknown). known_third_party maps family name -> fields present,
    for the families in THIRD_PARTY_FIELD_FAMILIES."""
    non_portable = [k for k in frontmatter if k not in PORTABLE_FIELDS]
    claude_only = [k for k in non_portable if k in CLAUDE_CODE_ONLY_FIELDS]
    known_third_party: dict[str, list[str]] = {}
    unknown = []
    for k in non_portable:
        if k in CLAUDE_CODE_ONLY_FIELDS:
            continue
        family = next((name for name, fields in THIRD_PARTY_FIELD_FAMILIES.items() if k in fields), None)
        if family:
            known_third_party.setdefault(family, []).append(k)
        else:
            unknown.append(k)
    return claude_only, known_third_party, unknown


LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
FENCED_CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#", "~")
BASE_DIR_PREFIXES = ("{baseDir}/", "{baseDir}")


def check_path_references(skill_path: Path, body: str) -> list[str]:
    """Every relative markdown link/image target in the body must resolve to
    a real file under the skill directory. Fenced code blocks, inline code
    spans, and HTML comments are stripped first — a ```markdown example
    showing what a template file should contain (e.g. a worked-example link
    like `[title](link)`), prose demonstrating markdown link syntax inline
    (e.g. "do NOT create links like `[doc.md](reviewed-document)`" — a
    daymade/claude-code-skills skill's actual cautionary example, ironically
    about this exact mistake), or an author-facing authoring note inside
    `<!-- -->` showing what optional collateral links should look like
    (e.g. `<!-- ... "Watch the [intro](URL)..." -->` — a real, literal
    placeholder found 12 times across anthropics/claude-for-legal's
    cold-start-interview, Phase 8 of the audit pilot) isn't a real reference
    into this skill's own directory, and matching it produces a false
    "missing file" finding. A `~/`-prefixed target is skipped too — it names
    another skill's expected *installed* location (e.g.
    `[calendar-sync](~/.claude/skills/calendar-sync)`, a real cross-skill
    dependency reference found in glebis/claude-skills), never a relative
    path within this skill's own bundle.

    A `{baseDir}/`-prefixed target (trailofbits/skills, Phase 11) is different
    from the skip cases above: it's a real, checkable, skill-relative
    reference under a cross-platform template-variable convention (not
    Claude Code's own `${CLAUDE_SKILL_DIR}` substitution syntax — a different,
    dollar-less convention this repo's skills use, presumably for portability
    across multiple agent tools), meant to resolve to the skill's own
    directory root at runtime. Verified directly before fixing: every one of
    41 `{baseDir}`-prefixed references across 7 skills in that repo resolves
    to a real file once the prefix is stripped — 100%, not a sample. Unlike
    the SKIP_PREFIXES targets (which can never be locally verified), this
    prefix is stripped, not skipped, so a genuinely broken
    `{baseDir}/nonexistent.md` reference is still correctly caught."""
    body = FENCED_CODE_BLOCK_RE.sub("", body)
    body = INLINE_CODE_SPAN_RE.sub("", body)
    body = HTML_COMMENT_RE.sub("", body)
    missing = []
    for match in LINK_RE.finditer(body):
        target = match.group(1).strip()
        if not target or target.startswith(SKIP_PREFIXES) or "://" in target:
            continue
        if target.startswith(BASE_DIR_PREFIXES):
            target = target[len("{baseDir}"):].lstrip("/")
        target = target.split("#")[0].split(" ")[0]  # drop anchors and markdown title text
        if not target:
            continue
        if not (skill_path / target).exists():
            missing.append(target)
    return sorted(set(missing))


CLAUDE_SKILL_DIR_REF_RE = re.compile(r"\$\{CLAUDE_SKILL_DIR\}/([^\s`\"')\]>]+)")


def check_claude_skill_dir_refs(skill_path: Path, content: str) -> list[str]:
    """Find `${CLAUDE_SKILL_DIR}/...` references that don't resolve to a
    real file under the skill directory. Deliberately runs on the RAW,
    unstripped file content (frontmatter and body both — a scoped
    `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/*)` value is a real,
    common place for this substitution to appear) — unlike
    check_path_references, which strips fenced code blocks and inline code
    spans before its markdown-link regex runs. `${CLAUDE_SKILL_DIR}/...`
    references overwhelmingly live inside backticked shell snippets (it's
    Claude Code's own runtime substitution for "this skill's own
    directory," used in body commands and `allowed-tools` values, not
    markdown links), so that stripping pass would make this check blind to
    exactly what it exists to catch.

    WARN-level in validate() below, not a hard error like
    check_path_references: a skill's own documentation *about* the
    `${CLAUDE_SKILL_DIR}` convention (e.g. a reference file explaining this
    exact syntax with an illustrative, never-meant-to-exist example path)
    is a false positive this check cannot structurally distinguish from a
    genuinely broken reference, unlike check_path_references' narrower
    prose-example exclusions — so this surfaces for a human/LLM read
    instead of failing validation outright on a possible false positive.
    """
    missing = []
    for match in CLAUDE_SKILL_DIR_REF_RE.finditer(content):
        target = match.group(1).rstrip(".,;:\"')")
        if target and not (skill_path / target).exists():
            missing.append(target)
    return sorted(set(missing))


BUNDLED_SCRIPT_EXTENSIONS = (".sh", ".py", ".js", ".ts", ".mjs", ".rb")
BASH_TOOL_RE = re.compile(r"\bBash\b")


def check_scripts_need_bash_permission(skill_path: Path, frontmatter: dict[str, str], content: str) -> str | None:
    """WARN, not error: a deliberate human-in-the-loop gate on a sensitive
    script is a legitimate low-freedom-tier authoring choice (see
    references/writing-philosophy.md's degrees-of-freedom tiers), not
    automatically a bug — this only flags the likely-forgotten case where a
    bundled script is mentioned but nothing grants Bash to run it, meaning
    every invocation hits a permission prompt.

    Looks for any bundled file with a script extension whose filename
    appears anywhere in the raw content, then checks whether
    `allowed-tools` grants Bash and `disallowed-tools` doesn't block it —
    a lightweight heuristic (mention, not a verified call), matching the
    confidence level of this codebase's other WARN-level content checks
    (e.g. check_degrees_of_freedom_proxy).
    """
    allowed = frontmatter.get("allowed-tools", "")
    disallowed = frontmatter.get("disallowed-tools", "")
    has_bash = bool(BASH_TOOL_RE.search(allowed)) and not BASH_TOOL_RE.search(disallowed)
    if has_bash:
        return None
    for script_file in sorted(skill_path.rglob("*")):
        if script_file.suffix in BUNDLED_SCRIPT_EXTENSIONS and script_file.name in content:
            return (f"references bundled script '{script_file.name}' but frontmatter doesn't grant Bash "
                    f"permission (allowed-tools missing Bash, or disallowed-tools blocks it) — every "
                    f"invocation will hit a permission prompt unless that's a deliberate gate")
    return None


def validate(skill_path: Path) -> dict:
    result: dict = {"skill_path": str(skill_path), "errors": [], "warnings": [], "info": [], "valid": True}

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        result["errors"].append(f"No SKILL.md found at {skill_md}")
        result["valid"] = False
        return result

    content = skill_md.read_text()
    frontmatter, body_after_frontmatter = frontmatter_and_body(content)
    name = frontmatter.get("name", "")

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

    claude_only, known_third_party, unknown = classify_extended_fields(frontmatter)
    if claude_only:
        result["info"].append(
            f"Claude Code-only fields present: {', '.join(sorted(claude_only))}. "
            f"These hard-error on spec-only surfaces (Claude.ai, Messages API, generic cross-vendor clients) — "
            f"fine if Claude Code is a target surface, see references/surface-matrix.md."
        )
    for family, fields in sorted(known_third_party.items()):
        # Warning, not error: a recognized third-party metadata family — real
        # taxonomy, not a typo. NOTE: this text must never contain the word
        # audit.py filters warnings on (naming-convention check), see
        # check_frontmatter_and_paths.
        result["warnings"].append(
            f"Known third-party metadata family '{family}': {', '.join(sorted(fields))}. "
            f"Not portable — spec-compliant clients reject unrecognized fields; nest these under "
            f"`metadata:` for cross-vendor compatibility."
        )
    if unknown:
        result["errors"].append(f"Unrecognized frontmatter field(s): {', '.join(sorted(unknown))}")

    missing_refs = check_path_references(skill_path, body_after_frontmatter)
    result["missing_references"] = missing_refs
    result["missing_references_error"] = None
    if missing_refs:
        result["missing_references_error"] = f"Missing referenced files: {', '.join(missing_refs)}"
        result["errors"].append(result["missing_references_error"])

    dangling_skill_dir_refs = check_claude_skill_dir_refs(skill_path, content)
    result["dangling_skill_dir_references"] = dangling_skill_dir_refs
    if dangling_skill_dir_refs:
        result["warnings"].append(
            f"Dangling ${{CLAUDE_SKILL_DIR}} reference(s): {', '.join(dangling_skill_dir_refs)}"
        )

    bash_permission_warning = check_scripts_need_bash_permission(skill_path, frontmatter, content)
    result["bash_permission_warning"] = bash_permission_warning
    if bash_permission_warning:
        result["warnings"].append(bash_permission_warning)

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
    parser.add_argument("skill_path", nargs="?",
                         help="Path to the skill directory, or a bare installed skill name to resolve "
                              "(not needed with --suggest-compatibility)")
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

    skill_path = resolve_skill_path_or_name(args.skill_path)
    if skill_path is None:
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
