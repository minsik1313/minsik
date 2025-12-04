#!/usr/bin/env bash
set -e

# P1-sky130: sky130 PCell 실행용 최소 설치 스크립트
# - Python venv 생성
# - gdsfactory + sky130 설치
# - volare PDK 설치/연결, Magic/KLayout 설정은 별도 문서를 따릅니다.

echo "==============================="
echo " P1-sky130 환경 설치 스크립트"
echo " (gdsfactory + sky130 PCell)"
echo "==============================="
echo

# 1) 기본 패키지
echo "[1/3] apt update & 기본 패키지 설치..."
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git

# 2) 작업 폴더 및 가상환경
LAB_ROOT="$HOME/sky130_lab"
VENV_PATH="${LAB_ROOT}/venv_sky130"

mkdir -p "${LAB_ROOT}/projects"
python3 -m venv "${VENV_PATH}"
source "${VENV_PATH}/bin/activate"

# 3) 패키지 설치
pip install --upgrade pip
pip install gdsfactory sky130

echo "[3/3] 설치 완료. 다음을 수행하세요:"
echo "1) 레포 클론:"
echo "   cd ${LAB_ROOT}/projects"
echo "   REPO_URL=\"https://github.com/your-username/current-mirror.git\""
echo "   git clone \"${REPO_URL}\" p1_sky130_current_mirror"
echo "   cd p1_sky130_current_mirror/src"
echo "2) 제너레이터 실행:"
echo "   source ${VENV_PATH}/bin/activate"
echo "   python run_cm_sky130.py"
echo "3) KLayout/Magic에서 cm_sky130_nf2.gds, cm_sky130_nf4.gds를 열어 PCell 배치 확인"
echo "4) WSL에서 Magic GUI 오류가 나면 README_sky130.md의 '환경 트러블슈팅' 절을 참고하세요."
