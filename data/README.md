# 데이터 디렉터리

이 폴더의 `*.jsonl`, `clips/`, `*.wav` 등 실제 데이터는 git에 커밋되지 않습니다
(루트 `.gitignore` 참고). 이 README만 추적됩니다.

## 포맷 (ms-swift 멀티모달 JSONL)

한 줄당 하나의 샘플:

```json
{"messages": [{"role": "user", "content": "<audio>이 음성을 한국어로 받아써줘"}, {"role": "assistant", "content": "정답 텍스트"}], "audios": ["data/clips/0001.wav"]}
```

- `<audio>` 토큰 개수는 `audios` 배열 길이와 일치해야 합니다.
- 오디오는 16kHz mono wav 권장(다른 포맷도 librosa로 디코딩되나 길이가 길면 VRAM↑).

## 생성 방법

```bash
# smoke test용 합성 데이터 (의존성 없이 표준 라이브러리로 사인파 wav 생성)
python scripts/prepare_data.py --synthesize --n-per-class 12

# 실데이터: prepare_data.py 의 build_records_from_real_data() 를 구현 후
python scripts/prepare_data.py
```

생성물:
- `data/train.jsonl`, `data/val.jsonl`
- `data/clips/*.wav`

## 태스크 예시별 user/assistant 구성
- **ASR(음성→텍스트)**: user `"<audio>이 음성을 받아써줘"`, assistant = transcript
- **음성 QA**: user `"<audio>{질문}"`, assistant = 답변
- **오디오 분류/캡셔닝**: user `"<audio>이 소리가 무엇인지 설명해줘"`, assistant = 라벨/설명
