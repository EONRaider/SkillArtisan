# Seed draft — bilibili-source

This is the rough, blank-slate ask fed to every comparison arm's authoring workflow.
Every arm sees exactly this text and produces its own skill from it.

---

I keep writing analysis pieces that reference Bilibili (B站) video performance — view
counts, likes, favorites, how the audience actually reacted in the comments — and every
time I either have to go paste the URL into a browser myself and copy numbers out by
hand, or Claude ends up estimating "probably a few thousand views" instead of an actual
number. That's not good enough for anything I'd cite.

I want a skill that fetches the real numbers: view/like/coin/favorite/share/reply counts,
the uploader's name and follower count, and — this matters as much as the raw numbers —
the danmaku (time-synced bullet comments), since that's the qualitative signal for *how*
people reacted, not just *how many* watched. It should accept whatever form someone
pastes: a full URL, a bare BVID, an old-style av number, or one of those b23.tv short
links. Subtitles would be nice too, but I understand those need my own Bilibili login to
access — that's fine, just ask first rather than trying silently.

The one rule that matters most: never hand-type or round a number as if it's real. If it
can't fetch something, say so — don't guess and present the guess as fact.
