#!/bin/bash
# Reproduces the four verified findings comparing SkillArtisan's row-15 eval
# engine against Anthropic's currently-shipped skill-creator (as of 2026-08-18).
# See skill-artisan-master-spec.md's Confidence Notes for the full writeup and
# skill-artisan/CHANGELOG.md's [2.2.2] and [2.2.3] entries for the fixes this
# documents.
#
# Run this again before any README "best in market" / comparison claim to
# reconfirm skill-creator hasn't since fixed these — do not cite the findings
# below as current without re-running this first.
#
# Usage: bash skill-creator-comparison-repro.sh
set -euo pipefail

SC="$HOME/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator/scripts"
SA_EVAL_LOOP="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/eval_loop.py"

if [ ! -d "$SC" ]; then
  echo "skill-creator not found locally at: $SC"
  echo "This script requires the official skill-creator plugin installed via the"
  echo "claude-plugins-official marketplace. Install it, or point \$SC at a checkout"
  echo "of https://github.com/anthropics/skills (or wherever it's canonically hosted)"
  echo "before re-running."
  exit 1
fi

echo "=== skill-creator source freshness ==="
stat -c '%y  %n' "$SC"/run_eval.py "$SC"/aggregate_benchmark.py
echo "(compare this date against today before trusting the findings below)"
echo

echo "=== Finding 1: premature-return trigger-detection bug in run_eval.py ==="
echo "Expect to see 'return False' / 'return triggered' BEFORE the 'result' event branch:"
grep -n "return False\|return triggered\|elif event.get(\"type\") == \"result\"" "$SC/run_eval.py"
echo

echo "=== Finding 2: timeout defaults in run_eval.py / run_loop.py ==="
echo "Expect --timeout default=30 in both (SkillArtisan fixed its equivalent to 180):"
grep -n 'timeout.*default=30\|default=30.*timeout' "$SC/run_eval.py" "$SC/run_loop.py"
echo

echo "=== Finding 3: None-vs-missing-key crash in aggregate_benchmark.py, live reproduction ==="
TMPDIR=$(mktemp -d)
mkdir -p "$TMPDIR/bench/eval-1/with_skill/run-1"
cat > "$TMPDIR/bench/eval-1/with_skill/run-1/grading.json" << 'EOF'
{"summary": {"pass_rate": 0.5, "passed": 1, "failed": 1, "total": 2}, "timing": null, "execution_metrics": null, "expectations": []}
EOF

echo "--- skill-creator's aggregate_benchmark.py on a grading.json with explicit null timing/metrics ---"
echo "(this exact pattern — explicit null, not a missing key — is what SkillArtisan's own"
echo " graders wrote whenever timing/metrics data was genuinely unrecoverable, confirmed"
echo " during this project's own 25-run regression test)"
if python3 "$SC/aggregate_benchmark.py" "$TMPDIR/bench" --skill-name test > /tmp/sc_out.log 2>&1; then
  echo "UNEXPECTED: skill-creator did NOT crash. Re-check whether this bug has been fixed upstream."
  cat /tmp/sc_out.log
else
  echo "CONFIRMED CRASH (expected):"
  tail -5 /tmp/sc_out.log
fi
echo

echo "--- SkillArtisan's eval_loop.py on the identical fixture ---"
if python3 "$SA_EVAL_LOOP" aggregate "$TMPDIR/bench" --skill-name test > /tmp/sa_out.log 2>&1; then
  echo "CONFIRMED CLEAN (expected):"
  cat /tmp/sa_out.log
else
  echo "UNEXPECTED: SkillArtisan's eval_loop.py crashed too. This needs investigation before citing the finding."
  cat /tmp/sa_out.log
fi

rm -rf "$TMPDIR" /tmp/sc_out.log /tmp/sa_out.log
echo

echo "=== Finding 4: non-atomic skill-directory publish race in run_eval.py's run_single_query() ==="
echo "Expect to see mkdir() and write_text() as two separate calls, with real work in between"
echo "(a wider window than SkillArtisan's pre-2.2.3 version had even before it was fixed):"
grep -n "mkdir(parents=True\|write_text(command_content\|command_file = " "$SC/run_eval.py"
echo
echo "This matters because every concurrent claude -p worker scans this same shared"
echo ".claude/commands/ (skill-creator) / .claude/skills/ (SkillArtisan) directory at"
echo "startup — a scan landing between mkdir() and write_text() can observe a broken entry."
echo "SkillArtisan fixed its equivalent (description_optimizer.py's run_single_query) in 2.2.3"
echo "by building the entry in a hidden staging dir and publishing/tearing it down with a"
echo "single os.rename(), which is atomic on the same filesystem. skill-creator's run_eval.py"
echo "still uses the two-call mkdir()+write_text() sequence shown above."
echo
echo "--- Live mechanism reproduction (no claude -p calls — pure filesystem race) ---"
echo "Reimplements each codebase's actual publish sequence verbatim (skill-creator's"
echo "mkdir()+write_text() from run_eval.py above; SkillArtisan's staging+os.rename() from"
echo "description_optimizer.py's run_single_query), hammers each with concurrent writers, and"
echo "has a scanner mimic a discovery pass (list .claude/<dir>/, require each entry to have a"
echo "complete, parseable file) to see how often it lands on a broken entry. A deliberate delay"
echo "is forced into each approach's equivalent vulnerable window so the race is reproducible"
echo "in a fast local run rather than needing real claude -p timing jitter to sometimes land in"
echo "a normally sub-millisecond gap — this changes how OFTEN the window is hit, not WHETHER"
echo "one exists structurally (os.rename() has no such window at all, at any delay)."
python3 - << 'PYEOF'
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path

N_WORKERS = 12
N_ROUNDS = 30
INJECTED_DELAY = 0.01
DESC = "x" * 300


def skill_creator_publish(root: Path, name: str):
    # Mirrors run_eval.py's run_single_query(): mkdir() then a separate
    # write_text() against the shared commands/skills directory.
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    time.sleep(INJECTED_DELAY)  # the actual vulnerable window in that code
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: |\n  {DESC}\n---\n\nbody\n")
    return d


def skill_creator_teardown(d: Path, root: Path, name: str):
    # skill-creator's run_single_query() cleans up with a plain unlink() —
    # same non-atomic shape as its publish. Mirrored here for a fair,
    # symmetric comparison (SkillArtisan's teardown got the same 2.2.3 fix
    # its publish did, see below).
    if (d / "SKILL.md").exists():
        (d / "SKILL.md").unlink()
    try:
        d.rmdir()
    except OSError:
        pass


def skillartisan_publish(root: Path, name: str):
    # Mirrors description_optimizer.py's run_single_query() post-2.2.3:
    # build in a hidden staging dir, publish with one atomic os.rename().
    staging = root / f".{name}.staging-{threading.get_ident()}"
    staging.mkdir(parents=True, exist_ok=True)
    (staging / "SKILL.md").write_text(f"---\nname: {name}\ndescription: |\n  {DESC}\n---\n\nbody\n")
    time.sleep(INJECTED_DELAY)  # equivalent point: content complete, not yet published
    d = root / name
    os.rename(staging, d)
    return d


def skillartisan_teardown(d: Path, root: Path, name: str):
    # Mirrors description_optimizer.py's run_single_query() finally block
    # post-2.2.3: rename out of the shared directory (atomic) before
    # removing, so a listing never catches a mid-deletion entry either.
    if d.exists():
        torn_down = root / f".{name}.torndown-{threading.get_ident()}"
        try:
            os.rename(d, torn_down)
        except OSError:
            return
        shutil.rmtree(torn_down, ignore_errors=True)


def worker(root, publish, teardown, worker_id, stop_event):
    for i in range(N_ROUNDS):
        name = f"skill-w{worker_id}-{i}-{os.urandom(3).hex()}"
        d = publish(root, name)
        teardown(d, root, name)
    stop_event.set()


def scan(root: Path):
    seen = broken = 0
    try:
        entries = list(root.iterdir())
    except FileNotFoundError:
        return 0, 0
    for e in entries:
        if e.name.startswith(".") or not e.is_dir():
            continue
        seen += 1
        f = e / "SKILL.md"
        if not f.exists():
            broken += 1
            continue
        try:
            content = f.read_text()
            if "---" not in content or "description:" not in content:
                broken += 1
        except OSError:
            broken += 1
    return seen, broken


def run(label, publish, teardown):
    root = Path(tempfile.mkdtemp(prefix=f"sc-repro-{label}-"))
    stop_events = [threading.Event() for _ in range(N_WORKERS)]
    threads = [
        threading.Thread(target=worker, args=(root, publish, teardown, i, stop_events[i]))
        for i in range(N_WORKERS)
    ]
    total_seen = total_broken = 0
    for t in threads:
        t.start()
    while not all(e.is_set() for e in stop_events):
        seen, broken = scan(root)
        total_seen += seen
        total_broken += broken
        time.sleep(0.001)
    for t in threads:
        t.join()
    shutil.rmtree(root, ignore_errors=True)
    pct = (100 * total_broken / total_seen) if total_seen else 0.0
    print(f"{label}: {total_broken}/{total_seen} scans caught a broken entry ({pct:.1f}%)")


run("skill-creator (mkdir+write_text)", skill_creator_publish, skill_creator_teardown)
run("SkillArtisan (staging+os.rename)", skillartisan_publish, skillartisan_teardown)
PYEOF
echo

echo "=== Done. Cross-check this output against the Confidence Notes writeup before citing in README. ==="
