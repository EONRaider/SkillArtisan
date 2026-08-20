# SkillArtisan

[![GitHub release](https://img.shields.io/github/v/release/EONRaider/SkillArtisan)](https://github.com/EONRaider/SkillArtisan/releases/latest)

This repo is the working home for **SkillArtisan** — a Claude Code plugin that supersedes Anthropic's shipped `skill-creator`. It contains both the source planning documents and the built plugin itself.

**→ For install instructions, usage, and what SkillArtisan actually does, see [`skill-artisan/README.md`](skill-artisan/README.md).** This root file is a map of the repo, not the plugin's own docs.

## Layout

```
.
├── action.yml                   # GitHub Action definition — must live at repo root
├── .github/workflows/           # this repo's own self-test workflows for action.yml
├── skill-artisan/              # the plugin itself — install/run this
│   ├── creating-skills/        # the bundled skill (decision gate, SKILL.md)
│   ├── agents/ eval-viewer/ assets/ scripts/
│   ├── benchmark/               # regression/QA harness + corpus for testing
│   │                             #   creating-skills itself — not part of the installed skill
│   └── README.md CHANGELOG.md LICENSE   # the live, canonical plugin docs
├── .claude/skills/              # project-local skills for maintaining this repo
│   └── drafting-changelog-entries/   # dogfoods the plugin's own workflow
├── LICENSE                      # repo-root copy, required for GitHub license
│                                 #   detection and GitHub Marketplace publishing
└── skill-artisan-master-spec.md      # design spec + 40-row Gap Table vs. skill-creator
```

`skill-artisan-master-spec.md` stays at the root because it documents the *build process* itself, not the plugin — there's no equivalent inside `skill-artisan/`. `README.md` and `CHANGELOG.md` exist only inside `skill-artisan/` — one canonical copy each, not duplicated at root, since their content is versioned narrative that would drift. `LICENSE` is the one exception: it's duplicated at root *and* inside `skill-artisan/` on purpose — static boilerplate text with no drift risk, and GitHub's own tooling (license detection, GitHub Marketplace's publish-eligibility check) reads the repo-root copy specifically, while the `skill-artisan/` copy is what actually ships with the installed plugin.

## Status

**Current version: `2.4.2`** — see [`skill-artisan/CHANGELOG.md`](skill-artisan/CHANGELOG.md) for the full release history, and [`skill-artisan/README.md`](skill-artisan/README.md) for what SkillArtisan does.

## License

MIT — see [LICENSE](LICENSE).
