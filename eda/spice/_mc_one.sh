#!/usr/bin/env bash
# MC 단일 샘플: R/C 에 ±5% 가우시안 변동을 주어 ngspice 1회 실행.
# 인자: <회로파일> <출력디렉터리> <샘플인덱스>
set -euo pipefail
CIR="$1"; OUTDIR="$2"; IDX="$3"

# ±5% 변동 (awk 난수, 시드=인덱스로 재현성)
read -r RVAL CVAL < <(awk -v seed="$IDX" 'BEGIN{
  srand(seed);
  r=1000 *(1+0.05*(2*rand()-1));
  c=100e-9*(1+0.05*(2*rand()-1));
  printf "%g %g", r, c
}')

SIMOUT="$OUTDIR/sample_${IDX}.dat"
echo "[$IDX] R=$RVAL C=$CVAL"
ngspice -b \
  --define Rval="$RVAL" --define Cval="$CVAL" \
  --define simout="$SIMOUT" \
  "$CIR" > "$OUTDIR/sample_${IDX}.log" 2>&1
