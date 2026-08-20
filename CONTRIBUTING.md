# Contributing to SkillArtisan

Notes for anyone developing SkillArtisan itself, not just installing it — the repo's own layout, the plugin's internal architecture, and how to exercise the eval engine's subagents without a real install.

## Repo layout

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

## Plugin architecture

SkillArtisan ships as a plugin, not a single skill, because its infrastructure genuinely needs more than one file. `action.yml` at the repo root makes the audit installable as a GitHub Action in third-party repos too — see the root README's "GitHub Action" section.

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
├── benchmark/                 # regression/QA harness + corpus for testing creating-skills
│                              #   itself — development tooling, not part of the installed skill
├── LICENSE
├── CHANGELOG.md
├── .skillignore
└── README.md
```

Full rationale in the project's [master specification](skill-artisan-master-spec.md).

## Testing subagents locally

The eval engine's `grader`/`comparator`/`analyzer` subagents (`agents/*.md`) are only invocable via `Task(subagent_type: ...)` once the plugin is genuinely installed — installing it locally mid-session does not make them available in that same session, since Claude Code's subagent-type registry is fixed at session start. A repo-context session (this repo open directly, not installed) should follow each agent's documented process by hand instead — see `skill-artisan/creating-skills/SKILL.md`'s "Testing and evaluating" section.
