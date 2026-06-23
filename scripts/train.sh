#!/usr/bin/env bash
# Qwen2.5-Omni-3B 오디오 멀티모달 QLoRA 파인튜닝
# 사용법: bash scripts/train.sh
# 8~12GB GPU 기준 기본값(QLoRA 4bit). 16GB 이상은 아래 16GB 섹션 참고.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

MODEL="${MODEL:-Qwen/Qwen2.5-Omni-3B}"
OUTPUT_DIR="${OUTPUT_DIR:-outputs/qwen25omni-3b-qlora}"
TRAIN_FILE="${TRAIN_FILE:-data/train.jsonl}"
VAL_FILE="${VAL_FILE:-data/val.jsonl}"
EPOCHS="${EPOCHS:-1}"
MAX_LENGTH="${MAX_LENGTH:-2048}"   # 오디오 시퀀스가 길면 OOM 회피 위해 축소
# dtype: Ampere+ 는 bfloat16 권장. Colab T4(Turing)는 bf16 미지원 → float16 주입.
#   예) TORCH_DTYPE=float16 COMPUTE_DTYPE=float16 bash scripts/train.sh
TORCH_DTYPE="${TORCH_DTYPE:-bfloat16}"
COMPUTE_DTYPE="${COMPUTE_DTYPE:-bfloat16}"

# 오디오 인코더(및 비전) freeze → 텍스트 백본 linear 레이어에만 LoRA
# 8~12GB: QLoRA(4bit). OOM 시 MAX_LENGTH/배치 더 줄이기.
swift sft \
  --model "$MODEL" \
  --dataset "$TRAIN_FILE" \
  --val_dataset "$VAL_FILE" \
  --train_type lora \
  --quant_method bnb \
  --quant_bits 4 \
  --bnb_4bit_compute_dtype "$COMPUTE_DTYPE" \
  --torch_dtype "$TORCH_DTYPE" \
  --target_modules all-linear \
  --freeze_vit true \
  --lora_rank 8 \
  --lora_alpha 16 \
  --lora_dropout 0.05 \
  --num_train_epochs "$EPOCHS" \
  --per_device_train_batch_size 1 \
  --gradient_accumulation_steps 16 \
  --gradient_checkpointing true \
  --learning_rate 1e-4 \
  --warmup_ratio 0.05 \
  --max_length "$MAX_LENGTH" \
  --eval_steps 50 \
  --save_steps 50 \
  --save_total_limit 2 \
  --logging_steps 5 \
  --dataloader_num_workers 2 \
  --output_dir "$OUTPUT_DIR"

echo ""
echo "학습 완료. 어댑터: $OUTPUT_DIR"
echo "추론:   bash scripts/infer.sh"

# ──────────────────────────────────────────────────────────────
# 16GB 이상 GPU: QLoRA 대신 LoRA(bf16) — 품질↑. 위 옵션에서 아래로 교체:
#   --quant_method 제거, --quant_bits 제거, --bnb_4bit_compute_dtype 제거
#   --per_device_train_batch_size 2  (여유 시)
# 오디오 출력(음성합성)까지 학습하려면 talker 모듈 별도 구성 필요 (1차 범위 외).
# ──────────────────────────────────────────────────────────────
