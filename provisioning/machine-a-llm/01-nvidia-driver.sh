#!/usr/bin/env bash
# Machine A: NVIDIA 드라이버 + CUDA 컨테이너 툴킷 설치 (Ubuntu 24.04).
# 2x RTX 5090(Blackwell)은 최신 드라이버 필요 — 570 계열 이상 권장.
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "sudo 로 실행하세요." >&2; exit 1; fi

echo ">> 빌드 도구/커널 헤더"
apt-get update -qq
apt-get install -y build-essential dkms linux-headers-"$(uname -r)"

echo ">> NVIDIA 드라이버 설치 (ubuntu-drivers 자동 선택)"
apt-get install -y ubuntu-drivers-common
# Blackwell(5090)은 신형 드라이버 필요. 자동 선택이 너무 낮으면 아래 주석으로 명시 설치.
ubuntu-drivers autoinstall
# apt-get install -y nvidia-driver-570    # ← 필요 시 버전 고정

echo ">> NVIDIA Container Toolkit (vLLM 도커 사용 대비)"
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  > /etc/apt/sources.list.d/nvidia-container-toolkit.list
apt-get update -qq
apt-get install -y nvidia-container-toolkit || echo "(도커 미사용 시 무시 가능)"

echo ""
echo ">> 재부팅 후 'nvidia-smi' 로 2x RTX 5090 인식 확인."
echo "   재부팅: sudo reboot"
