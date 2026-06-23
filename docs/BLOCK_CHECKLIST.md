# 아날로그 코어 블록 설계 체크리스트 — OTA · LDO · BGR · OSC · PLL

혼성 SoC의 전원·기준·클럭 체계를 구성하는 다섯 코어 블록의 설계·검증 체크리스트.
각 블록은 **스펙 확정 → 구조(topology) 선정 → 사이징 → 검증 → 레이아웃 sign-off**의
공통 흐름을 따른다(계획서 §2.5–§2.6, `analog/README.md`의 파이프라인과 동일 사상).

블록 간 의존성이 있으므로 **권장 설계 순서는 BGR → OTA → LDO → OSC → PLL** 이다.
(기준전압이 먼저, 그 위에 증폭기·레귤레이터, 그 다음 클럭 계통.)

표기: `[ ]` 미착수 · `[~]` 진행중 · `[x]` 완료.
각 블록의 `자동화 훅`은 `analog/sizing/`(tech/topology/autosize)에 토폴로지를
추가했을 때 연결되는 지점을 가리킨다.

---

## 0. 블록 공통 (모든 블록에 적용)
- [ ] 전원 도메인 확정 → `tech.select_domain(Vdd)`로 소자 flavor 결정 (1.8V thin-ox / 5V thick-ox)
- [ ] PVT 코너 정의 (tt/ss/ff × −40/27/125°C × Vdd ±10%)
- [ ] 측정 testbench를 `.measure` 기반으로 작성 (수동 판독 금지 — 회귀 자동화 전제)
- [ ] 목표/실측 비교 표를 PRD(`docs/PRD_TEMPLATE.md`)에 기록
- [ ] 스키매틱(Xschem) → DRC/LVS(Magic/Netgen) → PEX → 포스트레이아웃 재검증

---

## 1. OTA (Operational Transconductance Amplifier)
LDO 에러앰프·PLL 루프필터·BGR 앰프의 공용 빌딩블록. **가장 먼저 안정화할 코어.**

### 스펙
- [ ] DC 게인 (A_DC) 목표 [dB]
- [ ] 단위이득 대역폭 (GBW) / 위상여유 (PM ≥ 60°)
- [ ] 입력 공통모드 범위 (ICMR) / 출력 스윙
- [ ] 슬루레이트 (SR) / 정착시간
- [ ] 입력 오프셋 / 1/f·thermal 노이즈 / CMRR / PSRR
- [ ] 정전류 (I_q) / 부하 용량 (C_L)

### 구조 선정
- [ ] 5-트랜지스터 OTA (단단, 저게인) — 1차 후보
- [ ] 텔레스코픽 / 폴디드-캐스코드 (고게인·고대역) — 게인 부족 시 승격
- [ ] 2단 밀러 보상 (큰 스윙·구동) — 출력 스윙 요구 시
- [ ] 보상 방식 결정 (Miller Cc / Cc+Rz nulling / Ahuja)

### 사이징·검증
- [ ] gm/Id 방법론으로 동작점 설정 (자동화 훅: `autosize.py` W 스윕 → gm/Id 대체)
- [ ] `.op` 전 소자 포화영역 확인 (Vds > Vov)
- [ ] AC: 게인·GBW·PM (`.meas ac`)
- [ ] 트랜지언트: SR / 정착 (스텝 응답)
- [ ] 노이즈(`.noise`) / PSRR / 몬테카를로 오프셋
- [ ] 모든 PVT 코너에서 PM ≥ 60° 유지

### 레이아웃
- [ ] 입력쌍 common-centroid + 더미 / 매칭 정렬
- [ ] DRC / LVS clean → PEX → PM 재확인

---

## 2. LDO (Low-Dropout Regulator)
OTA(에러앰프) + BGR(기준) 위에 올라가는 블록 → **OTA·BGR 검증 후 진행.**

### 스펙
- [ ] V_out / I_load,max / 드롭아웃 전압 (V_do @ I_max)
- [ ] 정적전류 (I_q) / 효율
- [ ] 라인 레귤레이션 / 로드 레귤레이션
- [ ] PSRR @ 1k/100k/1M Hz / 출력 노이즈
- [ ] 로드 스텝 과도응답 (언더슈트/오버슈트, 정착)
- [ ] 안정성: C_out / ESR 범위 (외장 vs 내장형)

### 구조 선정
- [ ] 패스소자: PMOS(저드롭아웃) vs NMOS(고PSRR, 헤드룸 필요)
- [ ] 보상: 외장 캡(ESR 제로) vs 내장형(캡리스 + 밀러/Q-reduction)
- [ ] 에러앰프 = §1 OTA 재사용
- [ ] 기준 = §3 BGR 재사용

### 사이징·검증
- [ ] 패스소자 사이징 (V_do @ I_max 충족)
- [ ] 루프게인 AC → PM ≥ 60° (무부하/최대부하 양 극단)
- [ ] 로드 스텝 트랜지언트 (예: 1mA↔I_max, 1µs 에지)
- [ ] 라인 스텝 / PSRR 스윕
- [ ] 기동(soft-start) / 단락 보호 동작
- [ ] PVT × C_out/ESR 코너 전부 안정

### 레이아웃
- [ ] 패스소자 전류밀도·EM 확인, 켈빈 센스
- [ ] DRC / LVS clean → PEX → 안정성 재확인

---

## 3. BGR (Bandgap Reference)
체계의 기준전압원 → **가장 먼저 설계**(OTA/LDO/PLL이 의존).

### 스펙
- [ ] 기준전압 V_ref [V] / 온도계수 (TC) [ppm/°C]
- [ ] 라인 감도 / PSRR / 기동시간
- [ ] 정적전류 / 트림 비트 수 (있다면)
- [ ] 출력 노이즈 / 면적

### 구조 선정
- [ ] BJT(vertical PNP) vs MOS-only(서브스레숄드) 기준
- [ ] 전압모드(전통형) vs 전류모드(저전압 Banba형)
- [ ] 앰프형(OTA 필요) vs 자기바이어스형
- [ ] 곡률보정 유무

### 사이징·검증
- [ ] PTAT / CTAT 합성 → 1차 TC 상쇄 확인
- [ ] V_ref vs 온도 스윕 (−40~125°C) → TC 측정 (`.meas`)
- [ ] **기동 회로** 동작 검증 (zero-current 상태 탈출)
- [ ] 라인 스윕 / PSRR / 노이즈
- [ ] 트림 코드별 V_ref 분포 (몬테카를로)
- [ ] PVT 코너 TC 목표 이내

### 레이아웃
- [ ] BJT/저항 common-centroid·더미, 열 대칭
- [ ] DRC / LVS clean → PEX → TC 재확인

---

## 4. OSC (Oscillator)
온칩 클럭 소스. PLL의 기준/혹은 PLL 내 VCO로 사용 → **PLL 전에 단독 검증.**

### 스펙
- [ ] 발진 주파수 f_osc / 튜닝 범위 (VCO인 경우 K_VCO)
- [ ] 주파수 정확도 / 온도·전압 드리프트 [%]
- [ ] 위상잡음 [dBc/Hz @ offset] / 지터 (RMS, p-p)
- [ ] 기동시간 / 정적전류 / 듀티사이클
- [ ] 타입: RC relaxation / ring / LC / 크리스털(외장)

### 구조 선정
- [ ] RC relaxation (저면적·중간정밀, 트림 필요)
- [ ] 링 오실레이터 / 전류기아 링 (VCO용, 넓은 튜닝)
- [ ] LC-VCO (저위상잡음, 면적 큼)
- [ ] 기준전류/전압 = §3 BGR 연동 (드리프트 보상)

### 사이징·검증
- [ ] 트랜지언트 발진 기동 확인 (초기조건 없이)
- [ ] f_osc 측정 (`.meas tran`) / 듀티
- [ ] VCO: 제어전압 스윕 → f-V 곡선 / K_VCO 선형성
- [ ] 위상잡음(`.noise`/PSS-pnoise 상응) — ngspice 한계 시 근사
- [ ] f vs PVT 드리프트 / 트림 코드 분포
- [ ] 기동시간 / 전류 코너

### 레이아웃
- [ ] 타이밍 핵심소자 매칭, 공급 디커플링
- [ ] DRC / LVS clean → PEX → f_osc 재확인

---

## 5. PLL (Phase-Locked Loop)
**최상위 통합 블록** — OSC(VCO) + BGR(바이어스) + (필요시) OTA를 모두 사용 → **마지막.**

### 스펙
- [ ] 출력 주파수 / 분주비 (N, 정수 vs 프랙셔널)
- [ ] 기준 주파수 f_ref / 락 시간
- [ ] 위상잡음 / 지터 (RMS, p-p) / 스퍼
- [ ] 루프대역폭 / 위상여유 (≥ 60°) / 댐핑 (ζ ≈ 0.7)
- [ ] 정적전류 / 락 검출

### 구조 선정
- [ ] 차지펌프 PLL (CP-PLL) vs ADPLL
- [ ] PFD + 차지펌프 + 루프필터(2nd/3rd order)
- [ ] VCO = §4 OSC 재사용 / 바이어스 = §3 BGR
- [ ] 분주기: 정수 vs ΔΣ 프랙셔널

### 사이징·검증
- [ ] 루프 파라미터 산출 (I_cp, R/C, K_VCO, N → ω_n, ζ)
- [ ] 선형 모델(연속시간) 루프게인 AC → BW / PM 확인
- [ ] PFD/CP 데드존·전류 부정합 점검
- [ ] 트랜지언트 락 캡처 (주파수 스텝 → 락 시간/오버슈트)
- [ ] 지터/스퍼 (가능 범위에서) / 분주비 전환 글리치
- [ ] PVT 코너 락 유지 / PM ≥ 60°

### 레이아웃
- [ ] CP·LPF 매칭, VCO 격리(가드링·전용 공급)
- [ ] DRC / LVS clean → PEX → 루프 안정성 재확인

---

## 의존성 그래프 (설계 순서 근거)
```
        BGR (기준전압)
       /   |        \
     OTA   |          OSC ── (VCO)
       \   |         /        |
        \  |        /         |
         LDO       BGR bias   |
                    \         |
                     \        |
                      PLL ◀───┘  (OSC/VCO + BGR + OTA 통합)
```
- **BGR** 먼저: 모든 블록의 기준/바이어스.
- **OTA**: LDO 에러앰프·BGR 앰프·PLL 보조의 공용 코어.
- **LDO**: OTA+BGR 의존.
- **OSC**: BGR 바이어스 의존, PLL의 VCO.
- **PLL**: 전부 통합 — 마지막.

## 자동화 연계 (`analog/sizing/`)
현재 자동화기는 단일단/2단 게인 구조만 다룬다. 각 블록을 파이프라인에 태우려면:
1. `topology.py`에 해당 구조의 ngspice 덱 제너레이터 추가 (예: `five_transistor_ota`, `pmos_ldo_loop`).
2. `autosize.py`의 합격 판정식에 블록별 지표 추가 (PM, TC, 락시간 등).
3. W 상수 스윕 → **gm/Id + MOBO** 로 교체(계획서 §2.6) 후 PVT 코너 루프 추가.

각 체크리스트 항목이 green 이 되면 위 `[ ]`를 `[x]`로 갱신하고
`docs/ROADMAP.md` Phase 2 항목과 동기화한다.
