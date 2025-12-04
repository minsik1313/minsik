# P1-sky130: Current Mirror Layout (Sky130 PCell 버전)

## 목표
- P0-민무장에서 만든 **D–A–B–A–B–D** 인터디직 패턴을 그대로 유지하되, sky130 PCell을 사용해 **실제 NMOS Current Mirror**처럼 보이는 GDS를 생성합니다.
- 완벽한 DRC/타이밍까지는 목표가 아니며, **PCell 호출·배치·라벨링 체력** 확보가 목적입니다.
- 현재 인프라 v1.0은 동결 상태입니다. 가상환경을 준비한 뒤 로컬에서 실행·DRC를 진행하는 흐름을 기준으로 합니다.

## 디렉터리 구조
```
p1_sky130_current_mirror/
├─ README_sky130.md
├─ env/
│  └─ install_sky130_env.sh      # sky130 PCell 실행용 최소 설치 스크립트(선택)
└─ src/
   ├─ cm_sky130.py               # sky130 current mirror generator
   └─ run_cm_sky130.py           # num_pairs(AB 페어 수) 스윕 실행 드라이버
```

## 환경 전제 (개요)
- Python 3.9+ 가상환경을 사용합니다.
- 필수 패키지: `gdsfactory`, `sky130` (volare로 sky130 PDK가 설치·연결되어 있다고 가정).
- Magic/KLayout 검증은 민식/잼민이/지피티가 별도로 환경을 맞춥니다. 코드는 **sky130 PCell을 호출할 수 있는 상태**만 보장하면 됩니다.

### 빠른 설치 (선택)
```bash
bash env/install_sky130_env.sh
```
- 위 스크립트는 Python venv 생성 + `gdsfactory`, `sky130` 설치까지만 수행합니다.
- volare PDK 설치, Magic 설정 등은 별도 문서를 따릅니다.
- GitHub 원격 예시(URL만 교체하면 바로 사용 가능):
  ```bash
  REPO_URL="https://github.com/your-username/current-mirror.git"
  git clone "$REPO_URL" p1_sky130_current_mirror
  ```

## 사용법
```bash
# 가상환경 활성화 후
cd p1_sky130_current_mirror/src
python run_cm_sky130.py
```
- 실행 시 `cm_sky130_nf2.gds`, `cm_sky130_nf4.gds`가 생성됩니다. (`num_pairs`=2/4 스윕)
- KLayout/Magic으로 열어 **D–A–B–A–B–D** 패턴이 sky130 nMOS PCell로 배치되었는지 확인해 주세요.
- 저장소 루트에서 P0/P1을 한 번에 돌리고 싶다면(가상환경 활성화 상태):
  ```bash
  ./run_all_gds.sh --p1-only   # sky130만 실행
  ```
  모듈(gdsfactory/sky130)이 없으면 오류 메시지와 함께 중단되므로, `env/install_sky130_env.sh`를 먼저 실행 후 재시도하세요.
- 필요 시 `pip install --upgrade pip && pip install gdsfactory sky130`로 패키지를 설치한 뒤 실행하세요. 네트워크 제약이 있으면 trusted-host나 미러 옵션을 활용할 수 있습니다.

#### 🧭 실행 확인
- `python -c "import gdsfactory" || pip install gdsfactory sky130`로 의존성을 맞춘 뒤 `./run_all_gds.sh --p1-only`로 GDS를 생성합니다.
- KLayout/Magic으로 ABAB 패턴과 `sd_pitch_pair` 변화가 잘 반영됐는지 확인하세요.

### 배치 스타일
- OpenFASoC/Glayout 계열에서 쓰는 **계층 + 상대좌표** 패턴을 적용했습니다.
  - `_make_nmos_device` → `_add_pair` → `make_sky130_current_mirror` 순으로 계층화.
  - **ABAB 페어** 단위로 배치해 A/B의 소스를 맞닿게 놓고, 페어 간에는 `sd_pitch_pair`만큼 상대 이동합니다.
- 그룹 메타데이터
  - `component.info["pairs"]`: `[(A0, B0), (A1, B1), ...]` 형태의 페어 목록 (num_pairs 기준)
  - `component.info["a_list"]` / `"b_list"`: 라벨/라우팅에 바로 쓸 수 있는 A/B 리스트
- 최소 라우팅 스케치
  - `route_common_source(...)`가 페어 전체 bbox 기준으로 가상의 공통 소스 레일을 하나 그립니다(메탈 레이어 스케치).
  - 게이트/드레인은 현재 라벨(`REF_D`, `OUT_D`, `GATE_BIAS`, `VSS`)만 찍어 두었고 금속 연결은 다음 단계에서 추가합니다.
- Guard/Tap ring
  - `add_guard_ring(...)`가 페어/더미 bbox를 감싸는 링을 스케치합니다(실제 tap 세부 규칙은 TODO).

### Sky130 DRC 방어 지침(요약)
- 간격 상수: `MIN_LI1_SPACING=0.2um`, `MIN_DIFF_SPACING=0.3um`을 최소 여유로 삼아 pitch를 잡습니다.
- 컨택 스택: Poly/Diffusion → li1 → Metal1 연결은 향후 `add_poly_to_m1_contact`, `add_diff_to_m1_contact` 헬퍼 내부에서만 처리하도록 강제합니다.
- Source 공유: AB 페어는 bbox 기반으로 맞닿게 배치해 diffusion이 끊기지 않도록 합니다.
- Tap/Guard ring: `add_guard_ring`로 mirror 블록을 감싸 latch-up을 방어합니다(현재는 네 면을 독립 직사각형으로 두르는 스케치, 거리·레이어 정교화는 후속 단계에서 다룹니다).

## 실행 결과 체크포인트 (DoD)
- 에러 없이 `cm_sky130_nf2.gds`, `cm_sky130_nf4.gds`가 생성된다.
- Magic/KLayout에서 **sky130 nMOS PCell**로 보인다(단순 사각형이 아님).
- 라벨: 최소 `REF_D`, `OUT_D`, `GATE_BIAS`, `VSS`가 적절한 위치에 찍혀 있다.
- 공통 소스: 페어 bbox 기준으로 메탈 레일 하나가 추가되어 있다(가상 레이어).
- Guard ring hook: `add_guard_ring` 호출이 포함되어 있으며, 링 외곽/내곽 bbox가 info에 기록된다(실제 tap 컨택은 이후 단계에서 구현).
- 코드 구조: 디바이스 생성 로직이 한 곳에 모여 있어 **다른 nMOS PCell로 교체**해도 패턴·레이아웃 흐름은 유지된다.

## 5. 환경 트러블슈팅 (WSL / Ubuntu / Magic)
install_sky130_env.sh 실행 이후 자주 발생하는 문제와 최소 방어책을 정리했습니다. 문제가 생기면 순서대로 확인하세요.

### 5.1 GUI 의존성 누락 문제
- **증상**: Magic 컴파일/실행 중 cannot open display 류 오류.
- **방어책**:
  - WSL Ubuntu에서 다음 패키지를 먼저 설치합니다.
    ```bash
    sudo apt-get update
    sudo apt-get install -y build-essential csh tk-dev tcl-dev m4 libx11-dev libcairo2-dev
    ```
  - Windows 측에서 VcXsrv 같은 X 서버를 켜 둬야 `magic -d XR`이 정상 동작합니다.

### 5.2 Magic OpenGL 관련 에러
- **증상**: Magic 실행 시 OpenGL 오류, 창이 바로 꺼짐 등.
- **방어책**: WSL에서는 XR 드라이버로 실행하는 것을 권장합니다.
  ```bash
  magic -d XR   # 추천
  ```
  편의를 위해 alias를 추가할 수 있습니다.
  ```bash
  echo 'alias magicxr="magic -d XR"' >> ~/.bashrc
  source ~/.bashrc
  ```

### 5.3 PDK 경로 설정 (PDK_ROOT / PDK)
- **증상**: GDS를 Magic에서 열면 트랜지스터가 빈 박스로만 보임(기술 레이어 미로드).
- **원인**: volare 설치 후에도 `PDK_ROOT`, `PDK` 환경 변수가 설정되지 않은 경우.
- **방어책**: `.bashrc`에 아래를 추가한 뒤 재적용합니다.
  ```bash
  export PDK_ROOT="$HOME/.volare"
  export PDK="sky130A"
  source ~/.bashrc
  ```
  `echo $PDK_ROOT`, `echo $PDK`로 값이 정상 출력되는지 확인하세요.

## 6. Magic / KLayout 검증 치트시트 (30초 루틴)
Current Mirror GDS를 찍은 직후 최소 sanity check용 루틴입니다.

### 6.1 Magic으로 DRC 최소 검증
```bash
magic -d XR
```
Magic 콘솔에서:
```
gds read current_mirror.gds   ;# 예: cm_sky130_nf2.gds
load current_mirror           ;# top cell 이름에 맞게 조정
select top cell
box values 0 0 0 0
z                             ;# 전체 보기
drc check
drc why
drc find next
```
빨간 영역을 클릭 후 `drc why`로 위반 규칙을 확인합니다.

### 6.2 KLayout으로 레이아웃 확인
```bash
klayout current_mirror.gds    # 예: klayout cm_nf2.gds
```
- Display → Show Hierarchy 활성화.
- Diff/Poly/Metal1/li1 레이어를 켜고 끄며 ABAB 패턴, dummy, pair 구조가 의도대로 배치됐는지 육안 점검합니다.

### 6.3 목적
설치 문제로 멈추지 않고, GDS 출력 직후 **30초 안에 최소 검증**을 끝내기 위한 공통 루틴입니다. 문제가 보이면 5번 트러블슈팅을 먼저 확인하세요.

## 참고
- P0-민무장 버전(`p0_current_mirror/`)은 그대로 유지됩니다.
- sky130 PCell 호출 예시는 `src/cm_sky130.py`를 참고하세요. 라벨/라우팅은 **가벼운 스케치 수준**으로만 포함되어 있습니다.
