# 로컬 오디오 멀티모달 AI 파인튜닝

8~16GB GPU에서 **오디오/음성 포함 멀티모달 모델을 LoRA/QLoRA로 파인튜닝**하는 파이프라인.

- **모델**: [`Qwen/Qwen2.5-Omni-3B`](https://huggingface.co/Qwen/Qwen2.5-Omni-7B) — 텍스트·이미지·오디오·비디오 입력 처리 omni 모델 (3B = 저사양 GPU용)
- **프레임워크**: [ms-swift](https://github.com/modelscope/ms-swift) — PEFT/추론/병합 일괄 지원
- **방식**: QLoRA(4bit) + 오디오 인코더 freeze + 텍스트 백본 linear LoRA(rank 8)

## 요구사항
- NVIDIA GPU 8GB 이상 (16GB 권장), CUDA 12.x
- Python 3.10+
- GPU가 없다면 아래 **Colab에서 실행** 참고 (GitHub Codespaces는 2025-08 GPU 지원 종료)

## Colab에서 실행 (GPU 없을 때 권장)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/minsik1313/minsik/blob/claude/local-multimodal-model-8mluhh/notebooks/colab_finetune.ipynb)

`notebooks/colab_finetune.ipynb`를 Colab에서 열고 `런타임 > 런타임 유형 변경 > GPU` 설정 후 셀을 순서대로 실행하면
클론 → 설치 → 데이터 → 학습 → 추론 → 평가가 자동으로 진행됩니다.
무료 T4(Turing)는 bf16 미지원이라 노트북이 자동으로 **fp16**으로 학습합니다.

## 빠른 시작

```bash
# 1) 환경 셋업 (가상환경 + 의존성 + 검증)
bash scripts/setup.sh
source .venv/bin/activate

# 2) 샘플 데이터 생성 (smoke test용 합성 오디오)
python scripts/prepare_data.py --synthesize --n-per-class 12

# 3) 학습 (1 epoch smoke test, QLoRA 4bit)
bash scripts/train.sh

# 4) 추론 (val 셋 배치 추론 → outputs/infer_result.jsonl)
bash scripts/infer.sh

# 5) 평가
python scripts/eval.py --metric accuracy        # 분류/짧은텍스트
# python scripts/eval.py --metric wer           # ASR (jiwer 필요)
```

## 구조
```
scripts/
  setup.sh          환경 셋업 + 설치 검증
  prepare_data.py   ms-swift JSONL 데이터 생성 (--synthesize 로 합성 샘플)
  train.sh          Qwen2.5-Omni-3B QLoRA 학습
  infer.sh          어댑터 로드 후 추론
  eval.py           accuracy / WER 평가
configs/
  qwen25omni_qlora.yaml   하이퍼파라미터 요약(문서용)
data/
  README.md         데이터 포맷 설명 (실데이터는 git 제외)
```

## VRAM 가이드
| GPU | 권장 설정 |
|-----|-----------|
| 8~12GB | QLoRA 4bit + `freeze_vit` + `max_length` 축소 (기본값) |
| 16GB+ | LoRA bf16 (양자화 해제), batch_size 2 — `train.sh` 하단 주석 참고 |

## 실데이터 적용
1. `scripts/prepare_data.py`의 `build_records_from_real_data()`를 본인 데이터(wav 경로 + 정답)에 맞게 구현
2. `--synthesize` 없이 `python scripts/prepare_data.py` 실행
3. 태스크별 프롬프트 구성은 `data/README.md` 참고 (ASR / 음성 QA / 오디오 캡셔닝)

## 범위/주의
- 1차 범위는 **오디오 이해(입력)** 파인튜닝. 음성 출력(합성)까지 학습하려면 talker 모듈 별도 구성 필요.
- 오디오 시퀀스가 길면 8GB에서 OOM 가능 → `MAX_LENGTH` / 오디오 클립 길이 축소로 대응.

## 대안 모델
- **Phi-4-multimodal (5.6B)**: 오디오+비전 동시 필요 시 (Mixture-of-LoRAs)
- **Qwen2-Audio-7B**: 오디오-텍스트 전용 ([ms-swift best practice](https://swift2x-en.readthedocs.io/en/latest/Multi-Modal/qwen-audio-best-practice.html))
