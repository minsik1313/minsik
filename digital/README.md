# Digital 레인

혼성 SoC의 디지털 백엔드 블록과 RTL→GDS 자동화 플로우 (계획서 §2.7, §2.8).

```
digital/
├── rtl/boxcar_filter.v        # N-tap 이동평균 필터 (센서 디지털 처리 블록)
├── tb/                        # cocotb 회귀 (sign-off 게이트)
│   ├── test_boxcar_filter.py
│   └── Makefile               # SIM=icarus
└── openlane/config.json       # OpenLane2 RTL→GDS 설정 (sky130A)
```

## 시뮬레이션 (검증)
```bash
# 루트에서
make digital-sim
# 또는
make -C digital/tb
```
필요 도구: `iverilog`(Icarus), `cocotb`.

## RTL → GDS (레이아웃 자동화)
```bash
# IIC-OSIC-TOOLS 컨테이너 내부 (OpenLane2 + sky130A 필요)
openlane digital/openlane/config.json
```
floorplan/배치/CTS/라우팅/STA/DRC/LVS가 자동 수행된다.
