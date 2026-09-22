#!/usr/bin/env python3
"""Search for existing skills that might already cover a proposed skill's job.

Row 27 (prior art: daymade, refined by tripleyak/SkillForge's match-confidence
routing). This script does the part a script can actually do well — finding
candidates and ranking them by lexical overlap with the proposed skill's
description — and stops there. Deciding the real match confidence (≥80% use
existing / 50-79% improve existing / <50% create new / compose) requires
reading the close candidates' full SKILL.md and judging semantic overlap,
which is Claude's job, not this script's: a bag-of-words score cannot tell
you that "PDF form filling" and "PDF text extraction" are different jobs that
happen to share every non-stopword. Treat this script's output as a
shortlist to review, not a verdict — the decision gate in SKILL.md walks
through what to do with it.

Two modes, one per question:

- ``--query`` (whole-skill, the decision gate's check 2): does an existing
  skill already do what the proposed skill would do? Scores each candidate's
  frontmatter ``description`` by Jaccard overlap with the query.
- ``--fact`` (per-fact, used while drafting a justified new skill's body):
  does a sibling skill already state the governance, tooling, CI, or
  convention fact the draft is about to restate? Descriptions don't carry
  that kind of detail, so this mode splits each candidate's *body* into
  blocks (paragraphs, tables, lists, fenced code) and scores each block by
  coverage — the fraction of the fact's terms the block contains, not
  Jaccard, because a one-line fact checked against a twenty-row table
  would otherwise always score near zero for the table's size alone. The
  same caveat applies with more force: a hit means "read this block before
  writing yours," never "this is the same fact."

Usage:
    python scripts/dedup_search.py --query "review pull requests against a style guide"
    python scripts/dedup_search.py --query "..." --search-path ~/my-other-skills
    python scripts/dedup_search.py --fact "CI lint job runs ruff check locally" \
        --siblings-of .claude/skills/my-new-skill

Searches, by default: ~/.claude/skills/, ./.claude/skills/ (project-local),
and any --search-path directories given (repeatable). Add more with
--search-path; there's no reliable single location for installed plugin
skills across every Claude Code version, so point this at wherever your
plugin cache actually lives if you want those included. --siblings-of DIR
replaces those defaults with DIR's parent directory and excludes DIR itself
— the draft's own skills directory, minus the draft — which is the scope a
per-fact check wants; --search-path still adds to it.

Exit codes: 0 always (this is a search, not a gate — nothing here should
block anything by itself). 2 if no search paths existed at all.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from _common import find_skill_dirs, frontmatter_and_body, parse_skill_md

STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "to", "of", "in", "on", "with", "that", "this",
    "it", "is", "are", "be", "as", "at", "by", "from", "into", "your", "you", "use", "when",
    "using", "user", "users", "skill", "helps", "help", "helper", "should", "will", "can",
}

DEFAULT_SEARCH_PATHS = [Path.home() / ".claude" / "skills", Path.cwd() / ".claude" / "skills"]

# Per-mode --min-score defaults: Jaccard over two descriptions and coverage
# of a short fact by one block live on different scales, so one shared
# default would be either noise-flooded in fact mode or silent in query mode.
DEFAULT_MIN_SCORE = {"query": 0.05, "fact": 0.4}
DEFAULT_FACT_LIMIT = 10

HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def _stem(word: str) -> str:
    """Crude suffix stripping — enough to match "review"/"reviews"/"reviewing"
    to each other without pulling in a real NLP dependency for a heuristic
    that's explicitly a pre-ranking aid, not the actual match decision."""
    for suffix in ("ing", "ers", "er", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


# Two-letter words fact mode must still drop once it stops discarding every
# two-letter token (see tokenize's min_len).
SHORT_STOPWORDS = {
    "am", "do", "eg", "go", "he", "ie", "if", "me", "my", "no", "ok", "so", "up", "us", "vs", "we",
}


def tokenize(text: str, min_len: int = 3) -> set[str]:
    """Lowercased, stopword-filtered, crudely stemmed word set.

    ``min_len=3`` (the whole-skill default) drops every one- and two-letter
    word. Fact mode passes ``min_len=2``: the facts it checks for are full of
    load-bearing two-letter terms — CI, PR, gh, QA — that would otherwise
    vanish, leaving a fact like "CI runs ruff" scored on "run" and "ruff"
    alone.
    """
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {_stem(w) for w in words
            if len(w) >= min_len and w not in STOPWORDS and w not in SHORT_STOPWORDS}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


def suggest_tier(score: float) -> str:
    """Lexical-overlap-based suggestion only — see module docstring. Present
    this as a starting point for review, never as the actual routing decision."""
    if score >= 0.8:
        return "possible use-existing (verify by reading the candidate in full)"
    if score >= 0.5:
        return "possible improve-existing (verify by reading the candidate in full)"
    if score >= 0.2:
        return "possible compose ingredient (check if it covers part of the request)"
    return "low overlap"


def coverage(fact_tokens: set[str], block_tokens: set[str]) -> float:
    """Fraction of the fact's terms present in the block. Asymmetric on
    purpose: the question is whether the block *contains* the fact, and a
    block is allowed to say much more than the fact does."""
    if not fact_tokens:
        return 0.0
    return len(fact_tokens & block_tokens) / len(fact_tokens)


def split_blocks(body: str, first_line: int = 1) -> list[dict]:
    """Split a SKILL.md body into the units a restated fact would live in.

    A block is a run of non-blank lines (so a table, a tight list, or a
    paragraph each stay whole); a fenced code block is kept whole even
    across blank lines inside it. Headings aren't blocks themselves — each
    block records the nearest heading above it, since "## CI" is often the
    only place a block says what it's about. ``first_line`` is the 1-based
    file line number of the body's first line, so reported locations point
    into the real SKILL.md rather than into the frontmatter-stripped body.
    """
    blocks: list[dict] = []
    heading = ""
    current: list[str] = []
    start = 0
    fence = ""  # the opening marker (``` or ~~~) while inside a fenced block

    def flush() -> None:
        if current:
            blocks.append({"heading": heading, "line": start, "text": "\n".join(current)})
            current.clear()

    for offset, line in enumerate(body.split("\n")):
        lineno = first_line + offset
        fence_match = FENCE_RE.match(line)
        if fence:
            current.append(line)
            if fence_match and fence_match.group(1) == fence:
                fence = ""
            continue
        if fence_match:
            if not current:
                start = lineno
            current.append(line)
            fence = fence_match.group(1)
            continue
        heading_match = HEADING_RE.match(line)
        if heading_match:
            flush()
            heading = heading_match.group(1)
            continue
        if not line.strip():
            flush()
            continue
        if not current:
            start = lineno
        current.append(line)
    flush()
    return blocks


def _excluded(skill_dir: Path, exclude: list[Path]) -> bool:
    resolved = skill_dir.resolve()
    return any(resolved == e.resolve() for e in exclude)


def search_facts(fact: str, search_paths: list[Path], min_score: float,
                 exclude: list[Path] | None = None, limit: int | None = DEFAULT_FACT_LIMIT) -> list[dict]:
    """Rank body blocks of every skill under ``search_paths`` by how much of
    ``fact`` each one covers. ``exclude`` drops skill directories (the draft
    itself, when searching its siblings). ``limit`` caps the result count;
    ``None`` returns every block at or above ``min_score``."""
    fact_tokens = tokenize(fact, min_len=2)
    exclude = exclude or []
    hits = []
    for skill_dir in find_skill_dirs(search_paths):
        if _excluded(skill_dir, exclude):
            continue
        try:
            name, _, content = parse_skill_md(skill_dir)
        except (ValueError, OSError):
            continue
        _, body = frontmatter_and_body(content)
        body_first_line = content.count("\n") - body.count("\n") + 1
        for block in split_blocks(body, body_first_line):
            block_tokens = tokenize(f"{block['heading']}\n{block['text']}", min_len=2)
            score = coverage(fact_tokens, block_tokens)
            if score >= min_score:
                hits.append({
                    "name": name or skill_dir.name,
                    "path": str(skill_dir / "SKILL.md"),
                    "line": block["line"],
                    "heading": block["heading"],
                    "coverage_score": round(score, 3),
                    "matched_terms": sorted(fact_tokens & block_tokens),
                    "text": block["text"],
                })
    hits.sort(key=lambda h: (-h["coverage_score"], h["path"], h["line"]))
    return hits if limit is None else hits[:limit]


def search(query: str, search_paths: list[Path], min_score: float,
           exclude: list[Path] | None = None) -> list[dict]:
    query_tokens = tokenize(query)
    exclude = exclude or []
    candidates = []
    for skill_dir in find_skill_dirs(search_paths):
        if _excluded(skill_dir, exclude):
            continue
        try:
            name, description, _ = parse_skill_md(skill_dir)
        except (ValueError, OSError):
            continue
        score = jaccard(query_tokens, tokenize(description))
        if score >= min_score:
            candidates.append({
                "name": name or skill_dir.name,
                "path": str(skill_dir),
                "description": description,
                "lexical_overlap_score": round(score, 3),
                "suggested_tier": suggest_tier(score),
            })
    candidates.sort(key=lambda c: c["lexical_overlap_score"], reverse=True)
    return candidates


def _print_query_report(query: str, existing_paths: list[Path], candidates: list[dict]) -> None:
    print(f"Query: {query}")
    print(f"Searched: {', '.join(str(p) for p in existing_paths)}")
    if not candidates:
        print("\nNo candidates found above the similarity floor. Proceed toward 'create new' —")
        print("but this is a lexical search only; if you know of a differently-worded skill")
        print("that might cover this, check it by hand before concluding no match exists.")
        return

    print(f"\n{len(candidates)} candidate(s), ranked by lexical overlap (NOT a final verdict — read the close ones):\n")
    for c in candidates:
        print(f"  [{c['lexical_overlap_score']:.2f}] {c['name']} — {c['path']}")
        print(f"        {c['suggested_tier']}")
        print(f"        {c['description'][:160]}{'...' if len(c['description']) > 160 else ''}")
        print()


def _print_fact_report(fact: str, existing_paths: list[Path], hits: list[dict]) -> None:
    print(f"Fact: {fact}")
    print(f"Searched: {', '.join(str(p) for p in existing_paths)}")
    if not hits:
        print("\nNo sibling block covers enough of this fact's terms. Lexical only — if a sibling")
        print("you know of states it in different words, check that one by hand before writing it.")
        return

    print(f"\n{len(hits)} block(s), ranked by coverage of the fact's terms (NOT a verdict — read each")
    print("in context; where one really states the fact, point at it instead of restating it):\n")
    for h in hits:
        where = f" § {h['heading']}" if h["heading"] else ""
        first = " ".join(h["text"].split())
        print(f"  [{h['coverage_score']:.2f}] {h['name']}{where} — {h['path']}:{h['line']}")
        print(f"        matched: {', '.join(h['matched_terms'])}")
        print(f"        {first[:160]}{'...' if len(first) > 160 else ''}")
        print()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Find existing skills (--query) or sibling skill passages (--fact) that a new skill would duplicate")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--query", help="Free-text description of what the proposed skill would do (whole-skill dedup)")
    mode.add_argument("--fact", help="One governance/tooling/CI/convention fact a draft is about to state (per-fact dedup over sibling bodies)")
    parser.add_argument("--search-path", action="append", default=[], help="Additional directory to search (repeatable)")
    parser.add_argument("--siblings-of", metavar="DIR",
                        help="Search DIR's parent instead of the default paths, excluding DIR itself (the draft)")
    parser.add_argument("--min-score", type=float, default=None,
                        help=f"Minimum score to report (default: {DEFAULT_MIN_SCORE['query']} for --query, {DEFAULT_MIN_SCORE['fact']} for --fact)")
    parser.add_argument("--limit", type=int, default=DEFAULT_FACT_LIMIT,
                        help=f"--fact only: maximum blocks to report, 0 for no limit (default: {DEFAULT_FACT_LIMIT})")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a text report")
    args = parser.parse_args(argv)
    if args.limit < 0:
        parser.error("--limit must be 0 (no limit) or a positive integer")

    mode_name = "fact" if args.fact is not None else "query"
    min_score = DEFAULT_MIN_SCORE[mode_name] if args.min_score is None else args.min_score

    exclude: list[Path] = []
    if args.siblings_of:
        draft = Path(args.siblings_of).expanduser()
        exclude.append(draft)
        search_paths = [draft.resolve().parent]
    else:
        search_paths = list(DEFAULT_SEARCH_PATHS)
    search_paths += [Path(p).expanduser() for p in args.search_path]
    existing_paths = [p for p in search_paths if p.is_dir()]
    if not existing_paths:
        print("No search paths exist — nothing to compare against.", file=sys.stderr)
        for p in search_paths:
            print(f"  (missing: {p})", file=sys.stderr)
        sys.exit(2)

    if mode_name == "fact":
        hits = search_facts(args.fact, search_paths, min_score, exclude, args.limit or None)
        if args.json:
            print(json.dumps({"fact": args.fact, "hits": hits}, indent=2))
        else:
            _print_fact_report(args.fact, existing_paths, hits)
        return

    candidates = search(args.query, search_paths, min_score, exclude)
    if args.json:
        print(json.dumps({"query": args.query, "candidates": candidates}, indent=2))
    else:
        _print_query_report(args.query, existing_paths, candidates)


if __name__ == "__main__":
    main()
