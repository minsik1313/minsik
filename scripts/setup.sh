#!/usr/bin/env bash
# 로컬 오디오 멀티모달 파인튜닝 환경 셋업
# 사용법: bash scripts/setup.sh
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

VENV_DIR="${VENV_DIR:-.venv}"

echo "==> [1/5] Python 가상환경 생성: $VENV_DIR"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip

echo "==> [2/5] PyTorch 설치 확인"
# torch가 없으면 CUDA 12.1 빌드 설치 (환경에 맞게 index-url 조정 가능)
if ! python -c "import torch" 2>/dev/null; then
  echo "    torch 미설치 → CUDA 12.1 빌드 설치 시도"
  pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
fi

echo "==> [3/5] 의존성 설치 (requirements.txt)"
pip install -r requirements.txt

echo "==> [4/5] 설치 검증"
python - <<'PY'
import torch
print(f"  torch         : {torch.__version__}")
print(f"  CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"  GPU           : {torch.cuda.get_device_name(0)}")
    vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"  VRAM          : {vram:.1f} GB")
PY
echo "  swift version :"
swift --version || echo "  (swift CLI 확인 실패 - ms-swift 설치 점검 필요)"

echo "==> [5/5] 모델 메타데이터 다운로드 점검 (Qwen2.5-Omni-3B)"
echo "    실제 가중치는 학습/추론 시 자동 다운로드됩니다."
python - <<'PY'
try:
    from huggingface_hub import model_info
    info = model_info("Qwen/Qwen2.5-Omni-3B")
    print(f"  접근 OK: {info.modelId}")
except Exception as e:
    print(f"  (메타데이터 확인 건너뜀: {e})")
PY

echo ""
echo "셋업 완료. 다음 단계:"
echo "  source $VENV_DIR/bin/activate"
echo "  python scripts/prepare_data.py   # 샘플 데이터 생성"
echo "  bash scripts/train.sh            # 학습 smoke test"
