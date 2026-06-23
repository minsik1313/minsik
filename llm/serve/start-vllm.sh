#!/usr/bin/env bash
# Machine A: vLLM OpenAI 호환 서버 기동.
# 기본 모델은 Qwen2.5-Coder-32B (코딩/RTL 보조 1순위).
# 환경변수로 모델/포트/텐서병렬 조정 가능.
set -euo pipefail

VENV_DIR="${VENV_DIR:-$HOME/.venvs/vllm}"
MODEL="${MODEL:-Qwen/Qwen2.5-Coder-32B-Instruct}"
PORT="${PORT:-8000}"
HOST="${HOST:-192.168.50.10}"     # 전용망에만 바인딩 (외부 노출 금지)
TP="${TP:-2}"                     # 텐서 병렬 = GPU 수
MAXLEN="${MAXLEN:-32768}"         # 컨텍스트 길이
GPU_UTIL="${GPU_UTIL:-0.92}"

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo ">> vLLM 서버 기동"
echo "   모델=$MODEL  TP=$TP  ${HOST}:${PORT}  ctx=$MAXLEN"
exec vllm serve "$MODEL" \
  --host "$HOST" \
  --port "$PORT" \
  --tensor-parallel-size "$TP" \
  --max-model-len "$MAXLEN" \
  --gpu-memory-utilization "$GPU_UTIL" \
  --served-model-name minsik-coder

# 70B 품질 우선 예 (64GB VRAM 4bit):
#   MODEL=Qwen/Qwen2.5-72B-Instruct-AWQ MAXLEN=16384 llm/serve/start-vllm.sh
