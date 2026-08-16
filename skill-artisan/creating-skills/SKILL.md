---
name: creating-skills
description: Create new Claude Skills from scratch, or validate, secure, and evaluate ones already drafted. Use when the user wants to build a skill, package a repeated workflow into something Claude can reuse, or asks whether something "should be a skill" — this runs a decision gate first (skill vs. CLAUDE.md vs. AGENTS.md vs. MCP vs. subagent vs. plugin) and checks whether something already covers the request before writing anything new. Also use for validating a SKILL.md's frontmatter, gerund naming, or portable-field compliance; scanning a skill for leaked secrets or unsafe patterns; benchmarking a skill's task-success rate with and without it enabled; or optimizing a description for triggering accuracy. Covers Claude Code, Claude.ai, Cowork, Claude Tag, and Messages API authoring, targeting the cross-vendor agentskills.io spec by default. Use even without the word "skill" — "turn this into something Claude can reuse", "why isn't my skill triggering", "is this safe to publish", "does this frontmatter look right".
license: MIT (see plugin root LICENSE)
compatibility: Claude Code, for the full workflow (subagents for parallel eval runs, Bash for scripts/). Claude.ai and Cowork work with reduced capability — see "Claude.ai-specific instructions" and "Cowork-specific instructions" below. Requires Python 3.10+, Node.js (npx, for the skills-ref validator), git, and gitleaks (github.com/gitleaks/gitleaks) for security scanning. The GitHub CLI (gh, authenticated) is required only for `audit.py pr-execute`'s real-effects path — everything else works without it.
---

# Creating Skills

Author, validate, secure, and evaluate Claude Skills — superseding Anthropic's shipped `skill-creator` with frontmatter validation, a combined decision/dedup gate, five-surface compatibility guidance, and gitleaks-based security scanning, while keeping `skill-creator`'s evaluation engine intact (it's the strongest thing about it).

**Before drafting anything, run the Decision Gate below.** Everything after it assumes the gate concluded "yes, build (or improve) a skill."

## The Decision Gate

Three sequential checks, in order. Don't skip ahead — a "yes, this is a skill" conclusion from check 1 doesn't make check 2 optional.

### 1. What kind of artifact is this?

Not every "make Claude do X automatically" request is a skill. Route to the right artifact before writing anything:

| If the request is... | Build this instead | Why |
|---|---|---|
| Always-true project context (build commands, conventions, architecture) that only needs to apply in Claude Code | **CLAUDE.md** | Always-on context doesn't need progressive disclosure or a trigger description — it should just always be there. |
| The same, but portability to non-Claude agents matters (Cursor, Copilot, Codex, etc.) | **AGENTS.md** | The cross-vendor equivalent of CLAUDE.md — an open convention (Agentic AI Foundation, Linux Foundation) used across 60,000+ repos and 20-30+ agent tools. If in doubt whether portability matters, ask; don't default to CLAUDE.md just because this is Claude Code. |
| Deterministic action tied to a lifecycle event ("every time I finish a session," "before any commit," "when a tool call matches X") | **Hook** (`settings.json`) | A skill's `description` is a trigger the model matches against — a hint, not a guarantee. If the request needs the action to fire every time regardless of whether the model judges it relevant, that's the harness executing something on an event, not a document loaded on match. Configure via the `update-config` skill. |
| Live data or a running service the model needs to query (a database, an internal API, real-time metrics) | **MCP server** | A skill is a document — instructions loaded on match. It cannot hold a live connection or expose callable tools the way an MCP server can. |
| A task that needs an isolated context so it doesn't pollute the main conversation (a large parallel search, a long research pass) | **Subagent** | Skills run in the same context on match (or a forked context via `context: fork` — see check 3). If true isolation is the point, that's a subagent, not a skill. |
| A design-system / visual-identity job specifically (colors, typography, spacing tokens) | **DESIGN.md** (Google Labs, Apache-2.0) | More portable home for design tokens than prose inside a SKILL.md body. |
| Packaging multiple skills, hooks, agents, and/or an MCP server together for distribution | **Plugin** | The distribution layer — which is what `SkillArtisan` itself is. A plugin bundles skills; it isn't one. |
| A specific, repeatable procedure with clear trigger conditions, that benefits from being loaded only when relevant | **Skill** ✓ | Continue to check 2. |

If the answer isn't clearly "skill," say so plainly and stop — don't build a skill-shaped wrapper around something that should be CLAUDE.md or an MCP server just because the user asked for "a skill" by name. Explain which artifact actually fits and why.

### 2. Does one already exist?

Before drafting, search for something that already solves this — an existing skill, an MCP server, or a plain tool. Run:

```bash
python <plugin-path>/scripts/dedup_search.py --query "<what the proposed skill would do, in the user's words>"
```

This surfaces candidates ranked by lexical overlap with the query — a **shortlist to review, not a verdict**. Read the full SKILL.md of anything scoring above noise before deciding. Then route on actual match confidence, not a vague three-way call:

| Confidence | Route | What that means concretely |
|---|---|---|
| **≥ 80%** | **Use existing** | It already handles this. Point the user at it; don't build anything. |
| **50–79%** | **Improve existing** | Close, but has a real gap. Extend the existing skill (see check 3 for inline-vs-fork on the addition) rather than starting over. |
| **< 50%** | **Create new** | No good match. Proceed to authoring. |
| **(distinct case)** | **Compose** | The request needs several capabilities, none of which any single existing skill covers, but two or three together would. Recommend chaining them rather than building one new monolithic skill that duplicates what already exists piecemeal. |

Compose is a real, distinct outcome — not a fallback dumped into "create new" when nothing scores high enough. If `dedup_search.py` surfaces two or three medium-scoring candidates that each cover a *different slice* of the request, that's a compose signal: say so explicitly, and propose the combination before proposing new work.

### 3. Inline or fork?

Once you know you're building or extending a skill, decide its execution architecture — whether its instructions run inline in the main conversation context, or fork into an isolated subagent context (`context: fork`, Claude Code only). This is a real decision with failure modes if chosen wrong, not just a field to fill in.

**Default to inline.** Most skills should run inline — the model needs the surrounding conversation context to do the task well (it's answering a question *about* the conversation, editing a file the user is actively discussing, etc.), and forking loses that.

**Fork when the skill's job is self-contained and verbose.** Good fork candidates:
- Produce a large intermediate artifact the main conversation doesn't need to see in full (e.g., a research pass that reads 40 files and returns a 3-paragraph summary)
- Would otherwise flood the main context with tool-call noise unrelated to the user's actual next question
- Are safe to run with less context than the full conversation — they only need the specific inputs the skill declares, not "everything discussed so far"

**Worked examples:**
- A skill that reformats the file the user just pasted → **inline**. It needs to see what's in the conversation.
- A skill that runs a 200-file codebase audit and returns a findings list → **fork**. The audit's own tool-call trail (every file it opened) is noise to the main conversation; only the findings matter.
- A skill that drafts a reply in the user's writing voice → **inline**. Voice-matching needs the actual conversational context, not just a topic.
- A skill that benchmarks another skill (this plugin's own eval engine) → **fork**, and in fact multiple forks in parallel — see "Testing and evaluating" below. Each with-skill/without-skill run needs a clean, isolated context specifically so results aren't contaminated by anything from prior turns.

Getting this wrong in either direction has a real cost: inline-when-it-should-fork buries the main conversation in irrelevant tool calls; fork-when-it-should-be-inline produces output that's technically correct but ignores context the user assumed was available.

---

## Authoring a new skill

Once the gate says "create new" (or "improve existing"):

1. **Capture intent.** If the current conversation already demonstrates the workflow (the user just did the thing manually and said "turn this into a skill"), extract the steps, corrections, and input/output formats from that transcript first — don't make the user re-explain what already happened. Otherwise ask: what should this enable, when should it trigger, what's the output format, and whether test cases make sense (skills with objectively verifiable output benefit from them; skills with subjective output like writing style often don't).
2. **Interview and research.** Ask about edge cases and dependencies before drafting. Check `scripts/dedup_search.py` results again if research turns up something new.
3. **Write the frontmatter.** See `references/frontmatter-spec.md` for the full field table and constraints. Keep the description pushy *and* imperative — list concrete trigger contexts explicitly, including ones that don't name the domain directly, **and** phrase it as "Use when..." — these are complementary techniques, not alternatives (see the frontmatter spec's worked example). Name it in gerund form (`creating-x`, `reviewing-x`) — `scripts/validate.py` checks this and suggests alternatives.
4. **Write the body.** Match instruction specificity to task fragility using the three degrees-of-freedom tiers in `references/writing-philosophy.md`, and scope the skill as one coherent unit of work (same file, separate section — it's a different check from degrees of freedom, don't conflate them). Imperative voice, explain the *why*, keep it lean. Bundle a script rather than let every invocation reinvent the same helper.
5. **Validate frontmatter and structure:**
   ```bash
   python <plugin-path>/scripts/validate.py <skill-path>
   ```
   Fixes name/description spec constraints, gerund naming, reserved words, and dangling path references before you invest in evals.
6. **Test and evaluate.** See below — this is where most of the real iteration happens.
7. **Security-scan before publishing.** See `references/security-checklist.md`.
8. **Package.** See "Packaging" below.

## Testing and evaluating

Build evals *before* extensive documentation: establish a baseline, write minimal instructions, iterate from there. Start with 2-3 test cases before expanding.

This section branches by surface — Claude Code has the full workflow; Claude.ai and Cowork each drop specific pieces (see the surface-specific sections near the end of this file). What follows is the Claude Code path.

### Running and evaluating test cases

Save test prompts (no assertions yet) to `evals/evals.json` — see `creating-skills/references/schemas.md` for the exact schema. Draft assertions once you've seen first-round outputs, not upfront; assertions written before seeing any output tend to check the wrong things.

**Spawn all runs — with-skill AND baseline — in the same turn**, each from a clean context. Don't spawn with-skill runs first and come back for baselines later; launch everything together so results land around the same time. For a new skill, baseline is "no skill at all, same prompt." For improving an existing skill, snapshot the current version first (`cp -r <skill> <workspace>/skill-snapshot/`) and baseline against that snapshot, not "no skill."

As each subagent completes, capture `total_tokens` and `duration_ms` from the task notification into `timing.json` immediately — this is the only opportunity to record it. Grade each run with `agents/grader.md` (writes `grading.json` — the viewer depends on the exact field names `text`/`passed`/`evidence`, not variants).

**Two ways to invoke the grader, depending on how this plugin is loaded.** If SkillArtisan is installed (`claude plugin install skill-artisan`, not just present as a repo being edited), `Task(subagent_type: "grader")` invokes it directly — same for `comparator` and `analyzer`. If you're developing SkillArtisan itself (this repo, open directly rather than installed), none of the three are registered as invocable subagent types — confirmed directly: installing the plugin locally mid-session does not make them available in that same session either, since the subagent-type registry is fixed at session start, the same pattern already documented for Claude Tag's skill discovery in `references/surface-matrix.md`. A fresh session started *after* install should pick them up, but that's the expected behavior per how plugin discovery works generally, not something re-confirmed inside this session's own tooling. In repo-context, follow `agents/grader.md`'s (and `comparator.md`'s/`analyzer.md`'s) documented process by hand instead — this is a proven, real fallback, not a workaround of last resort: it's how every eval run in this plugin's own build and regression-testing history was actually graded.

Then aggregate:

```bash
python <plugin-path>/scripts/eval_loop.py aggregate <workspace>/iteration-N \
  --skill-name <name> --skill-path <path> [--preset smoke|reliable|regression] [--ci --threshold 0.8]
```

Named presets (row 35, prior art: `skillgrade`) set how many runs per configuration to plan for — `--smoke` (5, quick sanity check during iteration), `--reliable` (15, pre-review confidence), `--regression` (30, high-confidence gate before release). `--ci --threshold` exits non-zero when the primary configuration's pass rate falls below the threshold, for gating a release pipeline rather than only interactive review.

Do an analyst pass (`agents/analyzer.md`'s "Analyzing Benchmark Results" section) for patterns aggregate stats hide — always-pass assertions (non-discriminating), always-fail assertions (broken or too hard), high-variance evals (possibly flaky).

**Launch the HTML viewer** — present results through this, not raw JSON:

```bash
python <plugin-path>/eval-viewer/generate_review.py <workspace>/iteration-N \
  --skill-name "<name>" --benchmark <workspace>/iteration-N/benchmark.json
```

Pass `--previous-workspace <workspace>/iteration-<N-1>` from iteration 2 onward for diffing. The viewer has Outputs and Benchmark tabs; feedback auto-saves to `feedback.json` in the workspace. Read it once the user says they're done, and focus improvements on test cases with specific complaints (empty feedback means "looked fine").

**Advanced: blind comparison.** For a rigorous "is the new version actually better" judgment, `agents/comparator.md` scores two outputs without knowing which skill produced which, and `agents/analyzer.md` explains why the winner won. Optional, needs subagents, most iterations don't need it — the human review loop usually suffices.

**Test across model sizes before calling a skill done.** A skill that works well on the model that authored it can still fail on a different one — Haiku needs more explicit, less-inferrable guidance; Sonnet needs clarity and efficiency; Opus needs the least hand-holding and can be actively hurt by over-explaining obvious steps. Run at least a smoke-preset pass (`--preset smoke`, above) with each of Haiku, Sonnet, and Opus as the executor model before considering a skill finished, not just the model that happened to be powering the authoring session.

**Pinning the executor model.** None of this plugin's own scripts do this for you — `eval_loop.py` only aggregates results someone else produced, and `description_optimizer.py`'s `--model` flag pins a `claude -p` CLI subprocess, not a Task-tool subagent spawn. The actual mechanism is the orchestrating session's own subagent-spawn tool: pass a `model` parameter (`haiku`/`sonnet`/`opus`) when launching each with-skill/without-skill executor for the smoke pass, once per model, so all three model passes are real, separately-run configurations rather than one run relabeled three times.

### Optional pre-flight: four-stage self-critique

Before committing to the full eval loop above, a cheap sanity check (prior art: `mgechev/skills-best-practices`) catches obvious problems in a handful of chat turns, no subagents required:

1. **Discovery** — paste just the frontmatter into a fresh context; ask for 3 should-trigger + 3 should-not-trigger prompts and whether the description is too broad.
2. **Logic** — feed the full SKILL.md + directory tree; have it simulate executing the skill against a specific request and flag "Execution Blockers" — points where it has to guess.
3. **Edge Case** — have it adversarially generate failure-state questions without fixing them.
4. **Architecture Refinement** — have it rewrite for progressive disclosure based on what surfaced.

Optional, not a Stage 2 requirement — use it when a quick gut-check is worth more than jumping straight to a full eval run.

### Description optimization

After the skill itself is in good shape, optimize the frontmatter description for triggering accuracy:

1. Generate ~20 eval queries: 8-10 should-trigger, 8-10 should-not-trigger. Should-trigger queries need real coverage — different phrasings, cases where the user doesn't name the skill's domain directly. Should-not-trigger queries need to be genuine near-misses (share vocabulary, need something different) — not obviously-irrelevant negatives; those test nothing.
2. Let the user review the set before running anything: read `assets/eval_review.html`, replace `__EVAL_DATA_PLACEHOLDER__`/`__SKILL_NAME_PLACEHOLDER__`/`__SKILL_DESCRIPTION_PLACEHOLDER__`, write to a temp file, open it. They can edit, toggle, add/remove, then export `eval_set.json`.
3. Run the optimizer:
   ```bash
   python <plugin-path>/scripts/description_optimizer.py run \
     --eval-set <eval_set.json> --skill-path <path> --model <model-id-powering-this-session>
   ```
   Uses a 60/40 train/validation split (shuffled once, fixed across iterations — not reshuffled each round), each query run 3x for a reliable trigger rate against a 0.5 threshold, up to 5 iterations, and selects the best iteration by **validation** pass rate, not train (avoids picking an iteration that overfit the queries it was tuned against). Opens a live HTML report that updates each iteration.
4. Apply `best_description` from the output to the skill's frontmatter. Show before/after and the scores.

This is Claude Code only — it shells out to `claude -p`, which doesn't exist on Claude.ai or Cowork. Skip it entirely on those surfaces (see below); there's no fallback, since the CLI is the only way to test against the model actually powering the session.

## Security

Before packaging or publishing, run the security scan and read `references/security-checklist.md` in full — automated scanning has a real ceiling (it's keyword-based; it cannot see non-English content or a real name embedded in an example). See that file and `references/sanitization-checklist.md` for what a scan can't catch and what to check by hand.

```bash
python <plugin-path>/scripts/security_scan.py <skill-path>            # default: gitleaks gate only
python <plugin-path>/scripts/security_scan.py <skill-path> --verbose  # + pattern checks, educational
```

## Lifecycle

Classify every skill you author or audit as **capability-uplift** (gives the model an ability it otherwise lacks — can go obsolete as base capability improves, needs periodic re-benchmarking) or **encoded-preference** (a fixed choice — house style, a specific workflow order — that doesn't age the same way), and score it 0-10 on **timelessness** (≥7 is the durable bar). See `references/lifecycle.md` for the full framing, the re-benchmarking triggers, and how this score feeds `scripts/audit.py`'s upgrade-vs-rebuild decision. Attach the classification directly to the skill body (or `metadata` frontmatter) rather than in a separate tracking document — `scripts/audit.py`'s `lifecycle-classified` checklist item looks for exactly this.

`creating-skills` classifies itself as a working example: **encoded-preference, timelessness 9/10, last verified against claude-sonnet-5 (2026-08).** Frontmatter constraints, the security-scan gate structure, the decision-gate routing logic, and the writing-philosophy rules are all fixed choices about how to build a skill well, not a capability gap a smarter model closes on its own — a future model still benefits from a validated frontmatter check and a gitleaks gate before publishing. The one component with any capability-uplift flavor is the eval engine's with/without-skill delta measurement, which is why the score sits at 9 rather than a flat 10 — see `references/lifecycle.md`'s worked example for the full reasoning.

## Auditing existing skills

Everything above is for authoring or improving a skill you're actively drafting. `scripts/audit.py` is for a skill that already exists — someone else's, `skill-creator` itself, or your own skill library — and needs a checklist-grounded read before deciding whether to touch it at all. Reuses the Stage 1-4 infrastructure above rather than duplicating it: it calls `validate.py` and `security_scan.py`'s functions directly and defers regression benchmarking to `eval_loop.py`, the same division of labor the eval engine itself uses (a standalone script can't spawn subagents; that's always this file's job).

1. **Audit report.** `python <plugin-path>/scripts/audit.py report <skill-path>` runs a checklist pass and prints a per-item PASS/FAIL/WARN/MANUAL report plus a pass-rate summary — never a bare binary verdict. Most items are checked mechanically (frontmatter validity, security-scan cleanliness, evals presence, body-size limits, reference depth); a few are marked `MANUAL` because no pattern can substitute for reading the skill (whether multi-model testing actually happened, whether the description optimizer was run, whether the coherent-unit-scoping test passes). Read those yourself before finalizing a verdict — don't report a checklist pass rate as if the MANUAL items don't count.
2. **Upgrade-vs-rebuild decision.** The script defaults to `upgrade-in-place` and only recommends `rebuild` when it finds a specific, named condition: both frontmatter validity and description quality failing together (triggering logic fundamentally broken, not just one structural gap), a capability-uplift skill scoring under 7/10 timelessness (pass `--timelessness N --lifecycle capability-uplift|encoded-preference` once you know the score — see `references/lifecycle.md`), or a body more than double the size limit (a proxy for "patching means rewriting most of it," verify by reading before trusting the proxy). State which branch was taken and why — the script already cites the specific findings; don't discard that when relaying the decision.
3. **Institutional-knowledge safeguard.** The report flags every `##` section heading in the skill's body that doesn't map to a known checklist area (security, evals, frontmatter, naming, and so on) — these are candidates for undocumented workarounds, domain quirks, or hard-won lessons the checklist has no slot for. Before rebuilding, read each flagged section and decide explicitly: keep it, fold it into the rebuilt version, or discard it on purpose. Never let a rebuild silently drop content the checklist didn't anticipate.
4. **Regression benchmarking.** Not run by `audit.py` itself. Snapshot the skill before changing anything (`cp -r <skill> <workspace>/pre-audit-snapshot/`), make the accepted changes, then run the same with/without (here, old-version/new-version) `eval_loop.py aggregate` workflow the Testing and evaluating section above describes. Only accept the change if it doesn't regress the pre-change pass rate — a checklist-compliance improvement alone isn't sufficient grounds to call it done.
5. **Bulk mode** (row 31). `python <plugin-path>/scripts/audit.py bulk <skills-dir>` runs the same report across every skill found under a directory (e.g. `~/.claude/skills/`) and prints a collective table — pass rate and decision per skill — rather than requiring one invocation per skill. Follow up with `report` on any individual skill that needs the full breakdown.
6. **Contribution planning and execution** (row 32, lower priority than 1-5). `python <plugin-path>/scripts/audit.py pr-plan <skill-path> --upstream-repo <owner/repo>` prints an additive-only-changes plan built from the audit's FAIL items — this command itself never forks, commits, or opens anything. This only applies to third-party repositories, never the user's own skills. Present the plan and get explicit confirmation before taking any of the steps it lists; a PR against a repo this plugin doesn't own changes the trust model, and that confirmation is required every time, not once per skill.

   Once the fixes are actually made — by you, applying the plan's FAIL-item fixes to a local clone of (a fork of) the upstream repo, the same way any other real fix gets made — `python <plugin-path>/scripts/audit.py pr-execute <clone-path> --upstream-repo <owner/repo> --skill-name <name> --dry-run` previews the branch/diff/PR with zero side effects. Only after that preview looks right, **and only after a separate, explicit confirmation from the user in this chat** (not implied by having approved the plan, not reusable across skills), rerun with `--execute` in place of `--dry-run` to actually fork, branch, commit, push, and open the PR. The script refuses outright (exit 4) if the change set includes any deletion or rename — additive-only is enforced mechanically, not left to discretion — and is idempotent: rerunning against a skill that already has an open PR returns that PR's URL rather than opening a duplicate. `--execute` has no prompt of its own and no auto-confirm flag; the confirmation gate is structural, sitting one layer up in this conversation, not inside the script.

## Packaging

```bash
python <plugin-path>/scripts/security_scan.py <skill-path> --package <output-dir>
```

Refuses to run if the skill has no clean security-scan marker, or if the marker's content hash doesn't match the skill's current contents (scanned, then edited, then packaged without rescanning — the marker system exists specifically to catch this). `.skillignore` at the plugin root documents what never gets packaged (see `references/security-checklist.md`).

## Surface coverage

Five surfaces plus the generic cross-vendor case — full detail, including exactly which frontmatter fields are safe on each, in `references/surface-matrix.md`. Read it before targeting anything other than plain Claude Code. The `compatibility` frontmatter field should reflect the target surface(s) explicitly rather than being left to prose.

## Claude.ai-specific instructions

No subagents, so no parallel with/without-skill runs. Run test cases one at a time, sequentially, using the skill's own instructions yourself. Skip baseline runs (just use the skill to complete the task) and skip quantitative benchmarking (it relies on baseline comparison). If you can't open a browser, present results directly in conversation instead of the HTML viewer — show the prompt and output per test case, save file outputs to disk with the path, ask for feedback inline. Skip description optimization entirely (needs `claude -p`, Claude Code only).

## Cowork-specific instructions

Subagents work, so the main workflow (parallel runs, grading) works too — fall back to sequential only if you hit severe timeouts. No browser or display: use `--static <path>` on `generate_review.py` to write a standalone HTML file, and share the path rather than opening it. **Generate the eval viewer before self-evaluating outputs**, not after — get results in front of the human as soon as they exist, don't sit on them while you form your own opinion first. Feedback has no running server to POST to, so `feedback.json` downloads instead; read it once you have access. Description optimization works (it shells out via subprocess, not a browser) but save it until the skill itself is in good shape and the user agrees — it's a tuning pass, not a substitute for getting the skill right first.

## Reference files

- `references/frontmatter-spec.md` — canonical field table, constraints, worked description example
- `references/surface-matrix.md` — five-surface + cross-vendor compatibility rules, extended Claude Code fields, the plugin-cache-vs-source-path gotcha
- `references/writing-philosophy.md` — imperative voice, explain-why, coherent-unit scoping, degrees of freedom, content hygiene
- `references/security-checklist.md` — full security model: gitleaks gate, pattern checks, tamper detection, third-party audit, AI semantic read-through
- `references/sanitization-checklist.md` — what pattern-based scanning structurally cannot catch, and what to check by hand before publishing
- `references/script-design.md` — conventions for anything placed in a skill's own `scripts/`
- `references/schemas.md` — JSON schemas for `evals.json`, `grading.json`, `benchmark.json`, and the rest of the eval engine's data formats
- `references/lifecycle.md` — capability-uplift vs. encoded-preference, the timelessness score, re-benchmarking triggers
- `agents/grader.md`, `agents/comparator.md`, `agents/analyzer.md` — subagent role instructions for the eval engine

Read these on demand — that's the point of progressive disclosure. Don't pre-load them into context before they're relevant to the task at hand.
