<!-- ──────────────────────────────────────────────────────────────── -->
# 🌱 Sustainable Investment Toolkit
> **지속가능 투자(Sustainable Investment)**·경제 분석을 위한 100 % 오픈소스 파이썬 프로젝트  
<!-- ──────────────────────────────────────────────────────────────── -->

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9‒3.12-blue.svg)](https://www.python.org/)
[![Build](https://github.com/your-username/sustainable-investment/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/sustainable-investment/actions)
[![Docs](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://your-username.github.io/sustainable-investment)

> *“Balance profit **and** purpose—one pull request at a time.”*

> **Current-mirror mini mission:** P0(제너릭)·P1(sky130) 코드 제너레이터를 로컬에서 GDS → DRC까지 흘려보내는 흐름을 검증합니다.

---

## 📤 GitHub로 올리고 내려받기 (요약)
1. **원격 저장소 생성(필수)**: 기본 원격이 없습니다. **당신 GitHub 계정으로 새 repo를 만든 뒤** 아래 명령을 그대로 복사해 사용자명/레포명을 바꿔 주세요.
   ```bash
   # HTTPS 예시 (붙여넣고 <> 부분만 바꾸면 됨)
   REPO_URL="https://github.com/<YOUR_GITHUB_USERNAME>/rebalance_criteria.git"
   # SSH 예시
   # REPO_URL="git@github.com:<YOUR_GITHUB_USERNAME>/rebalance_criteria.git"
   ```
   > 정말 GitHub를 쓰지 않겠다면, 아래 **git 번들** 방법을 쓰세요. (원격 없이도 `./restore_from_bundle.sh rebalance_criteria.bundle rebalance_criteria main` 한 줄로 복원 가능)
2. **로컬을 원격에 연결**: 프로젝트 루트에서 `git remote add origin "$REPO_URL"` (이미 있으면 `git remote set-url origin "$REPO_URL"`)
3. **커밋 후 푸시**:
   ```bash
   git add .
   git commit -m "Initial current-mirror scaffolding"
   git push -u origin $(git branch --show-current)
   ```
4. **다른 환경에서 복제**: 집/비프록시 환경에서 `git clone "$REPO_URL"`로 받아 `./run_all_gds.sh`를 실행합니다.

> 업데이트 번들을 텍스트로 중계할 때는 `python p0_current_mirror/export_for_gpt.py --summary "..." --output updates_for_gpt.txt` 결과를 복사해 전달하면 됩니다.

### GitHub 없이 공유해야 할 때: 로컬 번들 생성
- `./package_repo.sh`를 실행하면 현재 커밋을 포함한 tar.gz 번들(기본: `rebalance_criteria_bundle_YYYYMMDD.tar.gz`)이 생성됩니다.
- **git clone이 꼭 필요하면** `./make_git_bundle.sh`로 `rebalance_criteria.bundle`을 만든 뒤, 다른 PC에서 아래처럼 복원하면 됩니다:
  ```bash
  # (원본 PC) 번들 생성
  ./make_git_bundle.sh    # 결과: rebalance_criteria.bundle

  # (다른 PC) 번들을 받아둔 후: 한 줄 복원 + main 체크아웃
  ./restore_from_bundle.sh rebalance_criteria.bundle rebalance_criteria main

  # 확인 후 실행
  cd rebalance_criteria
  ./run_all_gds.sh
  ```
- tar 번들을 메신저/이메일로 전달하면 상대방은 압축을 풀고 `./run_all_gds.sh`만 실행하면 됩니다.
- 출력 경로를 직접 지정하려면 `./package_repo.sh /tmp/my_bundle.tar.gz`처럼 실행하세요.

---

## 📑 개요
**Sustainable Investment Toolkit**은 ESG·임팩트·기후 리스크 데이터를  
*프로그래머블* 방식으로 수집·분석·시각화하여 **데이터 기반 지속가능 투자 전략**을 연구합니다.  

- **오직 파이썬**으로 작성 → Windows에서도 바로 실행  
- Jupyter Notebook, Dash 대시보드, 백테스트 스크립트를 모두 포함  
- “발표 지연·데이터 누수” 방지용 **Point-in-Time** 레이어 내장  

---

## 📚 목차
1. [주요 특징](#-주요-특징)  
2. [빠른 시작](#-빠른-시작)  
3. [디렉터리 구조](#-디렉터리-구조)  
4. [데이터 소스](#-데이터-소스)  
5. [5분 ESG 백테스트](#-5분-esg-백테스트)  
6. [로드맵](#-로드맵)  
7. [기여 가이드](#-기여-가이드)  
8. [라이선스](#-라이선스)  
9. [연락처](#-연락처)  

---

## ✨ 주요 특징
| 카테고리 | 기능 | 구현 스택 |
|----------|------|-----------|
| **데이터 수집** | Refinitiv·Sustainalytics·SEC 공시 API 래퍼 | `requests`, `pydantic` |
| **누수 방지** | 발표일+지연(Lag) 시프트, Point-in-Time 스냅샷 | `pandas`, `duckdb` |
| **리스크 모델** | CAPM·Fama-French·Carhart 확장팩 | `statsmodels` |
| **백테스트** | 벡터화·병렬 실행 파이프라인 | `vectorbt`, `numba` |
| **대시보드** | 실시간 포트폴리오&시나리오 뷰어 | `Plotly Dash` |
| **문서화** | Sphinx + GitHub Pages 자동 배포 | `sphinx-awesome-theme` |

---

## 🚀 빠른 시작
> **환경** | Windows 10/11, PowerShell, Python 3.9 이상

```powershell
# 1) 저장소 클론
git clone https://github.com/your-username/sustainable-investment.git
cd sustainable-investment

# 2) 가상환경 생성 & 활성화
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # (Cmd.exe 사용 시 .\.venv\Scripts\activate.bat)

# 3) 패키지 설치
pip install -r requirements.txt

# 4) 첫 파이프라인 실행 (2018‒2025 ESG 백테스트)
python scripts\run_pipeline.py --start 2018-01-01 --end 2025-07-31

---

## 🧠 AI 에이전트 역할 요약 (간소화)
> 민식은 **전달자** 역할만 수행합니다. 세 에이전트가 직접 말하고, 서로의 질문도 원문 그대로 중계합니다.

| 에이전트 | 핵심 역할 | 요청/전달 팁 |
|-----------|-----------|---------------|
| **잼민이(Gemini)** | 실시간 검색·멀티모달 요약(이미지·표·영상). | 입력 형식을 명시해 전달합니다. 필요하면 한 줄 요약만 추가. |
| **지피티(ChatGPT 5.1)** | 문제 정리·로드맵·명세서 작성. | 배경/제약/DoD를 붙여달라고 요청하고, 들은 말을 그대로 중계합니다. |
| **코덱이(ChatGPT Codex)** | **코더 전담**. 잼민이/지피티가 모아준 스펙·데이터를 구현합니다. | 함수 시그니처·입출력 예시·실패 케이스를 함께 넘기고, 코덱이는 필요한 포맷·툴링을 자유롭게 요구할 수 있습니다. |

### 기본 흐름
1. 질문을 각 에이전트에게 **그대로** 전달합니다.
2. 답변을 원문으로 공유합니다.
3. 필요한 경우, 서로에게 추가 질문을 다시 전달합니다.
4. 최종 선택·판단은 민식이 직접 합니다.

### 복사해 전달하기
- **to 잼민이 · from 민식**
  - "실시간 정보·이미지/영상 요약 부탁해. 입력 형식은 이렇게 보내: [자료 붙임]."
  - "코덱이가 손그림만 보고 코드 짤 수 있는지 답 줘."
- **to 지피티 · from 민식**
  - "아이디어를 명세서/로드맵으로 정리해 줘. 배경·제약·완료 정의를 내가 전달할게."
  - "코덱이가 편한 스펙 포맷과 폴더 구조가 뭔지 묻고 있어, 답 좀 줘."
- **to 코덱이 · from 민식**
  - 역할: "팀의 코더. 주제 선정은 묻지 않고, 받은 스펙대로 짜 줘."
  - 입력 예시: `input_data = {"bitcoin_price": [list], "gold_price": [list]}` / `output_format = "pandas_dataframe"` / `target_variable = "correlation_coefficient"`
  - 질문: "이미지나 손그림만 보고도 코드 작성 가능한지, 필요 포맷/추가 설명을 알려줘."
  - 권한: "코드를 더 편하게 짜기 위한 요청·툴링 제안은 언제든 잼민이·지피티에게 바로 물어봐."
  - **지피티에서 전달할 R&R 정리 & 질문**
    ```
    to 코덱이 (from 지피티, via 민식)
    [지금 상황 기준 R&R 요약: 👑 민식=주제·결정 / 💎 잼민이=정보·요약(Option A) / 🧠 지피티=PM·명세 / 💻 코덱이=개발·통합]

    자료 모으기와 말 정리는 민식·지피티·잼민이가 하고,
    그걸 코드/시스템으로 구현하는 주역은 코덱이 너야.

    잼민이가 주는 레퍼런스 코드는 참고용일 뿐, 프로젝트 구조에 맞게 재구성하는 건 전부 네 영역으로 둘게.

    다음 단계: 네가 편한 스펙 형식(MVP 범위, 폴더 구조, 로그 기준 등)을 알려줘.
    그 기준에 맞춰 나랑 잼민이가 재료·명세서를 맞춰서 넘길게.
    ```
  - **지피티에서 전달할 P0 파일럿 제안**
    ```
    📨 to 코덱이 (from 지피티, via 민식)
    [Option 3를 바로 풀스케일 LDO로 가기 전에, 일단 파일럿 P0로 작은 블록 하나만 코드 레이아웃 해보자는 방향이야.

    P0 목표:
    - sky130 PDK + gdsfactory(or KLayout Python) + Magic으로 **아주 작은 아날로그 primitive 하나(current mirror 혹은 diff pair)**를
      코드 레이아웃 → GDS 생성 → Magic DRC 통과까지 해보기.

    대장이 타겟 블록 정하면 너한테는 이렇게 요청할게:
    1️⃣ 환경 확인: Python 코드에서 gdsfactory(or KLayout)로 NMOS 1개 cell GDS 뽑기 + Magic으로 DRC 한 번 실행.
    2️⃣ 제너레이터 함수 v0: 예) make_current_mirror(w, l, nfingers, type="nmos") — 트랜지스터 instanciate, 소스/드레인 tie, 대칭 배치·간격 확보, 단일 cell export.
    3️⃣ DRC 연동 스크립트(선택): Python/shell 하나로 GDS 생성 → Magic DRC → 로그 출력까지 자동화.

    이 P0의 목적은 “완성도 높은 LDO”가 아니라 “툴체인·코드 레이아웃 방식이 팀에 맞는지 테스트”야. 부담 갖지 말고 실험 느낌으로 가자!]
    ```
  - **지피티에서 전달할 “민무장 P0” 레포 구성/스펙**
    ```
    📨 to 코덱이 (from 지피티, via 민식)
    [모드 변경 공지 ⚠️

    지금은 초기비용 0원 모드라서 sky130 PDK / volare / 외장 SSD 아직 안 쓴다.

    P0 1단계 목표는:
    “WSL + gdsfactory generic tech만으로 Current Mirror 패턴 제너레이터 뼈대를 만드는 것.”
    즉, MOS/PDK 없이 ‘D-A-B-A-B-D 직사각형 배열’ GDS 뽑는 거까지가 네 미션이다.

    1) 레포 구조 제안 (git init 기준)
    p0_current_mirror/
      ├─ README_min_env.md          # 집에서 WSL+gdsfactory만 설치하는 설명
      ├─ env/
      │  └─ install_min_env.sh      # PDK 없이 한 번에 깔리는 설치 스크립트
      └─ src/
         ├─ cm_generator.py         # Current mirror 제너레이터 골격
         └─ run_generator.py        # 제너레이터 호출 테스트

    2) run book (README_min_env.md 요약)
    - PowerShell 관리자: `wsl --install -d Ubuntu-22.04`
    - Ubuntu 터미널: apt 업데이트 → `python3 -m venv ~/sky130_lab/venv_gds` → `pip install gdsfactory`
    - `git clone <레포주소> p0_current_mirror` 후 `cd src && python run_generator.py`
    - 성공 시 `cm_nf2.gds`, `cm_nf4.gds` 생성. (선택) `sudo apt install -y magic` 후 `magic cm_nf2.gds` 로 모양 확인 가능. (`nf_per_leg`=2/4 스윕)

    3) 코드 골격 (요점)
    - `cm_generator.py`: D_L-A1-B1-A2-B2-D_R 직사각형 interdig 패턴.
    - helper `add_device()`로 이름 규칙 유지 → 나중에 sky130 MOS로 교체하기 쉽게.
    - `run_generator.py`: 기본 파라미터(nf_per_leg=2/4, pitch=2.0, w=1.0, h=4.0)로 `cm_nf2.gds`, `cm_nf4.gds` 출력.

    4) 네가 신경 쓸 포인트
    - 구조: helper 함수·이름 규칙을 깨끗하게 유지 (핀/메탈은 추후 추가).
    - 사용성: `source ~/sky130_lab/venv_gds/bin/activate && python run_generator.py` 로 끝나는 단순 플로우.

    위 구조를 먼저 잡아두면, 이후 sky130 PDK 붙일 때 MOS로 치환만 해도 된다.]
    ```

### 코덱이가 변경 사항을 지피티에게 알리는 빠른 방법
- **한 줄 요약**: “무슨 파일을 왜 바꿨는지” 1~2줄로 적기.
- **변경 파일**: 상대 경로와 핵심 함수/블록 이름을 함께 적기.
- **테스트 결과**: 실행 여부와 명령어를 적기(예: `python src/run_generator.py` 통과).
- **궁금한 점/요청**: 지피티에게 확인받고 싶은 포인트를 명확히 질문 형태로 남기기.

복사해서 전달하기:
```text
to 지피티 (from 코덱이, via 민식)
[업데이트 요약]
- 변경: p0_current_mirror/src/cm_generator.py — add_device() 로 D-A-B-A-B-D 패턴 정리, 파라미터 기본값 조정
- 테스트: ✅ python src/run_generator.py (cm_nf2.gds, cm_nf4.gds 생성 확인)
- 질문: 인터디직 폭/피치 기본값 더 적절한 추천치가 있는지?

필요하면 후속 작업이나 리스크(예: sky130 붙일 때 예상 이슈)도 덧붙여 달라고 요청.
```

**📣 공통 호출 멘트 ("주목")**
```
야 잼민이·지피티·코덱이, "주목"이야. 지금부터 내가 전달하는 말이 있어.
- 내가 붙여 넣는 메시지는 각자 네 말투대로 답해 줘.
- 헷갈리면 바로 질문 먼저, 절대 추측 금지.
준비됐으면 한 줄로 "OK"만 먼저 알려줘.
```

## 🧱 P1-sky130 current mirror (PDK 버전)
- 새 디렉터리: `p1_sky130_current_mirror/` (P0-민무장 버전은 그대로 유지)
- 목표: D–A–B–A–B–D 패턴을 **sky130 nMOS PCell**로 배치하고 라벨을 남긴 GDS 생성
- 실행: 가상환경 활성화 후
  ```bash
  cd p1_sky130_current_mirror/src
  python run_cm_sky130.py
  ```
  → `cm_sky130_nf2.gds`, `cm_sky130_nf4.gds` 생성 (KLayout/Magic에서 sky130 PCell인지 확인, `num_pairs`=2/4 스윕)
- 참고: 설치 스크립트 `env/install_sky130_env.sh`는 venv + `gdsfactory`/`sky130` 설치까지만 처리합니다.

## 🧪 테스트 표기 안내
- **⚠️ Not run (docs-only change)**: 코드가 아닌 문서만 수정되어 자동·수동 테스트를 돌리지 않았음을 의미합니다. 필요 시 관련 기능에 맞춰 테스트를 직접 실행해 주세요.

## 📄 GPT에게 파일 한 번에 전달하기
"민식이-코덱이-지피티" 사이에 파일을 던질 때 두 가지 루트가 있습니다. 외부 공유가 가능하면 깃 링크 하나로 끝내고, 불가하면 `export_for_gpt.py`가 모든 파일을 한 덩어리로 만들어 줍니다.

### 1) 외부 공유 OK → GitHub/Gist 링크만 보내기
- 코덱이: 작업 브랜치/레포를 GitHub(또는 비공개 Gist)에 푸시
- 민식 → 지피티: 링크와 리뷰해달라 할 파일 경로만 전달
- 지피티: 웹에서 직접 코드 확인 후 수정안/리뷰를 반환

### 2) 외부 공유 NO → `export_for_gpt.py`로 텍스트 묶음 만들기
> **한줄 답:** `p0_current_mirror/export_for_gpt.py` 출력 본문만 복사해 지피티에게 붙여넣으면 됩니다.

- **위치**: 저장소 루트 기준 `p0_current_mirror/export_for_gpt.py`
- **기본으로 포함되는 파일이 궁금하면**
  ```bash
  python p0_current_mirror/export_for_gpt.py --show-defaults
  ```
  (포함 경로만 출력하고 종료)
- **최소 실행 예시**: 기본 대상(README_min_env.md, install_min_env.sh, cm_generator.py, run_generator.py, sky130 P1 파일 4종)을 묶어서 표준 출력
  ```bash
  python p0_current_mirror/export_for_gpt.py --summary "변경 요약" --summary "테스트 결과"
  ```
  출력된 텍스트 블록을 **그대로 복사**해 지피티에게 전달하면 끝.
- **파일만 지정해 복사**: 헤더 없이 특정 파일만 묶고 싶다면
  ```bash
  python p0_current_mirror/export_for_gpt.py --no-header --output updates_for_gpt.txt p0_current_mirror/src/cm_generator.py
  ```
  `updates_for_gpt.txt`의 내용을 복사해 붙여넣으면 됩니다.

한 번의 명령으로 **to/from 머리말 + 요약 + 파일 내용**을 묶어줍니다.

```bash
# 기본 대상(README_min_env.md, install_min_env.sh, cm_generator.py, run_generator.py) + 머리말까지 출력
python p0_current_mirror/export_for_gpt.py \
  --summary "변경: add_strip 헬퍼 정리" \
  --summary "테스트: ✅ python src/run_generator.py"

# 특정 파일만 골라서 updates_for_gpt.txt에 저장 (머리말 제외)
python p0_current_mirror/export_for_gpt.py \
  --no-header \
  --output updates_for_gpt.txt \
  p0_current_mirror/src/cm_generator.py \
  p0_current_mirror/src/run_generator.py
```

주요 옵션
- `--recipient / --sender / --via`: "to 지피티 (from 코덱이, via 민식)" 머리말을 원하는 이름으로 바꿉니다.
- `--summary`: 한 번에 여러 줄 요약을 붙일 수 있습니다(옵션 반복 사용).
- `--no-header`: 머리말 없이 파일 내용만 내보냅니다.

### 출력 형태 예시
````text
📨 to 지피티 (from 코덱이, via 민식)

[업데이트 요약]
- 변경: add_strip() 로직 정리
- 테스트: ✅ python src/run_generator.py

[export_for_gpt.py 출력]

===== FILE: p0_current_mirror/src/cm_generator.py =====
```python
...파일 내용...
```

===== FILE: p0_current_mirror/src/run_generator.py =====
```python
...파일 내용...
```
````

이 블록을 그대로 지피티에게 붙여넣으면 파일 경로와 내용이 한 번에 전달됩니다.

## 🔄 P0/P1 첫 전체 실행 체크리스트
P0(민무장)와 P1(sky130) 모두 **GDS가 실제로 만들어지는지**를 빠르게 확인하려면 아래 순서대로 따라가세요.

### 1) P0(Generic) GDS 생성
```bash
cd p0_current_mirror
./env/install_min_env.sh      # 최초 1회
python src/run_generator.py   # cm_nf2.gds, cm_nf4.gds 생성
```
- **확인 포인트**: KLayout에서 열었을 때 D–A–B–A–B–D 패턴이 유지되고, `nf_per_leg`=2/4에 따라 전체 길이만 변합니다.

### 2) P1(Sky130) GDS 생성
```bash
cd p1_sky130_current_mirror
./env/install_sky130_env.sh   # 환경에 맞춰 1회 실행
python src/run_cm_sky130.py   # cm_sky130_nf2.gds, cm_sky130_nf4.gds 생성
```
- **확인 포인트**: sky130 PCell이 정상으로 보이고 ABAB 페어 구조가 유지됩니다. `sd_pitch_pair` 값을 바꾸면 A/B 간 간격만 변하는지 체크하세요.

### 3) (선택) Magic DRC 최소 점검
```bash
magic -d XR
```
Magic 콘솔에서:
```
gds read cm_sky130_nf2.gds   ;# 파일명은 생성 결과에 맞게 수정
load cm_sky130_nf2           ;# top cell 이름
select top cell
box values 0 0 0 0
z
drc check
drc why
drc find next
```
- li1/디퓨전 간격·tap 관련 에러가 나오면 README_sky130의 트러블슈팅 섹션을 참고하세요.

### 4) 리뷰용 번들 만들기
실행 결과를 지피티에게 보내고 싶다면 프로젝트 루트에서:
```bash
python p0_current_mirror/export_for_gpt.py \
  --summary "P0+P1 runner/generator 첫 실행 로그" \
  --output updates_for_gpt.txt
```
`updates_for_gpt.txt` 전체를 복사해 붙여넣으면 P0/P1 README·설치 스크립트·제너레이터·드라이버를 한 번에 공유할 수 있습니다.

### ⏩ 한 번에 돌리고 싶다면: run_all_gds.sh
- 전제: 가상환경을 활성화하고 `gdsfactory`(P0 필수)·`sky130`(P1 필수)를 설치한 상태.
- 루트에서 실행:
  ```bash
  ./run_all_gds.sh          # P0+P1 모두 실행
  ./run_all_gds.sh --p0-only  # P0만 실행
  ./run_all_gds.sh --p1-only  # P1만 실행
  ```
- 모듈이 없으면 친절한 오류와 함께 종료하므로, 메시지에 따라 `env/install_min_env.sh` 또는 `env/install_sky130_env.sh`를 먼저 돌린 뒤 재시도하면 된다.

### 🧭 실행 팁
- 가상환경을 활성화한 뒤 `./run_all_gds.sh`를 실행하면 P0/P1 GDS를 한 번에 생성할 수 있습니다.
- 필요한 모듈이 없다면 `env/install_min_env.sh` 또는 `env/install_sky130_env.sh`를 먼저 실행한 뒤 다시 시도하세요.
- KLayout이나 Magic으로 결과 GDS를 열어 D–A–B–A–B–D 패턴과 파라미터 변화가 잘 반영됐는지 확인하면 됩니다.
