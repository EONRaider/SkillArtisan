#!/bin/bash
# Reproduces the three verified findings comparing SkillArtisan's row-15 eval
# engine against Anthropic's currently-shipped skill-creator (as of 2026-08-18).
# See skill-artisan-master-spec.md's Confidence Notes for the full writeup and
# skill-artisan/CHANGELOG.md's [2.2.2] entry for the fixes this documents.
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
echo "=== Done. Cross-check this output against the Confidence Notes writeup before citing in README. ==="
