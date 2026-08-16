# Changelog

All notable changes to SkillArtisan are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [Semantic Versioning](https://semver.org/), interpreted for this project as:

- **Major version bump (1.0.0 → 2.0.0)** marks a v-stage boundary, not just a breaking change — v1 → v2 is the deliberate release split (see the master spec's "Build Stages → Plugin Files → Release Scope"), not an accident of semver discipline.
- **Minor version** for new capability within a stage that doesn't break existing usage (e.g. adding cross-agent evaluation as an opt-in mode within v1).
- **Patch version** for fixes — corrected patterns, tightened validation, documentation accuracy.

## [Unreleased]

Nothing shipped yet. This file will be updated as Stages 1-4 (v1) and later Stages 5-6 (v2) are actually built and packaged — see the companion Claude Code prompts (`skill-artisan-claude-code-prompt.md`) for the build plan this will track against.

### Planned for 1.0.0 (v1)
- Eval engine ported from `skill-creator`: with/without-skill runs, grader/comparator/analyzer subagents, description optimizer, HTML eval-viewer
- Combined decision gate: skill vs. CLAUDE.md vs. AGENTS.md vs. MCP vs. subagent vs. plugin, plus a dedup check (use-existing / improve-existing / create-new / compose)
- Frontmatter validation wrapping the official `skills-ref` tool, plus Claude-specific checks
- Five-surface matrix: Claude Code, Claude.ai, Cowork, Claude Tag, Messages API, plus generic cross-vendor
- Security: gitleaks-based scan (default gate) + pattern-based checks (`--verbose` layer) + content-hash tamper detection + AI semantic read-through guidance
- Named eval trial presets (`--smoke`/`--reliable`/`--regression`) and CI gating

### Planned for 2.0.0 (v2)
- Lifecycle framing: capability-uplift vs. encoded-preference classification with a scored timelessness threshold
- Audit mode: score an existing skill against the full checklist, upgrade-vs-rebuild decision, institutional-knowledge preservation, regression benchmarking
- Bulk audit mode across an entire skills directory
- Optional: contribute-back / auto-PR mode for third-party skill repositories

---

*No versions have been released yet. Once Stage 1-4 (v1) is built and packaged, this section will be replaced with a dated `[1.0.0]` entry summarizing what actually shipped, and the "Planned" list above will move to "Added."*
