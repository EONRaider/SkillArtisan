# SkillArtisan

[![GitHub release](https://img.shields.io/github/v/release/EONRaider/SkillArtisan)](https://github.com/EONRaider/SkillArtisan/releases/latest)

A plugin for Claude Code that builds, validates, secures, and maintains Claude Skills — superseding Anthropic's shipped `skill-creator` with a spec-compliant, cross-vendor, security-hardened successor.

SkillArtisan bundles a main skill named **`creating-skills`** along with an evaluation engine, a security scanner, a dedup/decision gate, and an audit mode for existing skills. It is not a single SKILL.md file — see the plugin's architecture in [CONTRIBUTING.md](CONTRIBUTING.md#plugin-architecture).

## Why this exists

Anthropic's own `skill-creator` is a good starting point, but has real gaps: no frontmatter validation, no gerund-naming guidance, no multi-model testing, no security scanning beyond a one-line "don't build malware" principle, and no way to audit or upgrade an existing skill. SkillArtisan closes all of these, while keeping the one thing `skill-creator` already does well — its evaluation and description-optimization engine — as its architectural basis: ported wholesale rather than redesigned from scratch, then hardened with five real bug fixes actual regression testing found (see "Verified against `skill-creator`'s current source" in [skill-artisan/README.md](skill-artisan/README.md)) — all five still present, unfixed, in `skill-creator`'s own code today.

The design is grounded in the canonical, cross-vendor [agentskills.io](https://agentskills.io) specification (not just Claude-specific conventions), so skills built with SkillArtisan are portable across Claude Code, Cursor, GitHub Copilot, Codex, Gemini CLI, and 40+ other agent products by default.

## Install

```
claude plugin marketplace add EONRaider/claude-plugins
claude plugin install skillartisan@eonraider
```

Requirements: Python 3.8+, [gitleaks](https://github.com/gitleaks/gitleaks) (for security scanning), `claude` CLI (for evaluation runs and description optimization), and Node.js (`npx`, for the `skills-ref` frontmatter validator — `validate.py` falls back to a pinned `npx` run if `skills-ref` isn't already installed locally). `git` and the GitHub CLI (`gh`, authenticated) are required only for `scripts/pr_execute.py`'s real-effects path (`audit.py pr-execute`) — everything else works without either.

## Quick start

Once installed, just ask Claude naturally:

```
"Create a skill that reviews pull requests for our team's style guide"
"Audit my existing invoice-parser skill against best practices"
"Benchmark this skill's trigger accuracy"
```

SkillArtisan's decision gate will first confirm a skill is actually the right tool (as opposed to CLAUDE.md, AGENTS.md, an MCP server, a subagent, or a plugin), check whether something already solves the request, then walk through authoring, validation, security scanning, and evaluation.

## GitHub Action

Any repository can install SkillArtisan's audit as a GitHub Action to check its own skills automatically, no local Claude Code session required:

```yaml
- uses: actions/checkout@v4
- uses: EONRaider/SkillArtisan@v2.5.4
  with:
    skills-path: .                                    # default: whole workspace
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }} # optional — see below
```

Behavior is gated on that one secret's presence, not a mode flag:

- **No `ANTHROPIC_API_KEY`** — mechanical audit only (`scripts/audit.py`'s checklist: frontmatter, security, evals, lifecycle, etc.), written to the job's step summary. Free — a consuming repo can safely wire this to `on: push` / `on: pull_request` if it wants continuous auditing.
- **`ANTHROPIC_API_KEY` set** — same report, plus: every skill with FAIL items gets an additive-only fix authored by Claude and opened as a pull request for review (`scripts/pr_execute.py` — same hard-refusal on any delete/rename, same idempotent branch naming, whether invoked from a chat session or from this Action). Nothing is ever merged automatically. `max-skills` (default `10`) caps API spend per run.

See `action.yml` for the full input list, and `.github/workflows/self-test-action.yml` / `self-test-action-fix-pr.yml` in this repo for working examples of both modes. Both are `workflow_dispatch`-only (manual trigger) *in this repo* — SkillArtisan deliberately doesn't audit its own skills automatically on every push here — regardless of how a consuming repo chooses to trigger the report-only mode for itself.

## Security

Every skill produced or audited by SkillArtisan is scanned with [gitleaks](https://github.com/gitleaks/gitleaks) before packaging, plus pattern-based checks for absolute paths, exposed emails, insecure URLs, and dangerous code patterns (available via `--verbose`). A content-hash tamper-detection marker prevents shipping a skill that was edited after its last clean scan.

**Automated scanning has a ceiling.** Pattern-based tools cannot see everything — they're blind to non-English content, real names embedded in examples, or lines lifted from real transcripts, since none of that has a keyword to trigger on. Before publishing any skill publicly, read it yourself. A clean scan is a gate, not a guarantee. See `references/sanitization-checklist.md`.

## Contributing

Working on SkillArtisan itself, rather than installing it? See [CONTRIBUTING.md](CONTRIBUTING.md) for the repo layout, the plugin's internal architecture, and how to test the eval engine's subagents locally.

## Status

**Current version: `2.5.4`** — see [`skill-artisan/CHANGELOG.md`](skill-artisan/CHANGELOG.md) for the full release history.

## Credits

SkillArtisan's evaluation engine is ported from Anthropic's `skill-creator`. Its security scanning architecture, dedup/decision gate refinements, and several structural conventions are adapted from real prior art in this space — particularly [`daymade/claude-code-skills`](https://github.com/daymade/claude-code-skills) and [`tripleyak/SkillForge`](https://github.com/tripleyak/SkillForge) — with attribution preserved in the [Gap Table](skill-artisan-master-spec.md#gap-table) row by row. This project exists because that prior art already fought many of these battles well; the goal was to synthesize the best of it against the canonical spec, not to claim originality it doesn't have.

## License

MIT — see [LICENSE](LICENSE).
