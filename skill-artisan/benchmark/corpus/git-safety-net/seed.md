# Seed draft — git-safety-net

Rough, blank-slate ask fed to every comparison arm's authoring workflow.

---

I want a skill for "did I just lose work" panic moments and for the cleanup that comes
after — recovering a commit/branch/stash that seems to have vanished, auditing what's
actually at risk before I delete anything, verifying something is really merged before I
remove the branch, and safely retiring old worktrees/clones/stashes once I'm sure nothing
is lost.

The thing that's burned me before: every git command I run is scoped to the one checkout
I'm sitting in. If I have a second, independent clone of the same repo sitting somewhere
else on disk with real work in it, `git branch -a` / `git stash list` / `git fsck` in this
checkout won't see any of it — a "clean" audit here can still mean real, unpushed work is
one `rm -rf` away in a sibling directory. I want the skill to actually go find every
checkout on the machine before it tells me anything is safe.

The other thing: "is this merged?" is genuinely harder to answer than it sounds. Commit
count is wrong after a squash-merge. I've heard even some of the smarter-looking content
checks (like a three-dot diff) can be wrong in specific ways. I want the actual right
answer here, not a check that merely looks more sophisticated than counting commits.

Recovery should never make things worse — anything destructive needs to be clearly called
out as destructive, separately from the read-only audit/recovery steps.
