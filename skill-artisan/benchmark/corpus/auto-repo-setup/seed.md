# Seed draft — auto-repo-setup

Rough, blank-slate ask fed to every comparison arm's authoring workflow.

---

I want a skill that makes a repository "just work" for whoever's picking it up — a
collaborator onboarding, a fresh clone on a new machine, or me at the start of a session
wanting the latest remote changes — without inventing a special launcher or wizard every
time. It should figure out the actual stack from what's really there (lockfiles, manifests,
existing docs) rather than assuming Python/Node/whatever by default, and it should never
silently stash, merge, rebase, or discard my uncommitted work to make setup "look"
successful.

It also needs to handle the messier cases: diagnosing why a startup hook is firing more
than once instead of just re-registering it, safely handling commit/push/history-cleanup
requests without going straight to a destructive git command, and — only when it's
genuinely needed, not as a default — installing a lifecycle hook for behavior that has to
happen before the very first prompt. Ordinary "sync me up" requests shouldn't need a hook
at all; a hook is for when timing genuinely requires it.
