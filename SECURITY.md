# Security Policy

## Supported Versions

SkillArtisan is a single actively-developed line — there are no long-term
support branches. Security fixes are released against the latest version
only; users should stay current.

| Version   | Supported          |
| --------- | ------------------ |
| 2.5.x (latest) | :white_check_mark: |
| < 2.5     | :x:                |

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
