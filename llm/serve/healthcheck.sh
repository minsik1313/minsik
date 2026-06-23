#!/usr/bin/env bash
# LLM 엔드포인트 헬스체크 + 간단 생성 테스트.
set -euo pipefail
BASE="${BASE:-http://192.168.50.10:8000}"

echo ">> /v1/models"
curl -fsS "$BASE/v1/models" | python3 -m json.tool

echo ">> 생성 테스트"
curl -fsS "$BASE/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{
        "model": "minsik-coder",
        "messages": [{"role":"user","content":"Write a Verilog 2-input AND gate module."}],
        "max_tokens": 128
      }' | python3 -m json.tool
