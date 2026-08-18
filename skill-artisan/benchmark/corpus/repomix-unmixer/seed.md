# Seed draft — repomix-unmixer

Rough, blank-slate ask fed to every comparison arm's authoring workflow.

---

Someone sent me a repomix-packed file — sometimes it's XML, sometimes it's the Markdown
variant, occasionally JSON — and I want the original files back out as an actual
directory tree I can open in an editor, not just one giant blob I have to read top to
bottom. I want a skill that figures out which of the three formats the file is in, parses
it, and writes out every file to its original relative path, creating whatever parent
directories are needed. I'd also like to know it actually worked — how many files it
restored, not just silence-means-success.
