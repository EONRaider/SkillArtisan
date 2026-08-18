# Seed draft — debugging-network-issues

Rough, blank-slate ask fed to every comparison arm's authoring workflow.

---

Every time we hit a weird network/connection bug — a WebSocket that drops at some
suspiciously exact interval, an intermittent "connection reset" that a teammate wants to
fix by just restarting the service, a proxy/CDN issue where symptoms don't match the
obvious cause — I watch people (including me) jump straight to a guess and act on it. Then
it "gets fixed" by luck, and comes back three weeks later because nobody found the actual
root cause.

I want a skill that enforces slower, evidence-driven investigation for this class of bug:
demand a concrete artifact (a log line, a packet capture, a metric) before accepting any
theory, insist that a hypothesis be falsifiable and name what observation would rule it
out, and use layered isolation — testing the same request through paths that differ by one
hop at a time — instead of stacking assumptions. It should also know when a shortcut fix
("just restart it," "just bump the pool size") is masking a real problem rather than
solving it, and get a second opinion before committing to a root cause or shipping a fix.

This needs to generalize past pure networking too — connection-reset-style symptoms show
up in database pool exhaustion, job scheduling, and other places that aren't literally a
network stack, and the same evidence-over-assumption discipline should still apply there.
