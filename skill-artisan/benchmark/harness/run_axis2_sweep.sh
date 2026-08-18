#!/usr/bin/env bash
set -uo pipefail
cd /home/eonraider/Desktop/SkillArtisan/skill-artisan/benchmark/harness

declare -A names=(
  ["excel-automation/skill-creator"]="excel-automation"
  ["excel-automation/daymade-fork"]="excel-automation"
  ["excel-automation/skillforge"]="excel-automation"
  ["excel-automation/creating-skills"]="building-excel-reports"
  ["debugging-network-issues/skill-creator"]="debugging-network-issues"
  ["debugging-network-issues/daymade-fork"]="debugging-network-issues"
  ["debugging-network-issues/skillforge"]="debugging-network-issues"
  ["debugging-network-issues/creating-skills"]="debugging-network-issues"
  ["narrative-arc-builder/skill-creator"]="narrative-arc-builder"
  ["narrative-arc-builder/daymade-fork"]="narrative-arc-builder"
  ["narrative-arc-builder/skillforge"]="narrative-arc-builder"
  ["narrative-arc-builder/creating-skills"]="building-narrative-arcs"
)

for key in "${!names[@]}"; do
  skill="${key%/*}"
  arm="${key#*/}"
  target="${names[$key]}"
  outdir="workspace/$skill/$arm/audited/$target"
  triggers="../corpus/$skill/evals/trigger-evals.json"
  outfile="axis2-results/${skill}__${arm}.json"
  echo "=== $skill / $arm ($target) ===" >&2
  python3 axis2_trigger_scorer.py "$outdir" "$triggers" \
    --runs-per-query 1 --num-workers 1 --timeout 180 --model sonnet --json \
    > "$outfile" 2> "${outfile}.log"
  echo "$skill/$arm: exit=$? -> $outfile" >&2
done
echo "ALL DONE" >&2
