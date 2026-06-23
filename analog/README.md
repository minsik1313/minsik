# Analog 레인 — 전압 도메인 인지 자동화

혼성 SoC의 아날로그 IP 설계·사이징 자동화 (계획서 §2.5, §2.6).
단순 width 스윕이 아니라 **전압 도메인 → 소자 flavor → 구조(topology) → 사이징**을
순서대로 결정하는 모델이다.

```
analog/
└── sizing/
    ├── tech.py        # 전압 도메인 라이브러리 (sky130 소자 flavor 매핑)
    ├── topology.py    # 구조 라이브러리 + ngspice 덱 생성 (CS / 2-stage)
    └── autosize.py    # 오케스트레이터 (스펙 → 소자/구조/사이징 자동 결정)
```

## 동작 원리 (파이프라인)
```
spec(Vdd, gain)
   │
   ├─▶ select_domain(Vdd)        전압 도메인 판정 → sky130 소자 flavor 선정
   │     1.8V → nfet_01v8 (thin-ox),  3.3~5V → nfet_g5v0d10v5 (thick-ox)
   │     ※ Vds_max 가 Vdd*1.05 를 못 덮으면 더 두꺼운 소자로 자동 승격
   │
   ├─▶ bias = Vth + Vov          도메인별 헤드룸/오버드라이브로 바이어스 설정
   │
   └─▶ for topology in [CS, two_stage]:   구조 선정 (게인 부족 시 자동 승격)
          sweep W → ngspice 측정 →
            (a) 게인 목표 충족  AND
            (b) 출력이 포화영역 헤드룸 내  AND
            (c) Vds ≤ 소자 정격
          → 처음으로 만족하는 (구조, W) 채택
```

## 실행
```bash
make analog-autosize
# 또는
python3 analog/sizing/autosize.py
```
필요 도구: `ngspice`.

### 예시 출력이 보여주는 것
- **1.8V 저게인** → `nfet_01v8` + common_source
- **1.8V 고게인(30dB)** → 단단 부족 → **two_stage 로 구조 자동 승격**
- **5V** → **thick-oxide `nfet_g5v0d10v5` 소자 flavor 자동 선택** (1.8V 소자는 과전압)

## 코어 블록 설계 체크리스트
OTA · LDO · BGR · OSC · PLL 블록별 스펙→구조→사이징→검증→레이아웃 체크리스트와
설계 순서(의존성)는 [`docs/BLOCK_CHECKLIST.md`](../docs/BLOCK_CHECKLIST.md) 참고.

### 구현된 블록
- **BGR** — sky130A sub-1V Banba 밴드갭 (Vdd 1.2V → Vref 0.8V, TC 25 ppm/°C):
  [`bgr/`](bgr/) · 실행 `make bgr-sim`

## 실제(sky130) 설계로의 전환
현재는 PDK 없이 돌도록 generic Level-1 모델을 쓰지만, 두 군데만 바꾸면 실 PDK로 전환된다.
1. `tech.py`의 `demo_model` → sky130 `.lib` include 로 교체:
   `.lib $PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice tt`,
   소자는 `tech.py`의 `nfet`/`pfet` 이름(`sky130_fd_pr__...`)으로 인스턴스화.
2. `autosize.py`의 상수 W 스윕 → **gm/Id 방법론 + MOBO(베이지안 최적화)** 로 교체.
3. 레이아웃: Xschem 스키매틱 → Magic/KLayout(파이썬 제너레이터) → Netgen LVS / Magic PEX.
