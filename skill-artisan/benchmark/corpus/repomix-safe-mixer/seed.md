# Seed draft — repomix-safe-mixer

Rough, blank-slate ask fed to every comparison arm's authoring workflow.

---

I use repomix to pack up codebases into a single file — for sharing a reference copy
with a contractor, or bundling context for an LLM. Twice now I've caught myself about to
hand someone a packed file that still had a real API key or database URL baked into it
from a `.env`-style config file that got swept up in the pack. I want a skill that scans
for hardcoded credentials *before* packing, refuses to pack if it finds something, and
tells me exactly where (file and line) so I can go fix it. Once it's clean, it should go
ahead and do the actual repomix packing for me — I don't want a separate "now run repomix
yourself" step.

I know secret-scanning is inherently a bit trigger-happy on pattern matches — I'd rather
it over-flag with a line/file citation than under-flag, but it should distinguish "found a
pattern" from "confirmed this is a real leaked secret," since I've had scans point at
obvious placeholder text before.
