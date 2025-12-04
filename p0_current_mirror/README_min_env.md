# P0-민무장: Current Mirror Code-Layout (No PDK)

## 목표

- 외장 SSD, sky130 PDK 없이
- **WSL + Ubuntu + Python + gdsfactory(generic)**만 가지고
- Current Mirror 패턴(D-A-B-A-B-D)을 코드로 GDS로 찍어보는 것.

## 1. WSL + Ubuntu 설치 (윈도우에서 1회)

PowerShell(관리자)에서:

```powershell
wsl --install -d Ubuntu-22.04
```

재부팅 후 Ubuntu 뜨면 사용자 이름/비번만 설정.

## 2. 기본 패키지 & 가상환경

Ubuntu(WSL) 터미널에서:

```
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git
```

작업 폴더 & 가상환경:

```
mkdir -p ~/sky130_lab/projects
python3 -m venv ~/sky130_lab/venv_gds

source ~/sky130_lab/venv_gds/bin/activate
pip install --upgrade pip
pip install gdsfactory
```

## 3. 이 레포 가져오기

이 레포는 기본 원격이 없습니다. GitHub에 새 repo를 만든 뒤 **본인 계정·레포 이름**으로 URL을 채워 넣어야 합니다.

```
cd ~/sky130_lab/projects

# GitHub에 올려둔 경우(사용자명만 교체)
REPO_URL="https://github.com/<YOUR_GITHUB_USERNAME>/rebalance_criteria.git"
git clone "$REPO_URL" p0_current_mirror

# GitHub 없이 번들 파일만 받은 경우: 한 줄 복원 + main 체크아웃
# ./restore_from_bundle.sh /path/to/rebalance_criteria.bundle p0_current_mirror main

cd p0_current_mirror
```

> GitHub를 쓰지 않을 경우 `package_repo.sh`나 `make_git_bundle.sh`로 만든 번들을 받아 `git clone rebalance_criteria.bundle p0_current_mirror`처럼 복원하세요. `<YOUR_GITHUB_USERNAME>`를 그대로 두면 clone이 실패합니다.

## 4. 제너레이터 실행해보기

```
source ~/sky130_lab/venv_gds/bin/activate
cd ~/sky130_lab/projects/p0_current_mirror/src

python run_generator.py
```

정상 실행되면 `cm_nf2.gds`, `cm_nf4.gds` 두 개가 생성된다.(`nf_per_leg` 파라미터를 2/4로 스윕)

## 5. (선택) Magic으로 GDS 확인

원하면:

```
sudo apt install -y magic
magic cm_nf2.gds
```

여기서 보는 건 generic layout 모양이고,
아직 sky130 DRC/규칙을 따르는 건 아니다.

---

## 6. env/install_min_env.sh (간단 버전)

집에서 민식이 WSL 켜고 한 번에 돌릴 수 있게,
최소 설치만 하는 스크립트. 저장 위치는 `p0_current_mirror/env/install_min_env.sh`이며,

```bash
bash env/install_min_env.sh
```

처럼 실행하면 된다.

```bash
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
echo "   git clone <레포주소> p0_current_mirror"
echo
echo "2) 제너레이터 실행:"
echo "   source ${VENV_PATH}/bin/activate"
echo "   cd ${LAB_ROOT}/projects/p0_current_mirror/src"
echo "   python run_generator.py"
echo
echo "cm_nf2.gds, cm_nf4.gds 가 생성되면 P0-민무장 환경 성공."
```

<레포주소>는 네가 실제 Git remote 정해지면 그때 채워 넣으면 된다.
