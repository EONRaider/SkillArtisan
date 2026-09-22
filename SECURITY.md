# Security Policy

## Supported Versions

SkillArtisan is a single actively-developed line — there are no long-term
support branches. Security fixes are released against the latest version
only; users should stay current.

| Version   | Supported          |
| --------- | ------------------ |
| 2.11.x (latest) | :white_check_mark: |
| < 2.11    | :x:                |

## Reporting a Vulnerability

Report suspected vulnerabilities privately through GitHub's
[Security Advisories](https://github.com/EONRaider/SkillArtisan/security/advisories/new)
for this repository ("Report a vulnerability" under the Security tab).
Please do not open a public issue for security reports.

Include, where possible: the affected version/tag, a minimal reproduction
(a sample `SKILL.md` or plugin invocation is ideal), and the impact you'd
expect (e.g. arbitrary file write, secret exfiltration, command execution
during a scan or eval run).

You can expect an initial response within 5 business days. If the report
is accepted, we'll agree on a disclosure timeline with you and credit you
in the fix's release notes unless you prefer to stay anonymous; if
declined, we'll explain why. Fixes are shipped as a new patch/minor
release and tagged (`vX.Y.Z`); see
[`skill-artisan/CHANGELOG.md`](skill-artisan/CHANGELOG.md) for history.

## Scope

SkillArtisan generates and audits Claude Skills (`SKILL.md` files and
their supporting scripts/references) and ships as a Claude Code plugin
plus an optional GitHub Action. In scope:

- The plugin's own scripts (`skill-artisan/scripts/`), eval agents, and
  `action.yml`/workflow code.
- Security-scanning bypasses — e.g. a skill that should be flagged by the
  gitleaks/pattern checks or content-hash tamper-detection described in
  the [README](README.md#security) but isn't.
- Supply-chain issues in the plugin's own dependencies or install path.

Out of scope: vulnerabilities in skills *produced by* SkillArtisan that a
user then edits or publishes themselves — see
`references/sanitization-checklist.md` for the review responsibilities
that stay with the publisher after a clean scan.

## Known limitations and residual risk

Deliberate design limits, not undisclosed bugs — please don't report these
as new findings. Each one is a place where the safe behaviour depends on the
operator, or where a fix would cost more than the risk it removes.

### `scripts/pr_execute.py --execute` writes to real repositories

This is the one script in the plugin whose job is irreversible side effects:
it commits, force-pushes, and opens a pull request. Several things bound it
— it stages only the exact paths `--dry-run` printed rather than `git add
-A`, it refuses any change set containing a deletion or rename, it pushes
with `--force-with-lease` so a branch that moved underneath it is not
overwritten, and it has no `--yes` flag or interactive prompt that could
substitute for a human decision. What remains:

- **Untracked files are still additive.** `verify_additive_only` rejects
  deletions and renames; it does not reject a new file. A `.env` or a scratch
  file sitting in the clone is a legitimate-looking addition, and explicit
  staging means it is committed if it was there when the change set was
  inspected. **Read the `--dry-run` file list before passing `--execute`** —
  that list is exactly what will be published.
- **With push access, there is no fork.** When the authenticated account can
  already write to the target, the script pushes a branch directly to it
  rather than to a fork. That is intentional (forking your own repo fails),
  but it means `--execute` against a repo you own writes to that repo.
- **`--execute` is authorized one layer up.** The script cannot obtain
  consent itself. Outside the GitHub Action, every `--execute` needs a fresh
  human confirmation; see the module docstring for why that carve-out is
  scoped to the Action alone and must not be generalized to "this context is
  automated".

### `scripts/description_optimizer.py` spawns nested `claude -p`

The child runs with the host project's working directory and inherits the
environment, including credentials. It is given explicit permission flags —
tool execution and file writes denied, MCP servers not inherited, anything
that would prompt denied rather than auto-answered — so a child cannot act
on the machine. Two things are not fixed:

- **Indirect prompt injection.** Optimizing an existing skill's description
  means putting that skill's body into the child's prompt. If the skill is
  third-party, that body is untrusted text, and it can influence what the
  child writes back. The tool denials mean the worst case is a bad
  *description*, not a command being run — but **treat a proposed
  description for a skill you did not write as a suggestion to read, not
  output to accept unseen.**
- **The child inherits credentials.** `ANTHROPIC_API_KEY` and the
  authenticated session are exactly what the child needs to run at all, so
  they are not scrubbed.

The script also moves an already-installed skill of the same name aside for
the duration of an eval, so the real skill doesn't absorb triggers meant for
the candidate. That is now crash-safe: a sentinel file records the move, and
the next run restores anything an interrupted run left hidden. If both a
hidden copy and a reinstalled skill exist, the script leaves both alone and
says so rather than guessing which is current.

### The eval viewer serves on localhost

`eval-viewer/generate_review.py` runs an unauthenticated HTTP server bound
locally, with a `POST /api/feedback` endpoint that writes to the workspace.
Any process or user on the machine can reach it while it runs. Embedded eval
data is escaped so third-party content in a run's output cannot inject
script into the page, and the viewer will not terminate a process holding
its port that it cannot identify as one of its own earlier runs. The server
itself is still unauthenticated by design — it is a local review UI, not a
service. Don't run it on a shared or multi-user host.

### Pattern scanning is heuristic

`scripts/security_scan.py`'s pattern checks are regular expressions over
source text. They now match across whole files rather than single lines, so
a call split across lines is caught, and they cover the common execution and
deserialization sinks. They are still defeated by obfuscation, indirection
through a variable, or any language construct that doesn't look like the
pattern. The gitleaks tier and these checks raise the floor; they are not a
substitute for reading a skill you intend to publish. See
`references/sanitization-checklist.md`.

### The vendored validator's licence is self-contradictory upstream

`skills-ref@0.1.5`, vendored under `skill-artisan/vendor/skills-ref/`,
declares MIT in its `package.json` and ships Apache-2.0 licence text. This
is an upstream inconsistency we report rather than resolve — the vendored
files are kept byte-identical to what the registry publishes so they stay
verifiable. Details and the integrity hashes are in
[`skill-artisan/vendor/README.md`](skill-artisan/vendor/README.md).
