# SkillArtisan

A plugin for Claude Code that builds, validates, secures, and maintains Claude Skills — superseding Anthropic's shipped `skill-creator` with a spec-compliant, cross-vendor, security-hardened successor.

**→ Full documentation — why this exists, install instructions, and the GitHub Action — lives in the [repo root README](../README.md).** This file covers the plugin's positioning against `skill-creator` in more depth, plus quick reference for whoever's already installed it.

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
| Frontmatter validation | `scripts/quick_validate.py` exists (kebab-case, length limits, required fields) but is never referenced by `SKILL.md`'s own documented process — unused in practice | Wraps the official `skills-ref` validator + Claude-specific checks |
| Naming guidance | Same unused script covers kebab-case/hyphen rules; no gerund-form guidance anywhere | Gerund-form enforcement (warning, not a hard fail — `skills-ref` itself accepts non-gerund names), parent-directory matching |
| Decision gate | None — jumps straight to authoring | Skill vs. CLAUDE.md vs. AGENTS.md vs. MCP vs. subagent vs. plugin, plus a dedup/compose check |
| Security | "Don't build malware" (one line) | Gitleaks-based scan, pattern checks, content-hash tamper detection, AI semantic read-through |
| Surfaces covered | Claude Code, Claude.ai, Cowork | + Claude Tag, Messages API, generic cross-vendor |
| Multi-model testing | Not mentioned | Explicit Haiku/Sonnet/Opus pass |
| Existing-skill audit | Path-handling advice only | Full audit mode (`scripts/audit.py`): checklist scoring, upgrade-vs-rebuild decision, institutional-knowledge preservation, regression benchmarking, bulk mode |
| Lifecycle tracking | Not mentioned | Capability-uplift vs. encoded-preference classification with a scored timelessness threshold (`references/lifecycle.md`) |
| Eval engine | Strong — with/without-skill runs, description optimizer | Same architecture, ported wholesale rather than rebuilt — since hardened with five real bug fixes that regression testing found; no longer literally unchanged from the original port |

See the full [Gap Table](../skill-artisan-master-spec.md#gap-table) (40 rows) for the complete comparison, including against other community tools (`daymade/claude-code-skills`, `tripleyak/SkillForge`).

## Verified against `skill-creator`'s current source

Not a "best in market" claim — that requires the full Best-in-Market Scorecard (see the master spec), which hasn't run. Narrower and more concrete: the one piece of `skill-creator` this project kept "fully intact" — its evaluation/description-optimization engine, ported wholesale rather than rebuilt — turned out to need five real fixes that actual regression testing caught, not code review. All five were checked directly against Anthropic's own currently-shipped `skill-creator` source, and all five are present and unfixed there today. Full bug-by-bug writeup and a reproduction script: [`benchmark/VERIFIED-BUGS.md`](benchmark/VERIFIED-BUGS.md).

## Security

Every skill produced or audited by SkillArtisan is scanned with [gitleaks](https://github.com/gitleaks/gitleaks) before packaging, plus pattern-based checks for absolute paths, exposed emails, insecure URLs, and dangerous code patterns (available via `--verbose`). A content-hash tamper-detection marker prevents shipping a skill that was edited after its last clean scan.

**Automated scanning has a ceiling.** Pattern-based tools cannot see everything — they're blind to non-English content, real names embedded in examples, or lines lifted from real transcripts, since none of that has a keyword to trigger on. Before publishing any skill publicly, read it yourself. A clean scan is a gate, not a guarantee. See `references/sanitization-checklist.md`.

## License

MIT — see [LICENSE](./LICENSE).
