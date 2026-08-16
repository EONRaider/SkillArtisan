# Sanitization Checklist

The read-through guide for security layer 5 (`references/security-checklist.md`) — what to look for once the automated scans are clean, since a green scan only proves the *pattern-based* checks found nothing, not that nothing is there. Named with a hyphen to match this plugin's own reference-file convention (the equivalent file in `daymade/claude-code-skills` uses an underscore — that's their convention, not a portability requirement here).

Read every bundled file — SKILL.md, every `references/` file, every `scripts/` file, every example in `evals/` — and check each item below. This is a human read (or a careful LLM read acting on the author's behalf), not another automated pass; the entire point is to catch what pattern matching structurally cannot.

## What gitleaks and the pattern checks cannot see

- **Real names in a non-Latin script.** Gitleaks does not cover CJK. A real person's or project's name written in Chinese, Japanese, or Korean carries no keyword signature — it passes every automated layer clean regardless of how sensitive it actually is.
- **A real name in Latin script that isn't shaped like a secret.** "Contact Priya at the office" isn't a credential, a path, or a URL — none of the pattern checks fire on it, but it may still be information that shouldn't ship in a public skill.
- **Verbatim content lifted from a real session.** If a worked example was copy-pasted from an actual transcript rather than written as a synthetic illustration, it can carry real file paths, real data values, or real conversational content that happens not to match any of the specific patterns the scanner looks for (an absolute path pattern only catches `/home/[user]/`-shaped strings — a relative path, a company-internal hostname, or a project codename slips through untouched).
- **Business-sensitive detail with no secret shape.** An internal project codename, an unreleased product name, a specific customer's situation used as a worked example — none of this trips a credential or path pattern, but publishing it might not be something the author actually intended.

## Read-through pass

Work through the skill's files with these questions in mind, not as a rigid checklist to tick mechanically — the goal is genuine judgment about what would surprise the author if a stranger read it back to them:

1. **Every example and worked scenario** — is this synthetic, or was it lifted from a real session? If real, does it contain anything specific to a real person, company, or project that doesn't need to be there for the example to make its point?
2. **Every file path mentioned anywhere** — not just ones matching an absolute-path pattern. Does any path reveal something about the author's specific machine, employer, or project structure that a generic placeholder (`/path/to/project`, `~/example`) would serve just as well?
3. **Every name** — people, companies, internal tools, codenames. Is each one either genuinely necessary (a real public API's actual name) or should it be genericized?
4. **Every comment in bundled scripts** — comments sometimes carry context that never made it into the prose (a debugging note, a "TODO: ask Priya about the auth flow" left in from real development). These are exactly the kind of thing that has no pattern signature.
5. **Non-English content anywhere in the bundle** — read it, or have someone who can. Don't assume "the scanner would have caught it" — it structurally can't, for this specific category.
6. **Anything that would surprise the author.** The most reliable single test: if a stranger read this skill back to the author line by line, would anything make them wince or say "wait, I didn't mean to include that"? If you can't confidently answer no, look harder at that section specifically.

## When this applies

Every time, for the author's own skill, before the first public publish — not just for third-party review (that's `references/security-checklist.md`'s layer 4, a different threat model: adversarial instructions someone else wrote, not information the author didn't mean to include). A skill that's passed both the automated scan and this read-through has cleared what SkillArtisan can actually verify; it has not been certified by anyone but the person who did the reading.
