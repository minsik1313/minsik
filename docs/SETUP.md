# 환경 구축 (Phase 0)

오픈소스 EDA 부트스트랩 환경. 계획서(`FABLESS_PLAN.md`) §2.1~2.4의 실행편.

## 가장 쉬운 길: GitHub Codespaces
이 repo는 `.devcontainer/`를 포함하므로 Codespace로 열면 `iverilog`·`ngspice`·`cocotb`가
자동 설치된다. 별도 설치 없이 `make digital-sim`, `make analog-autosize` 실행 가능.
(레이아웃·RTL→GDS까지 필요하면 아래 IIC-OSIC-TOOLS 이미지를 사용.)

## 권장(풀 플로우): 컨테이너 단일 환경
모든 PDK·툴이 동봉된 **IIC-OSIC-TOOLS** Docker 이미지를 표준 환경으로 사용한다.
```bash
docker run -it --rm -v "$PWD":/work -w /work hpretl/iic-osic-tools
```
포함: sky130A · gf180mcuD · ihp-sg13g2 PDK, ngspice/Xyce, Xschem, Magic, KLayout,
Netgen, Yosys, OpenLane2/OpenROAD, Verilator, cocotb 등.

## 최소(이 저장소 검증용) 로컬 설치
이 저장소의 데모(디지털 회귀 + 아날로그 스윕)만 돌리려면:
```bash
sudo apt-get install -y iverilog ngspice   # 시뮬레이터
pip install cocotb                          # 디지털 검증 프레임워크
```

## 동작 확인
```bash
make digital-sim       # cocotb + Icarus 회귀 통과
make analog-autosize   # 전압 도메인 인지 아날로그 사이징 실행
```

## PDK 표준화
- 기본: **sky130A** (`open_pdks` 또는 컨테이너 동봉).
- RF/SiGe 필요 시 **ihp-sg13g2** 병행.
- `PDK_ROOT` 환경변수로 SPICE `.lib` include 경로를 잡는다.
