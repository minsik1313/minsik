# Analog 레인

혼성 SoC의 아날로그 IP 설계·사이징 자동화 (계획서 §2.5, §2.6).

```
analog/
└── amp/
    ├── common_source.spice   # ngspice 데모 회로 (generic 모델, PDK 불필요)
    └── sizing_sweep.py       # W 스윕 → 게인 측정 → 최적 W 선정 (사이징 자동화 골격)
```

## 사이징 스윕 실행
```bash
# 루트에서
make analog-sweep
# 또는
python3 analog/amp/sizing_sweep.py
```
필요 도구: `ngspice`.

## 실제 설계로의 전환
- `common_source.spice`의 `.model` 줄을 sky130 디바이스 모델로 교체:
  `.lib $PDK_ROOT/sky130A/libs.tech/ngspice/sky130.lib.spice tt` + `sky130_fd_pr__nfet_01v8`.
- 상수 스윕 → **MOBO(베이지안 최적화)** 루프로 교체하면 다목적 사이징 자동화로 확장.
- 레이아웃: Xschem 스키매틱 → Magic/KLayout(파이썬 제너레이터) → Netgen LVS / Magic PEX.
