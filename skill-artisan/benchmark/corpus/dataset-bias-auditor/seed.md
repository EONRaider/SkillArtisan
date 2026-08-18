# Seed draft — dataset-bias-auditor

Rough, blank-slate ask fed to every comparison arm's authoring workflow.

---

I keep getting handed datasets, survey results, or "studies" where someone wants me to
draw a conclusion from them, and I want a second pair of eyes on the methodology before I
trust the number — not on whether the arithmetic is right, but on whether the way the data
was collected or compared actually supports the conclusion being drawn. The classic traps:
survivorship bias (only looking at the things that "made it," missing everything that
didn't), selection bias (the sample isn't representative of who it's claimed to represent),
confounding variables (correlation getting presented as causation when an obvious third
factor could explain both), measurement bias (the way something was measured
systematically favors one outcome), and self-selection in surveys (only people with strong
opinions bothered to respond).

I want a skill that reads a description of how a dataset/study/survey was put together and
flags which of these apply, explains concretely *why* the specific setup described creates
that risk (not a generic textbook definition), and — importantly — doesn't cry wolf on
every dataset. Plenty of studies are methodologically sound for what they claim; the skill
needs to actually distinguish a real methodology problem from a well-designed study, not
just list every possible bias reflexively.
