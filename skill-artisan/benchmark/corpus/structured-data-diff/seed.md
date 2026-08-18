# Seed draft — structured-data-diff

Rough, blank-slate ask fed to every comparison arm's authoring workflow.

---

I keep getting two versions of the same structured data — a CSV export from last week and
one from this week, or two JSON API responses — and I need to know what actually changed
between them. Not a raw line-by-line text diff (that's useless once rows get reordered or
a column gets added in the middle), but a real structured comparison: which rows were
added, which were removed, which existing rows had a field change, and what that field
change actually was.

The tricky part is telling a *real* change from noise: rows coming back in a different
order isn't a change if the same data is still there; `42` and `"42"` probably shouldn't
count as different unless I ask for strict type checking; and `19.999999999` vs `20.0` is
floating-point rounding noise, not a real edit. I also need it to match rows up by an
actual identifying column (like an `id` or `sku`), not by row position, since a single
inserted row would otherwise make every row after it look "changed."

Output should be something a human can actually read — categorized additions/removals/
modifications, not a giant unified diff blob.
