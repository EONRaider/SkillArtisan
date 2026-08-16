# SkillArtisan

This repo is the working home for **SkillArtisan** — a Claude Code plugin that supersedes Anthropic's shipped `skill-creator`. It contains both the source planning documents and the built plugin itself.

**→ For install instructions, usage, and what SkillArtisan actually does, see [`skill-artisan/README.md`](skill-artisan/README.md).** This root file is a map of the repo, not the plugin's own docs.

## Layout

```
.
├── skill-artisan/              # the plugin itself — install/run this
│   ├── creating-skills/        # the bundled skill (decision gate, SKILL.md)
│   ├── agents/ eval-viewer/ assets/ scripts/
│   └── README.md CHANGELOG.md LICENSE   # the live, canonical copies
├── .claude/skills/              # project-local skills for maintaining this repo
│   └── drafting-changelog-entries/   # dogfoods the plugin's own workflow
└── skill-artisan-master-spec.md      # design spec + 40-row Gap Table vs. skill-creator
```

`skill-artisan-master-spec.md` stays at the root because it documents the *build process* itself, not the plugin — there's no equivalent inside `skill-artisan/`. `README.md`, `CHANGELOG.md`, and `LICENSE` exist only inside `skill-artisan/`; root-level copies of those three were removed after they drifted out of sync with the real ones (the root `CHANGELOG.md` copy kept saying "nothing shipped yet" long after v1.0.1 had). One canonical copy each, no duplication to keep in sync.

Two more files existed at the root during earlier development and were deliberately removed, including from git history: `skill-artisan-TODO.md` (a pre-implementation research log, redundant with the master spec's own "Appendix: Research Provenance" section) and `skill-artisan-claude-code-prompt.md` (the two build prompts — Prompt A, already run for v1, and Prompt B, the not-yet-run v2 instructions). The prompt file is kept locally for running v2 later; it's git-ignored rather than tracked, since the project intentionally doesn't publish its own build prompts.

## Status

**v1.0.1** — Stages 1-4 of the master spec (eval engine, decision/dedup gate, five-surface matrix, security scanning) are built, verified against a live `claude -p` session and a real `gitleaks` install, and dogfooded on a real project skill. **v2** (lifecycle framing, audit mode) is scoped but not started — see [`skill-artisan/CHANGELOG.md`](skill-artisan/CHANGELOG.md) for what shipped and what's next, and the master spec's Gap Table for the row-by-row comparison against `skill-creator` and other prior art.

## License

MIT — see [`skill-artisan/LICENSE`](skill-artisan/LICENSE).
