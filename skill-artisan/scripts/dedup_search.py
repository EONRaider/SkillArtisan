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

Usage:
    python scripts/dedup_search.py --query "review pull requests against a style guide"
    python scripts/dedup_search.py --query "..." --search-path ~/my-other-skills

Searches, by default: ~/.claude/skills/, ./.claude/skills/ (project-local),
and any --search-path directories given (repeatable). Add more with
--search-path; there's no reliable single location for installed plugin
skills across every Claude Code version, so point this at wherever your
plugin cache actually lives if you want those included.

Exit codes: 0 always (this is a search, not a gate — nothing here should
block anything by itself). 2 if no search paths existed at all.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from _common import find_skill_dirs, parse_skill_md

STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "to", "of", "in", "on", "with", "that", "this",
    "it", "is", "are", "be", "as", "at", "by", "from", "into", "your", "you", "use", "when",
    "using", "user", "users", "skill", "helps", "help", "helper", "should", "will", "can",
}

DEFAULT_SEARCH_PATHS = [Path.home() / ".claude" / "skills", Path.cwd() / ".claude" / "skills"]


def _stem(word: str) -> str:
    """Crude suffix stripping — enough to match "review"/"reviews"/"reviewing"
    to each other without pulling in a real NLP dependency for a heuristic
    that's explicitly a pre-ranking aid, not the actual match decision."""
    for suffix in ("ing", "ers", "er", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {_stem(w) for w in words if w not in STOPWORDS and len(w) > 2}


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


def search(query: str, search_paths: list[Path], min_score: float) -> list[dict]:
    query_tokens = tokenize(query)
    candidates = []
    for skill_dir in find_skill_dirs(search_paths):
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Find existing skills that might overlap a proposed new skill")
    parser.add_argument("--query", required=True, help="Free-text description of what the proposed skill would do")
    parser.add_argument("--search-path", action="append", default=[], help="Additional directory to search (repeatable)")
    parser.add_argument("--min-score", type=float, default=0.05, help="Minimum lexical overlap score to report (default: 0.05)")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a text report")
    args = parser.parse_args()

    search_paths = list(DEFAULT_SEARCH_PATHS) + [Path(p).expanduser() for p in args.search_path]
    existing_paths = [p for p in search_paths if p.is_dir()]
    if not existing_paths:
        print("No search paths exist — nothing to compare against.", file=sys.stderr)
        for p in search_paths:
            print(f"  (missing: {p})", file=sys.stderr)
        sys.exit(2)

    candidates = search(args.query, search_paths, args.min_score)

    if args.json:
        print(json.dumps({"query": args.query, "candidates": candidates}, indent=2))
        return

    print(f"Query: {args.query}")
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


if __name__ == "__main__":
    main()
