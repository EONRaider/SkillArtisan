# SkillArtisan

A plugin for Claude Code that builds, validates, secures, and maintains Claude Skills — superseding Anthropic's shipped `skill-creator` with a spec-compliant, cross-vendor, security-hardened successor.

SkillArtisan bundles a main skill named **`creating-skills`** along with an evaluation engine, a security scanner, a dedup/decision gate, and an audit mode for existing skills. It is not a single SKILL.md file — see [Architecture](#architecture) below.

## Why this exists

Anthropic's own `skill-creator` is a good starting point, but has real gaps: no frontmatter validation, no gerund-naming guidance, no multi-model testing, no security scanning beyond a one-line "don't build malware" principle, and no way to audit or upgrade an existing skill. SkillArtisan closes all of these, while keeping the one thing `skill-creator` already does well — its evaluation and description-optimization engine — fully intact.

The design is grounded in the canonical, cross-vendor [agentskills.io](https://agentskills.io) specification (not just Claude-specific conventions), so skills built with SkillArtisan are portable across Claude Code, Cursor, GitHub Copilot, Codex, Gemini CLI, and 40+ other agent products by default.

## Install

```
claude plugin marketplace add <owner>/skill-artisan
claude plugin install skill-artisan
```

Requirements: Python 3.8+, [gitleaks](https://github.com/gitleaks/gitleaks) (for security scanning), `claude` CLI (for evaluation runs and description optimization).

## Quick start

Once installed, just ask Claude naturally:

```
"Create a skill that reviews pull requests for our team's style guide"
"Audit my existing invoice-parser skill against best practices"
"Benchmark this skill's trigger accuracy"
```

SkillArtisan's decision gate will first confirm a skill is actually the right tool (as opposed to CLAUDE.md, AGENTS.md, an MCP server, a subagent, or a plugin), check whether something already solves the request, then walk through authoring, validation, security scanning, and evaluation.

## What's different from `skill-creator`

| | `skill-creator` (Anthropic) | SkillArtisan |
|---|---|---|
| Frontmatter validation | None | Wraps the official `skills-ref` validator + Claude-specific checks |
| Naming guidance | None | Gerund-form enforcement, parent-directory matching |
| Decision gate | None — jumps straight to authoring | Skill vs. CLAUDE.md vs. AGENTS.md vs. MCP vs. subagent vs. plugin, plus a dedup/compose check |
| Security | "Don't build malware" (one line) | Gitleaks-based scan, pattern checks, content-hash tamper detection, AI semantic read-through |
| Surfaces covered | Claude Code, Claude.ai, Cowork | + Claude Tag, Messages API, generic cross-vendor |
| Multi-model testing | Not mentioned | Explicit Haiku/Sonnet/Opus pass |
| Existing-skill audit | Path-handling advice only | Full audit mode (`scripts/audit.py`): checklist scoring, upgrade-vs-rebuild decision, institutional-knowledge preservation, regression benchmarking, bulk mode |
| Lifecycle tracking | Not mentioned | Capability-uplift vs. encoded-preference classification with a scored timelessness threshold (`references/lifecycle.md`) |
| Eval engine | Strong — with/without-skill runs, description optimizer | Same engine, ported intact — this is the one thing kept unchanged |

See the full [Gap Table](../skill-artisan-master-spec.md#gap-table) (40 rows) for the complete comparison, including against other community tools (`daymade/claude-code-skills`, `tripleyak/SkillForge`).

## Architecture

SkillArtisan ships as a plugin, not a single skill, because its infrastructure genuinely needs more than one file:

```
skill-artisan/
├── .claude-plugin/plugin.json
├── creating-skills/          # the main skill — entry point, decision gate
│   ├── SKILL.md
│   └── references/
├── agents/                   # eval subagents (grader, comparator, analyzer)
├── eval-viewer/               # HTML review UI for benchmark results
├── assets/
├── scripts/                  # validation, security scanning, dedup search, eval loop, audit
├── LICENSE
├── CHANGELOG.md
├── .skillignore
└── README.md
```

Full rationale in the project's [master specification](../skill-artisan-master-spec.md).

## Release scope

SkillArtisan shipped in two deliberate stages, both now released:

- **v1** (`1.0.0`) — eval engine, decision gate, surface matrix, security scanning. A complete, usable tool on its own.
- **v2** (`2.0.0`) — lifecycle framing (capability-uplift vs. encoded-preference classification, `references/lifecycle.md`) and audit mode (`scripts/audit.py`: upgrade/rebuild existing skills, bulk mode across a whole skills directory, an optional additive-only contribution-plan mode for third-party repos). Shipped after v1 had been dogfooded on a real project skill, so the audit heuristics were informed by real usage (see `[1.0.1]` in the changelog) rather than designed in a vacuum.

The one thing v2 deliberately did not do: claim "best in market." That requires the master spec's full Best-in-Market Scorecard — a 12-20 skill benchmark corpus, four other comparison arms actually run, three axes scored separately — and that hasn't been run yet. See [CHANGELOG.md](./CHANGELOG.md) for what's shipped, what's deferred, and why.

## Security

Every skill produced or audited by SkillArtisan is scanned with [gitleaks](https://github.com/gitleaks/gitleaks) before packaging, plus pattern-based checks for absolute paths, exposed emails, insecure URLs, and dangerous code patterns (available via `--verbose`). A content-hash tamper-detection marker prevents shipping a skill that was edited after its last clean scan.

**Automated scanning has a ceiling.** Pattern-based tools cannot see everything — they're blind to non-English content, real names embedded in examples, or lines lifted from real transcripts, since none of that has a keyword to trigger on. Before publishing any skill publicly, read it yourself. A clean scan is a gate, not a guarantee. See `references/sanitization-checklist.md`.

## Credits

SkillArtisan's evaluation engine is ported from Anthropic's `skill-creator`. Its security scanning architecture, dedup/decision gate refinements, and several structural conventions are adapted from real prior art in this space — particularly [`daymade/claude-code-skills`](https://github.com/daymade/claude-code-skills) and [`tripleyak/SkillForge`](https://github.com/tripleyak/SkillForge) — with attribution preserved in the [Gap Table](../skill-artisan-master-spec.md#gap-table) row by row. This project exists because that prior art already fought many of these battles well; the goal was to synthesize the best of it against the canonical spec, not to claim originality it doesn't have.

## License

MIT — see [LICENSE](./LICENSE).
