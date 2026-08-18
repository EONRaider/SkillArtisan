#!/usr/bin/env bash
# Step 2: Axis 2 trigger-accuracy scoring, single-arm (creating-skills only),
# across all 16 corpus skills. Reuses two results already produced during the
# abandoned multi-arm pilot (debugging-network-issues, excel-automation) and
# fills in the remaining 14.
set -uo pipefail
cd /home/eonraider/Desktop/SkillArtisan/skill-artisan/benchmark/harness

declare -A outdirs=(
  ["auto-repo-setup"]="workspace/auto-repo-setup/creating-skills/output"
  ["bilibili-source"]="workspace/bilibili-source/creating-skills/output"
  ["dataset-bias-auditor"]="workspace/dataset-bias-auditor/creating-skills/output"
  ["deep-research"]="workspace/deep-research/creating-skills/output"
  ["design-style-picker"]="workspace/design-style-picker/creating-skills/output"
  ["fact-checker"]="workspace/fact-checker/creating-skills/output"
  ["frontend-visual-qa"]="workspace/frontend-visual-qa/creating-skills/output/auditing-rendered-uis"
  ["github-sensitive-data-cleanup"]="workspace/github-sensitive-data-cleanup/creating-skills/output"
  ["git-safety-net"]="workspace/git-safety-net/creating-skills/output"
  ["narrative-arc-builder"]="workspace/narrative-arc-builder/creating-skills/output"
  ["repomix-safe-mixer"]="workspace/repomix-safe-mixer/creating-skills/output"
  ["repomix-unmixer"]="workspace/repomix-unmixer/creating-skills/output"
  ["structured-data-diff"]="workspace/structured-data-diff/creating-skills/output"
  ["ui-designer"]="workspace/ui-designer/creating-skills/output"
)

for skill in "${!outdirs[@]}"; do
  outdir="${outdirs[$skill]}"
  triggers="../corpus/$skill/evals/trigger-evals.json"
  outfile="axis2-results/${skill}__creating-skills.json"
  echo "=== $skill ($(date '+%H:%M:%S')) ===" >&2
  python3 axis2_trigger_scorer.py "$outdir" "$triggers" \
    --runs-per-query 1 --num-workers 1 --timeout 180 --model sonnet --json \
    > "$outfile" 2> "${outfile}.log"
  echo "$skill: exit=$? -> $outfile ($(date '+%H:%M:%S'))" >&2
done
echo "ALL DONE" >&2
