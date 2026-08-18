# Seed draft — design-style-picker

Rough, blank-slate ask fed to every comparison arm's authoring workflow.

---

I keep getting stuck at the "I don't know what I want it to look like, but I'll know it
when I see it" stage of a design decision. I don't want to be asked to describe an
abstract style in words — I already can't. I want a skill that generates a real batch of
visibly different options along at least a couple of axes (say, color intensity as one
axis and layout/organization strategy as another), so I can point at the ones that are
close and the ones that are wrong, rather than staring at a blank prompt trying to
articulate "modern but not too corporate."

It should look at whatever I already have — existing screenshots, design tokens, brand
colors — before generating anything, and treat that as the starting vocabulary rather than
proposing something unrelated. It should actually look at what it generated itself before
showing it to me, so I'm not wading through five near-identical variants. And when I do
pick, it should implement from the *principles* in what I picked (color roles, density,
hierarchy) rather than literally trying to reproduce pixels from a generated reference
image.
