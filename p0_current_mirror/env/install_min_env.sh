#!/usr/bin/env bash
set -e

echo "==============================="
echo " P0-민무장 환경 설치 스크립트"
echo " (WSL Ubuntu + gdsfactory only)"
echo "==============================="
echo

# 1. 기본 패키지
echo "[1/3] apt update & 기본 패키지 설치..."
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git

# 2. 작업 폴더 & 가상환경
echo "[2/3] 작업 폴더 및 가상환경 생성..."
LAB_ROOT="$HOME/sky130_lab"
mkdir -p ${LAB_ROOT}/projects

VENV_PATH="${LAB_ROOT}/venv_gds"
python3 -m venv ${VENV_PATH}

source ${VENV_PATH}/bin/activate
pip install --upgrade pip
pip install gdsfactory

# 3. 안내 메시지
echo "[3/3] 설치 완료."
echo
echo "이제 아래 순서로 진행하세요:"
echo
echo "1) 레포 클론:"
echo "   cd ${LAB_ROOT}/projects"
echo "   # GitHub 예시 (사용자명만 교체)"
echo "   git clone https://github.com/<YOUR_GITHUB_USERNAME>/rebalance_criteria.git p0_current_mirror"
echo "   # GitHub를 안 쓸 때: git clone /path/to/rebalance_criteria.bundle p0_current_mirror"
echo
echo "2) 제너레이터 실행:"
echo "   source ${VENV_PATH}/bin/activate"
echo "   cd ${LAB_ROOT}/projects/p0_current_mirror/src"
echo "   python run_generator.py"
echo
echo "cm_nf2.gds, cm_nf4.gds 가 생성되면 P0-민무장 환경 성공."
