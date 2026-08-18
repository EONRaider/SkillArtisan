#!/usr/bin/env bash
# Stage 1 pilot: re-score 3 low-trigger skills at --runs-per-query 3 to rule
# out single-run noise before treating them as real description problems.
set -uo pipefail
cd /home/eonraider/Desktop/SkillArtisan/skill-artisan/benchmark/harness

mkdir -p axis2-results/pilot-3x

for skill in fact-checker git-safety-net bilibili-source; do
  outdir="workspace/$skill/creating-skills/output"
  triggers="../corpus/$skill/evals/trigger-evals.json"
  outfile="axis2-results/pilot-3x/${skill}__creating-skills__3x.json"
  echo "=== $skill ($(date '+%H:%M:%S')) ===" >&2
  python3 axis2_trigger_scorer.py "$outdir" "$triggers" \
    --runs-per-query 3 --num-workers 1 --timeout 180 --model sonnet --json \
    > "$outfile" 2> "${outfile}.log"
  echo "$skill: exit=$? -> $outfile ($(date '+%H:%M:%S'))" >&2
done
echo "PILOT DONE" >&2
