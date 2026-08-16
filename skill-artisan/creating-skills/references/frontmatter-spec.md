# Canonical Frontmatter Spec

The six fields portable across every agentskills.io-compliant client (Claude Code, Claude.ai, Cowork, the Messages API, and 40+ cross-vendor products). Extended Claude Code fields are a separate, opt-in layer — see `references/surface-matrix.md`; they hard-error on spec-only surfaces, so don't reach for them by default.

| Field | Required | Constraints |
|---|---|---|
| `name` | Yes | 1–64 chars. Lowercase unicode alphanumeric + hyphens only. No leading/trailing hyphen. No consecutive hyphens. Must match the parent directory name exactly. Gerund form (`creating-x`, not `x-creator`) is an official recommendation, not a hard constraint — `scripts/validate.py` warns, doesn't fail, on non-gerund names. |
| `description` | Yes | 1–1024 chars, non-empty, no angle brackets. Third person. Must cover both *what* the skill does and *when* to use it. |
| `license` | No | License name, or a short reference to a bundled license file. Keep it short — this isn't the place for full license text. |
| `compatibility` | No | Max 500 chars. Only include when the skill has real environment requirements: target surface(s), required system packages, network access needs. Most skills don't need this field at all — an empty `compatibility` is not a gap to fill in by default. |
| `metadata` | No | Arbitrary string-to-string map for client-specific properties the spec doesn't cover. Use distinctive key names to avoid collisions with another client's convention. |
| `allowed-tools` | No | Space-separated string of pre-approved tools. Experimental — support varies by client implementation; don't rely on it being enforced everywhere it's declared. |

## The description field, in full

This is the primary triggering mechanism — Claude decides whether to invoke a skill based on its name and description alone, before reading anything else. Two techniques, used *together*, not as alternatives:

1. **Imperative "Use when..." framing.** Write it as an instruction to the model, not a feature description. "Use when the user asks for X, mentions Y, or wants to Z" reads as a directive; "This skill does X" reads as documentation the model can take or leave.
2. **Pushy, explicit trigger-context listing.** Don't rely on the model inferring when a skill applies from a terse summary — spell out the contexts, including ones that don't name the domain directly. Real Claude Code models tend to *undertrigger* skills (fail to consult one that would help) more often than they overtrigger, so err toward being explicit rather than concise here.

Worked example — weak vs. strong, same skill:

> Weak: "How to build a simple fast dashboard to display internal data."

> Strong: "How to build a simple fast dashboard to display internal data. Make sure to use this skill whenever the user mentions dashboards, data visualization, internal metrics, or wants to display any kind of company data, even if they don't explicitly ask for a 'dashboard.'"

The second version is longer, more repetitive, and more effective — that's the tradeoff this field makes on purpose. `scripts/description_optimizer.py` (see the main SKILL.md's "Description optimization" section) fine-tunes this empirically once a draft exists; use the worked example above as the starting baseline before running it, not as a substitute for running it.

## Path references

Every relative markdown link or image target in the SKILL.md body (`[text](references/foo.md)`, `![alt](assets/bar.png)`) must resolve to a real file under the skill directory. `scripts/validate.py` checks this and fails with `Missing referenced files: X, Y` rather than shipping a dangling link — a broken reference silently degrades the skill for anyone who reaches it, since the model has no way to know the file was supposed to exist.
