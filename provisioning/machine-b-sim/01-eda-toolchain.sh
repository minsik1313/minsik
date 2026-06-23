#!/usr/bin/env bash
# Machine B: 오픈소스 회로설계 EDA 툴체인 설치 (Ubuntu 24.04).
# 아날로그 SPICE + 디지털 RTL/합성 전반.
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "sudo 로 실행하세요." >&2; exit 1; fi

echo ">> 공통 빌드 도구"
apt-get update -qq
apt-get install -y build-essential git cmake python3 python3-pip parallel iperf3

echo ">> 아날로그 SPICE + 스키매틱/레이아웃"
apt-get install -y ngspice xschem magic   # ngspice(시뮬), xschem(스키매틱), magic(레이아웃)
# Xyce(병렬 SPICE, MC/코너 대량 처리)는 별도 빌드 또는 공식 패키지 사용:
#   https://xyce.sandia.gov/  (대형 MC 스윕 시 권장)

echo ">> 디지털 RTL 시뮬/합성"
apt-get install -y verilator iverilog gtkwave yosys
# OpenROAD/OpenLane(PnR)는 컨테이너 권장:
#   https://github.com/The-OpenROAD-Project/OpenLane

echo ">> KiCad (PCB, 선택)"
apt-get install -y kicad || echo "(KiCad 생략 가능)"

echo ""
echo ">> 설치 확인"
for t in ngspice verilator iverilog yosys gtkwave; do
  printf "  %-12s " "$t"; command -v "$t" >/dev/null && "$t" --version 2>&1 | head -1 || echo "없음"
done

echo "완료. 예제 실행: eda/spice/  및  eda/rtl/"
