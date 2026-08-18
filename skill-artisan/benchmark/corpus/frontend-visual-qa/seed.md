# Seed draft — frontend-visual-qa

Rough, blank-slate ask fed to every comparison arm's authoring workflow.

---

I want a skill for auditing a UI that's already been built and rendered — not designing
one from scratch, auditing what's actually there. The core discipline I want enforced:
treat a build succeeding, or the DOM merely containing the right elements, as weak
evidence — the only thing that counts as proof is actually looking at the rendered result,
whether that's a real browser, a screenshot, or a static image someone hands me.

It needs to handle a bunch of specific traps I keep running into: a transient error toast
that flashes and vanishes before a screenshot can catch it (so "I didn't see it" isn't the
same as "it didn't happen"); comparing a page against a reference design and actually
measuring the gap instead of a vague "looks worse"; a UI where clicking between views
changes the visible content but never updates the URL, so refresh/deep-link/back-button
all silently break; lazy-loaded images below the fold that look "broken" in a screenshot
but are actually just not-yet-triggered, versus ones that are genuinely broken; and a
static screenshot review that should stick to what's actually visible in the image rather
than inventing claims about DOM structure or interactive behavior a still image can't
prove.

Default to audit-only — it shouldn't start editing implementation, installing
dependencies, or "fixing" things unless I explicitly ask it to change something, and it
should be honest when some piece of evidence (a real browser, a working test driver)
just isn't available rather than claiming to have verified something it didn't.
