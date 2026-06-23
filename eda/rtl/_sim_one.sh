#!/usr/bin/env bash
# 단일 시드 RTL 시뮬: iverilog 컴파일 + vvp 실행.
# 인자: <rtl디렉터리> <출력디렉터리> <시드>
set -euo pipefail
RTL="$1"; OUTDIR="$2"; SEED="$3"

WORK="$OUTDIR/work_$SEED"
mkdir -p "$WORK"
iverilog -g2012 -DSEED="$SEED" \
  "$RTL/alu_tb.v" "$RTL/alu.v" -o "$WORK/sim"
vvp "$WORK/sim" > "$OUTDIR/seed_${SEED}.log" 2>&1
tail -1 "$OUTDIR/seed_${SEED}.log"
