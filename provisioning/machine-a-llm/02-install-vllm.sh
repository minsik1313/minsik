#!/usr/bin/env bash
# Machine A: Python 가상환경 + vLLM 설치 (OpenAI 호환 서버).
# 드라이버 설치(01) + 재부팅 후 실행.
set -euo pipefail

VENV_DIR="${VENV_DIR:-$HOME/.venvs/vllm}"

echo ">> Python venv: $VENV_DIR"
python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo ">> pip 업그레이드"
pip install --upgrade pip wheel

echo ">> vLLM 설치 (CUDA 빌드). Blackwell은 최신 vLLM 필요."
pip install --upgrade vllm

echo ">> 모델 다운로드 도구 (huggingface)"
pip install --upgrade "huggingface_hub[cli]"

echo ""
echo ">> 설치 확인:"
python -c "import vllm; print('vLLM', vllm.__version__)"
nvidia-smi --query-gpu=name,memory.total --format=csv

cat <<EOF

다음 단계:
  1) (선택) HF 토큰 로그인:  huggingface-cli login
  2) 모델 받기 예:           huggingface-cli download Qwen/Qwen2.5-Coder-32B-Instruct
  3) 서버 기동:              llm/serve/start-vllm.sh
가상환경 활성화는 'source $VENV_DIR/bin/activate'
EOF
