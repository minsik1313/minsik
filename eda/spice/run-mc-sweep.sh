#!/usr/bin/env bash
# SPICE Monte Carlo / 코너 스윕을 Slurm array job 으로 분산.
# 각 array 태스크가 R/C 값을 난수 변동시켜 독립 ngspice 실행 → 임베러싱리 패러렐.
#
#   eda/spice/run-mc-sweep.sh [샘플수]     (기본 64)
# Slurm 없이 로컬 병렬로 돌리려면:  NO_SLURM=1 eda/spice/run-mc-sweep.sh
set -euo pipefail

N="${1:-64}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${OUT:-/projects/spice-mc/$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT"
echo ">> Monte Carlo N=$N → $OUT"

if [[ -n "${NO_SLURM:-}" ]] || ! command -v sbatch >/dev/null; then
  echo ">> 로컬 병렬 실행 (GNU parallel)"
  seq 1 "$N" | parallel -j "$(nproc)" "$HERE/_mc_one.sh" "$HERE/rc_lowpass.cir" "$OUT" {}
else
  echo ">> Slurm array 제출 (파티션 sim)"
  sbatch --partition=sim --array=1-"$N" \
         --job-name=spice-mc --output="$OUT/slurm-%a.log" \
         --wrap "$HERE/_mc_one.sh $HERE/rc_lowpass.cir $OUT \$SLURM_ARRAY_TASK_ID"
  echo "   진행상황: squeue -n spice-mc   결과: $OUT"
fi
