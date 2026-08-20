# SkillArtisan

[![GitHub release](https://img.shields.io/github/v/release/EONRaider/SkillArtisan)](https://github.com/EONRaider/SkillArtisan/releases/latest)

This repo is the working home for **SkillArtisan** — a Claude Code plugin that supersedes Anthropic's shipped `skill-creator`. It contains both the source planning documents and the built plugin itself.

**→ For install instructions, usage, and what SkillArtisan actually does, see [`skill-artisan/README.md`](skill-artisan/README.md).** This root file is a map of the repo, not the plugin's own docs.

## Layout

```
.
├── skill-artisan/              # the plugin itself — install/run this
│   ├── creating-skills/        # the bundled skill (decision gate, SKILL.md)
│   ├── agents/ eval-viewer/ assets/ scripts/
│   ├── benchmark/               # regression/QA harness + corpus for testing
│   │                             #   creating-skills itself — not part of the installed skill
│   └── README.md CHANGELOG.md LICENSE   # the live, canonical copies
├── .claude/skills/              # project-local skills for maintaining this repo
│   └── drafting-changelog-entries/   # dogfoods the plugin's own workflow
└── skill-artisan-master-spec.md      # design spec + 40-row Gap Table vs. skill-creator
```

`skill-artisan-master-spec.md` stays at the root because it documents the *build process* itself, not the plugin — there's no equivalent inside `skill-artisan/`. `README.md`, `CHANGELOG.md`, and `LICENSE` exist only inside `skill-artisan/` — one canonical copy each, not duplicated at root.

## Status

**Current version: `2.4.2`** — see [`skill-artisan/CHANGELOG.md`](skill-artisan/CHANGELOG.md) for the full release history, and [`skill-artisan/README.md`](skill-artisan/README.md) for what SkillArtisan does.

## License

MIT — see [`skill-artisan/LICENSE`](skill-artisan/LICENSE).
