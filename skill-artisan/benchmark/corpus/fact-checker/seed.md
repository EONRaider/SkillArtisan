# Seed draft — fact-checker

Rough, blank-slate ask fed to every comparison arm's authoring workflow.

---

I write a lot of technical documentation and notes that reference things like model
specs, version numbers, pricing, and general statistics, and they go stale — an AI model's
context window gets superseded, a library's API changes, a statistic I cited two years ago
isn't current anymore. I want a skill that reads through a document, identifies the actual
verifiable factual claims (not opinions, not tutorial prose, not architecture discussion —
just the checkable stuff), searches official/authoritative sources for each one, and tells
me clearly whether each claim is accurate, outdated (was true, got superseded), incorrect,
or unverifiable, citing where it got the current answer from.

It should propose corrections with a clear rationale and source citation, and it should
ask before actually editing my document — I want to review the corrections, not have them
silently applied. And it needs to be honest when it can't find an authoritative source
rather than guessing and presenting the guess as verified.
