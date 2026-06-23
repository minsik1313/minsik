#!/usr/bin/env bash
# RTL 리그레션: 여러 랜덤 시드로 alu_tb 를 Slurm array 로 분산 실행.
#   eda/rtl/run-regression.sh [시드수]      (기본 32)
# Slurm 없이 로컬 병렬:  NO_SLURM=1 eda/rtl/run-regression.sh
set -euo pipefail

N="${1:-32}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${OUT:-/projects/rtl-regress/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT"
echo ">> RTL 리그레션 시드 1..$N → $OUT"

if [[ -n "${NO_SLURM:-}" ]] || ! command -v sbatch >/dev/null; then
  echo ">> 로컬 병렬 (GNU parallel)"
  seq 1 "$N" | parallel -j "$(nproc)" "$HERE/_sim_one.sh" "$HERE" "$OUT" {}
  echo ">> 요약"; grep -h -E "PASS|FAIL" "$OUT"/seed_*.log || true
else
  echo ">> Slurm array 제출 (파티션 sim)"
  sbatch --partition=sim --array=1-"$N" \
         --job-name=rtl-regress --output="$OUT/slurm-%a.log" \
         --wrap "$HERE/_sim_one.sh $HERE $OUT \$SLURM_ARRAY_TASK_ID"
  echo "   진행: squeue -n rtl-regress   결과요약: grep -h PASS\\|FAIL $OUT/seed_*.log"
fi
