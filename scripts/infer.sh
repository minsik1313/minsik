#!/usr/bin/env bash
# 파인튜닝된 어댑터로 오디오 멀티모달 추론
# 사용법: bash scripts/infer.sh [어댑터경로]
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

ADAPTER="${1:-${ADAPTER:-outputs/qwen25omni-3b-qlora}}"
VAL_FILE="${VAL_FILE:-data/val.jsonl}"

# 최신 체크포인트 자동 탐색 (checkpoint-* 디렉터리)
if [ -d "$ADAPTER" ]; then
  latest_ckpt="$(find "$ADAPTER" -maxdepth 1 -type d -name 'checkpoint-*' | sort -V | tail -n1 || true)"
  if [ -n "${latest_ckpt:-}" ]; then
    ADAPTER="$latest_ckpt"
  fi
fi
echo "==> 어댑터: $ADAPTER"

# val 셋에 대해 배치 추론 → 결과 jsonl 저장
swift infer \
  --adapters "$ADAPTER" \
  --val_dataset "$VAL_FILE" \
  --max_new_tokens 128 \
  --temperature 0 \
  --result_path "outputs/infer_result.jsonl"

echo ""
echo "추론 결과: outputs/infer_result.jsonl"
echo "평가:      python scripts/eval.py --pred outputs/infer_result.jsonl"

# ──────────────────────────────────────────────────────────────
# LoRA를 베이스에 병합해 단일 모델로 내보내기(선택, 배포용):
#   swift export --adapters "$ADAPTER" --merge_lora true
# 대화형 단건 추론:
#   swift infer --adapters "$ADAPTER"   # 프롬프트에 <audio> 와 오디오 경로 입력
# ──────────────────────────────────────────────────────────────
