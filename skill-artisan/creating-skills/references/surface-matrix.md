# Surface Matrix

Five surfaces plus the generic cross-vendor case. Read the section for whatever you're targeting before writing frontmatter or teaching a workflow that assumes capabilities the surface doesn't have. `scripts/validate.py --suggest-compatibility <surfaces>` turns any combination of the surface names below into a ready-to-use `compatibility` field value.

## Table of Contents

- [Claude Code](#claude-code)
- [Claude.ai / Cowork](#claudeai--cowork)
- [Claude Tag](#claude-tag)
- [Messages API](#messages-api)
- [Generic cross-vendor](#generic-cross-vendor)
- [Choosing a target](#choosing-a-target)

## Claude Code

The full-capability surface: subagents, a browser (for the eval viewer), the `claude` CLI (for description optimization), and a real filesystem.

**Extended frontmatter fields**, on top of the six portable ones (`references/frontmatter-spec.md`). These are Claude Code-only — `scripts/validate.py` flags them as informational when present, since they'll hard-error on every other surface:

| Field | Purpose |
|---|---|
| `disable-model-invocation` | Skill is user-invocable only (e.g. via a slash command), never auto-triggered from a description match. |
| `user-invocable` | Explicitly controls whether a human can invoke the skill directly, independent of model auto-triggering. |
| `context: fork` | Runs the skill in an isolated subagent context rather than inline. See the main SKILL.md's "Inline or fork?" decision guide — this is the field that implements that decision. |
| `paths` | Restricts which project paths the skill's auto-triggering considers relevant (monorepo scoping). |
| `when_to_use` | A structured alternative/supplement to prose triggering guidance in `description`. |
| `argument-hint` | Autocomplete hint text when the skill is invoked as a slash command. |

**Directory-qualified nested skills**: in a monorepo, `apps/web:deploy` addresses a skill scoped to a specific subdirectory rather than the whole repo — useful when multiple subprojects have same-named but different skills (`apps/web:deploy` vs. `apps/api:deploy`).

**The cache-vs-source-path gotcha.** Installed plugin skills are cached at `~/.claude/plugins/cache/<marketplace>/<skill>/<version>/...` — this copy is read-only from the plugin's perspective and gets silently overwritten on the next update. **Before editing any Claude Code plugin skill, confirm the path you're about to edit does NOT contain `/cache/` or `/plugins/cache/`.** Always edit the source repository the plugin is built from; an edit to the cache path is real work that vanishes on the next `claude plugin update` with no warning that it happened.

## Claude.ai / Cowork

Six portable fields only — no extended Claude Code fields, they'll be ignored at best and rejected at worst depending on the client.

**Claude.ai** has no subagents and typically no CLI. The eval workflow adapts: sequential test-case execution (read the skill, follow it yourself, one case at a time), no baseline runs (baseline comparison needs the isolation subagents provide), no quantitative benchmarking, no description optimization (needs `claude -p`). If there's no browser, skip the HTML viewer and present results directly in the conversation instead.

**Cowork** has subagents (so parallel with/without-skill runs and grading work normally) but no browser or display. Use `eval-viewer/generate_review.py --static <path>` to write a standalone HTML file rather than starting a server, and share the resulting path. Description optimization still works — it shells out via `subprocess`, not a browser — but hold it until the skill itself is settled.

## Claude Tag

Same frontmatter format as Claude Code. Skills live in a git repository, one folder per plugin, and reach live channels only after a human merges a PR — there's no direct "push straight to production" path the way editing a local Claude Code skill has. Claude can self-improve a Claude Tag skill by opening a PR from what it learns in channel usage, but that PR still needs a human merge.

**Discovery is session-start-only**, at exactly `.claude/skills/<name>/SKILL.md`. A commit merged mid-session is not picked up until the next session starts — don't expect a just-merged change to be visible immediately in an already-running channel.

(This is also, empirically, the correct discovery path for registering a test skill during trigger evaluation in *any* Claude Code session, not just Claude Tag specifically — `scripts/description_optimizer.py` writes to `.claude/skills/<name>/SKILL.md` for exactly this reason, confirmed directly while building this plugin: `.claude/commands/<name>.md` registers as a slash command, not a skill, and never appears in `available_skills`.)

## Messages API

Skills run inside a code-execution container with **no network access and no runtime package installation**. Any package a bundled script needs must already be available in that container — declare it via `compatibility` so an author (or the container's builder) knows to pre-install it; there's no `pip install` fallback at runtime the way there is locally.

Custom skills **do not sync across surfaces**. A skill uploaded on claude.ai is not automatically available via the Messages API, and vice versa — each surface has its own upload/registration path.

## Generic cross-vendor

The default target, not a fallback for when nothing else applies — see the plugin's positioning: `creating-skills` produces spec-compliant output by default, with Claude-specific extensions as an opt-in layer selected per target, never assumed. Six portable fields only, and avoid instructions that silently assume a Claude Code-only capability (subagents, the `claude` CLI, `context: fork`) is available. If a skill needs to run on Cursor, GitHub Copilot, Gemini CLI, ChatGPT/Codex, or any other agentskills.io-compliant client, this is the profile to write for, and everything above is additive on top of it, not the other way around.

## Choosing a target

Most skills should target **Claude Code + generic cross-vendor** by default — write to the six-field baseline, and layer in Claude Code extensions only for the specific behaviors that need them (usually just `context: fork`, if anything). Reach for Claude Tag, Messages API, or Claude.ai-specific guidance only when there's a concrete reason the skill will actually run there — don't pad `compatibility` with every surface "just in case."
