# 클라이언트 연동 — B에서 A의 로컬 LLM 사용

A의 vLLM 은 OpenAI 호환 API (`http://192.168.50.10:8000/v1`, 모델명 `minsik-coder`).

## aider (CLI 코딩 어시스턴트)

```bash
pip install aider-chat
export OPENAI_API_BASE=http://192.168.50.10:8000/v1
export OPENAI_API_KEY=dummy            # vLLM 기본은 인증 없음 (전용망 한정)
aider --model openai/minsik-coder
```

## continue.dev (VS Code 확장)

`~/.continue/config.json`:
```json
{
  "models": [
    {
      "title": "minsik-coder (local)",
      "provider": "openai",
      "model": "minsik-coder",
      "apiBase": "http://192.168.50.10:8000/v1",
      "apiKey": "dummy"
    }
  ]
}
```

## curl 직접 호출 (스크립트에서 RTL/SPICE 생성 자동화)

```bash
curl -s http://192.168.50.10:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"minsik-coder","messages":[{"role":"user","content":"..."}]}'
```

> 인증을 켜려면 vLLM `--api-key <KEY>` 후 클라이언트 `OPENAI_API_KEY` 일치시킬 것.
> 전용망(192.168.50.0/24) 외부에는 절대 노출하지 말 것.
