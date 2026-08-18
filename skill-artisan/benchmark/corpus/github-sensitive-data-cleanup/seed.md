# Seed draft — github-sensitive-data-cleanup

Rough, blank-slate ask fed to every comparison arm's authoring workflow.

---

I need a skill for the moment I realize a secret or private internal detail (an API key,
an internal domain, an internal IP, PII) made it into a Git repository's history — not
just the working tree, the actual history — and especially if that repo is public or about
to be pushed publicly. I want it to: scan first and show me exactly what it found before
touching anything, always create a real backup before rewriting anything, verify repo
visibility before any push rather than guessing from the URL, never use `--no-verify` to
bypass a safety hook, and re-verify after rewriting rather than trusting a clean `git log`
at face value.

The one thing I really don't want is a shortcut: if a *live* credential got exposed,
rewriting history doesn't invalidate it — that has to get rotated regardless of whether
the history gets cleaned. And if a public repo has forks, cleaning my copy's history
doesn't remove it from those forks, so that needs to be called out explicitly, not glossed
over.
