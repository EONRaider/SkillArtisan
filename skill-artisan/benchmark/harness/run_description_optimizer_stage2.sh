#!/usr/bin/env bash
# Stage 2: run the iterative improve-description loop against the corpus
# skills confirmed (not noise) to have poor Axis-2 trigger rates. Sequential
# on purpose -- even at --num-workers 1 each, two concurrent script
# invocations would still contend for the same claude -p resources.
set -uo pipefail
cd /home/eonraider/Desktop/SkillArtisan/skill-artisan

mkdir -p benchmark/harness/axis2-results/description-optimizer

for skill in fact-checker bilibili-source; do
  outdir="benchmark/harness/axis2-results/description-optimizer/$skill"
  mkdir -p "$outdir"
  echo "=== $skill ($(date '+%H:%M:%S')) ===" >&2
  python3 scripts/description_optimizer.py run \
    --eval-set "benchmark/corpus/$skill/evals/trigger-evals.json" \
    --skill-path "benchmark/harness/workspace/$skill/creating-skills/output" \
    --num-workers 1 --timeout 180 --model sonnet --verbose \
    --report none --no-browser \
    --results-dir "$outdir" \
    > "$outdir/stdout.json" 2> "$outdir/stderr.log"
  echo "$skill: exit=$? ($(date '+%H:%M:%S'))" >&2
done
echo "STAGE2 DONE" >&2
