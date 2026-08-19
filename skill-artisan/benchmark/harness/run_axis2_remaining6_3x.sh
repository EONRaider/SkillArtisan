#!/usr/bin/env bash
# Stage 1 (3x re-verification) on the 6 remaining low-trigger-rate skills not
# covered by the earlier 3-skill pilot. Sequential, single-worker, per the
# established concurrency-safety finding.
set -uo pipefail
cd /home/eonraider/Desktop/SkillArtisan/skill-artisan/benchmark/harness

mkdir -p axis2-results/pilot-3x

for skill in dataset-bias-auditor deep-research excel-automation narrative-arc-builder repomix-unmixer structured-data-diff; do
  outdir="workspace/$skill/creating-skills/output"
  triggers="../corpus/$skill/evals/trigger-evals.json"
  outfile="axis2-results/pilot-3x/${skill}__creating-skills__3x.json"
  echo "=== $skill ($(date '+%H:%M:%S')) ===" >&2
  python3 axis2_trigger_scorer.py "$outdir" "$triggers" \
    --runs-per-query 3 --num-workers 1 --timeout 180 --model sonnet --json \
    > "$outfile" 2> "${outfile}.log"
  echo "$skill: exit=$? -> $outfile ($(date '+%H:%M:%S'))" >&2
done
echo "REMAINING6 DONE" >&2
