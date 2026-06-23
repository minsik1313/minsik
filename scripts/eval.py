#!/usr/bin/env python3
"""파인튜닝 결과 간단 평가.

swift infer 가 저장한 결과 JSONL(--result_path)을 읽어,
예측(response)과 정답(label)을 비교한다.

- 분류/짧은 텍스트: exact-match accuracy
- ASR/자유 텍스트: --metric wer 로 단어 오류율(WER) 계산 (jiwer 필요)

swift infer 결과 줄에는 보통 다음 키가 있다:
  {"response": "...", "labels": "..."}  또는 {"response": "...", "label": "..."}
키 이름은 버전에 따라 다를 수 있어 유연하게 처리한다.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_pairs(path: Path) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            pred = obj.get("response") or obj.get("prediction") or ""
            # 정답 후보 키 탐색
            label = (
                obj.get("labels")
                or obj.get("label")
                or obj.get("solution")
                or obj.get("target")
                or ""
            )
            # messages 안의 마지막 assistant 가 정답인 경우 대응
            if not label and isinstance(obj.get("messages"), list):
                for m in reversed(obj["messages"]):
                    if m.get("role") == "assistant":
                        label = m.get("content", "")
                        break
            pairs.append((str(pred).strip(), str(label).strip()))
    return pairs


def accuracy(pairs: list[tuple[str, str]]) -> float:
    if not pairs:
        return 0.0
    correct = sum(1 for p, l in pairs if p == l)
    return correct / len(pairs)


def wer(pairs: list[tuple[str, str]]) -> float:
    try:
        from jiwer import wer as _wer
    except ImportError:
        raise SystemExit("jiwer 미설치: pip install jiwer")
    preds = [p for p, _ in pairs]
    refs = [l for _, l in pairs]
    return _wer(refs, preds)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", default="outputs/infer_result.jsonl",
                    help="swift infer 결과 JSONL 경로")
    ap.add_argument("--metric", choices=["accuracy", "wer"], default="accuracy")
    ap.add_argument("--show", type=int, default=5, help="샘플 미리보기 개수")
    args = ap.parse_args()

    path = Path(args.pred)
    if not path.exists():
        raise SystemExit(f"결과 파일 없음: {path}  (먼저 bash scripts/infer.sh 실행)")

    pairs = load_pairs(path)
    print(f"평가 샘플 수: {len(pairs)}")
    for i, (p, l) in enumerate(pairs[: args.show]):
        print(f"  [{i}] pred={p!r}  label={l!r}")

    if args.metric == "accuracy":
        print(f"\nExact-match accuracy: {accuracy(pairs):.4f}")
    else:
        print(f"\nWER: {wer(pairs):.4f}")


if __name__ == "__main__":
    main()
