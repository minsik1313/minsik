#!/usr/bin/env python3
"""오디오 멀티모달 파인튜닝용 데이터 준비 스크립트.

ms-swift 멀티모달 JSONL 포맷으로 train/val 셋을 생성한다.
각 샘플 포맷:
    {
      "messages": [
        {"role": "user", "content": "<audio>이 음성을 한국어로 받아써줘"},
        {"role": "assistant", "content": "정답 텍스트"}
      ],
      "audios": ["data/clips/0001.wav"]
    }

기본 동작:
- --synthesize 사용 시, 의존성만으로 동작하는 합성 사인파 .wav 샘플과
  JSONL을 만들어 파이프라인 smoke test가 가능하도록 한다(실데이터 불필요).
- 실데이터 사용 시 build_records()를 본인 데이터에 맞게 수정.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import struct
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
CLIPS_DIR = DATA_DIR / "clips"

# smoke test용: (주파수 라벨, Hz) → assistant 정답으로 사용
TONE_LABELS = [
    ("낮은 음", 220.0),
    ("중간 음", 440.0),
    ("높은 음", 880.0),
]
PROMPT = "<audio>이 오디오에 들어있는 음의 높이를 '낮은 음/중간 음/높은 음' 중 하나로 답해줘."


def write_sine_wav(path: Path, freq: float, seconds: float = 1.0, rate: int = 16000) -> None:
    """의존성 없이 표준 라이브러리만으로 사인파 wav 생성 (16kHz mono 16bit)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(seconds * rate)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            val = int(0.3 * 32767 * math.sin(2 * math.pi * freq * i / rate))
            frames += struct.pack("<h", val)
        w.writeframes(bytes(frames))


def build_synthetic_records(n_per_class: int) -> list[dict]:
    """smoke test용 합성 데이터셋. 실데이터로 교체하세요."""
    records: list[dict] = []
    idx = 0
    for label, freq in TONE_LABELS:
        for _ in range(n_per_class):
            clip = CLIPS_DIR / f"{idx:04d}.wav"
            write_sine_wav(clip, freq)
            records.append(
                {
                    "messages": [
                        {"role": "user", "content": PROMPT},
                        {"role": "assistant", "content": label},
                    ],
                    "audios": [str(clip.relative_to(PROJECT_ROOT))],
                }
            )
            idx += 1
    return records


def build_records_from_real_data() -> list[dict]:
    """실데이터 연결 지점.

    예: 음성 인식(ASR)이라면 (wav 경로, transcript) 쌍을 순회하며
        messages의 user content는 "<audio>이 음성을 받아써줘",
        assistant content는 transcript로 채운다.
    """
    raise NotImplementedError(
        "실데이터 로딩 로직을 구현하세요. 우선은 --synthesize로 파이프라인을 검증하세요."
    )


def dump_jsonl(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  wrote {len(records):4d} samples -> {path.relative_to(PROJECT_ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthesize", action="store_true",
                    help="합성 샘플 데이터 생성 (smoke test용)")
    ap.add_argument("--n-per-class", type=int, default=12,
                    help="합성 모드에서 클래스당 샘플 수")
    ap.add_argument("--val-ratio", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)

    if args.synthesize:
        records = build_synthetic_records(args.n_per_class)
    else:
        records = build_records_from_real_data()

    random.shuffle(records)
    n_val = max(1, int(len(records) * args.val_ratio))
    val, train = records[:n_val], records[n_val:]

    dump_jsonl(train, DATA_DIR / "train.jsonl")
    dump_jsonl(val, DATA_DIR / "val.jsonl")
    print(f"\n총 {len(records)}건 (train={len(train)}, val={len(val)})")
    print("다음: bash scripts/train.sh")


if __name__ == "__main__":
    main()
