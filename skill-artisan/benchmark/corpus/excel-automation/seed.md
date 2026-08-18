# Seed draft — excel-automation

This is the rough, blank-slate ask fed to every comparison arm's authoring workflow.
Every arm sees exactly this text and produces its own skill from it — nothing here should
be treated as an existing skill to copy from.

---

Every time I ask Claude to build me a polished Excel report, I end up re-explaining the
same three things from scratch: how to get openpyxl formatting to actually look
professional instead of default-ugly, how to pull data out of a giant `.xlsm` investment-
banking model that openpyxl either chokes on or silently mangles, and how to drive the
Excel window itself on my Mac (scroll to a cell, zoom, select a range) without the
AppleScript call hanging forever if Excel isn't responding.

I want this turned into something Claude can just reuse — a skill that knows: (1) when to
reach for openpyxl vs. when a file is complex enough that raw zipfile+XML parsing is the
only thing that actually works, (2) how to keep AppleScript calls from hanging (a timeout,
basically), and (3) what "professional formatting" actually means in openpyxl terms
(borders, number formats, header styling) rather than a bare data dump.

This should stay Mac-specific for the window-control piece — I'm not asking for
cross-platform Excel automation, just make sure that's stated rather than silently assumed.
