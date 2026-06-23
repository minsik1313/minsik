# 1인 Fabless 설립 — 단계별 Plan & 큰 그림

> 1인(혼자) 운영을 전제로, **오픈소스 EDA 부트스트랩 + 혼성신호(Mixed-Signal) SoC +
> 자체 칩 제품 판매**를 목표로 하는 실행 로드맵.

## 0. 전제와 현실 점검

확정된 방향:
- **EDA 전략: 오픈소스 우선(부트스트랩)** — 라이선스 비용 0, 저비용 MPW
- **도메인: 혼성신호(Mixed-Signal) SoC** — 디지털 코어 + 아날로그 IP 통합
- **수익 모델: 자체 칩 제품 판매**

> ⚠️ **현실 점검**
> - 2025년 **Efabless 폐업**으로 오픈 실리콘 생태계가 재편됨 → 후속 **ChipFoundry chipIgnite**.
> - **디지털 자동화는 거의 완전 자동(OpenLane2/OpenROAD)** = 1인의 강점.
> - **아날로그 자동화(사이징·레이아웃)는 아직 미성숙** = 자동화 + 수작업 혼합이 현실.
> - 따라서 "완전 자동 1인 fabless"는 디지털을 척추로 삼고, 아날로그 IP를 자산화하며
>   단계적으로 성장하는 구조가 합리적이다.

---

## 1. 큰 그림 (Big Picture)

### 1.1 가치사슬 한눈에

```
[아이디어/스펙]
      │
      ▼
┌───────────────── 환경 구축 (Phase 0) ─────────────────┐
│ 오픈 EDA 툴체인 + PDK + Docker(IIC-OSIC-TOOLS)          │
└────────────────────────────┬──────────────────────────┘
                             ▼
        ┌──────────────── 설계 (Phase 1~2) ────────────────┐
        │  디지털 레인              아날로그 레인            │
        │  RTL(Verilog)             스펙→토폴로지            │
        │   │ Yosys 합성             │ 사이징(ngspice/MOBO)  │
        │   │ OpenROAD P&R           │ Xschem 스키매틱       │
        │   ▼ OpenLane2 (자동)       ▼ Magic/KLayout(반자동) │
        │  GDS(디지털 블록)         GDS(아날로그 IP)         │
        └───────────────┬───────────────┬──────────────────┘
                       ▼               ▼
                ┌──── 통합 & 검증 (Sign-off) ────┐
                │ DRC(Magic/KLayout) · LVS(Netgen)│
                │ PEX · 포스트레이아웃 시뮬       │
                │ Caravel/ChipFoundry 하네스 통합 │
                └───────────────┬────────────────┘
                               ▼
                ┌──── 제작 Tapeout (Phase 3) ────┐
                │ MPW 셔틀 제출 → 웨이퍼/다이      │
                └───────────────┬────────────────┘
                               ▼
        ┌──── 평가/양산 (Phase 4) ────┐   ┌──── 판매 (Phase 5) ────┐
        │ 패키징 · 보드 · 특성평가     │──▶│ 모듈/평가보드/소량양산  │
        └─────────────────────────────┘   └────────────────────────┘
```

### 1.2 단계별 타임라인·비용 요약 (오픈소스 부트스트랩 기준)

| Phase | 내용 | 기간(목표) | 핵심 비용 |
|---|---|---|---|
| 0 | 툴체인·PDK·인프라 구축 | 1~2개월 | 거의 0 (PC/워크스테이션만) |
| 1 | 디지털·아날로그 자동화 파이프라인 셋업 | 2~3개월 | 0 |
| 2 | 타겟 회로 설계·검증(sign-off) | 3~6개월 | 0 (인건/시간) |
| 3 | MPW 시제작(첫 테이프아웃) | 1회 | **TinyTapeout ~$0.3k / chipIgnite ~$10k** |
| 4 | 패키징·평가·재설계 | 2~4개월 | 패키징·PCB·계측 수백~수천 $ |
| 5 | 소량 양산·판매 | 지속 | chipIgnite 양산 ~$20/unit(1k qty) 수준부터 |

> **2단 부스터 전략:** "싸게 한 번 굽고 배운다."
> **TinyTapeout(학습용 초저가 테이프아웃) → chipIgnite(실제 제품 셔틀).**

---

## 2. 항목별 상세 실행 계획

### 2.1 Simulation License 취득
- **오픈소스 = 라이선스 불필요(핵심 비용 절감 포인트).**
  - 회로 시뮬: **ngspice**(GPL, SPICE), 대규모/혼성은 **Xyce**(병렬) 병행
  - 디지털 시뮬: **Verilator**(고속), **Icarus Verilog**, 파형 **GTKWave/Surfer**
  - 검증 프레임워크: **cocotb**(파이썬 테스트벤치)
- 상용이 꼭 필요해질 때만(예: 정밀 RF/고전압): Cadence Spectre·Synopsys HSPICE를
  스타트업/대학 프로그램 또는 Europractice 멤버십으로 할인 확보 → **2차 고려**.
- **Action:** ngspice + Xyce + Verilator + cocotb 설치·검증(샘플 회로/RTL 동작 확인).

### 2.2 PDK 선정

| PDK | 노드 | 특징 | 혼성신호 적합성 | 추천도 |
|---|---|---|---|---|
| **SkyWater sky130** | 130nm CMOS | 가장 성숙한 오픈 생태계, ChipFoundry/Cadence 셔틀 | 디지털+기본 아날로그 | ★★★ (기본 선택) |
| **IHP sg13g2** | 130nm BiCMOS | **SiGe HBT(RF)** 포함, 완전 오픈 검증(DRC/LVS/PEX), TinyTapeout 지원 | RF·고성능 아날로그 | ★★☆ (RF면 1순위) |
| GF gf180mcu | 180nm CMOS | 5메탈, Wafer.Space 셔틀 | 고전압·아날로그 | ★★☆ |

- **권장: sky130A로 시작** — 레퍼런스·튜토리얼·셔틀이 가장 풍부, 혼성 SoC 하네스 존재.
  RF/SiGe가 타겟이면 sg13g2 병행.
- **Action:** `open_pdks` 설치 또는 **IIC-OSIC-TOOLS** Docker 사용
  (sky130A·gf180mcuD·ihp-sg13g2 + 전 툴 동봉) → PDK 1개로 표준화.

### 2.3 MPW 비용

| 서비스 | 공정 | 진입 비용(대략) | 용도 |
|---|---|---|---|
| **TinyTapeout** | sky130/gf180/ihp-sg13g2 | **~$100–300/타일** | 학습·초저가 첫 테이프아웃 |
| **ChipFoundry chipIgnite** (Efabless 후속) | sky130 | **~$10k(소량)**, 양산 ~$20/unit@1k | 실제 제품 셔틀(하네스 SoC) |
| SkyWater FastShuttle(직접) | sky130 | 블록당 ~$10k–12k | 직접 제출 |
| Europractice | 다수 노드 | 멤버십·노드별 상이(유럽) | 다양한 공정 접근 |
| GF GlobalShuttle / Tower / Samsung MPW | 상용 노드 | 고가($수만~) | 향후 스케일업 |

- **전략:** ① TinyTapeout로 플로우 전체를 싸게 1회 관통 → ② chipIgnite로 제품 테이프아웃.
- **Action:** 셔틀 캘린더(마감일) 기준으로 설계 일정 역산. 첫 예산 라인 = TinyTapeout 1슬롯.

### 2.4 1인 설계 자동화 및 검증 (전체 파이프라인의 척추)
- **컨테이너화로 재현성 확보:** IIC-OSIC-TOOLS Docker 단일 환경.
- **Make/스크립트 기반 원클릭 플로우:** RTL→GDS, 스키매틱→사이징→레이아웃→sign-off를
  스크립트로 묶어 "혼자서도 회귀(regression) 가능"하게.
- **검증(Sign-off) 표준:**
  - **DRC:** Magic / KLayout 룰덱
  - **LVS:** Netgen (레이아웃 vs 스키매틱)
  - **PEX → 포스트레이아웃 시뮬:** Magic 기생추출 → ngspice 재검증
  - **디지털 STA/기능검증:** OpenSTA, cocotb 회귀
- **버전관리·CI:** Git + GitHub Actions로 DRC/LVS/시뮬 자동 회귀(테이프아웃 전 게이트).
- **Action:** 작은 레퍼런스 블록으로 "RTL→GDS 통과 + LVS clean"을 먼저 달성해 플로우 신뢰 확보.

### 2.5 아날로그 회로설계 자동화 (사이징·토폴로지)
- **현실:** 토폴로지 선택·노드별 사이징은 아직 인간 주도. 자동화는 "보조".
- **활용 가능 도구:**
  - **사이징 최적화:** ngspice 스윕 + **MOBO(다목적 베이지안 최적화)** 루프,
    오픈소스 **Oceane**(OTA/OpAmp/비교기 템플릿)
  - **AI 보조(2025~):** LLM 에이전트형(AutoSizer·AnalogAgent 등)으로 스펙→초기 사이징
    가이드 — 실험적, 검증 필수
  - **PVT 코너 스윕** 자동화로 강건성 확보
- **전압 도메인 인지(중요):** 자동화는 반드시 **전원 전압 → 소자 flavor → 구조 → 사이징**을
  연동해야 한다. sky130 기준 1.8V 코어는 thin-oxide(`nfet_01v8`), 3.3~5V는
  thick-oxide(`nfet_g5v0d10v5`)를 써야 하며, 소자 **Vds 정격**이 전원을 못 덮으면 자동 승격.
  게인 부족 시 단단(common-source)→다단(two-stage)으로 구조도 자동 승격.
  → 구현: `analog/sizing/`(`tech.py` 도메인/소자 라이브러리, `topology.py` 구조,
  `autosize.py` 오케스트레이터). 실행 `make analog-autosize`.
- **Action:** 핵심 블록(bandgap, LDO, comparator 등)별 파라미터화 스키매틱 + 위 자동화로
  사이징. 현재는 generic Level-1 데모이며, sky130 `.lib` + gm/Id + MOBO로 전환.
  결과는 항상 수작업 검토.

### 2.6 아날로그 레이아웃 자동화
- **현실:** 가장 미성숙 영역. 정합(matching)·기생·웰 등은 수작업 비중 큼.
- **접근:**
  - **연구툴 시도:** **ALIGN**, **MAGICAL**(netlist→GDSII 자동 배치/배선) — 일부 블록 한정,
    산출물 검증·수정 전제
  - **생산성 도구:** **Magic**(공정 친화) + **KLayout**(파이썬 스크립팅, PCell/제너레이터) 병용
  - **재사용:** 잘 만든 셀(전류미러·차동쌍 등)을 파라미터화 제너레이터로 라이브러리화 → 생산성↑
- **Action:** 자주 쓰는 아날로그 프리미티브를 KLayout 파이썬 제너레이터로 자산화. 자동툴은 보조로만.

### 2.7 디지털 회로설계 자동화
- **성숙도 높음 — 1인 생산성의 핵심.**
  - RTL: **Verilog/SystemVerilog**, 필요 시 고수준은 **Chisel/Amaranth**
  - 합성: **Yosys**
  - 검증: **cocotb + Verilator**(고속 시뮬), 포멀 일부 **SymbiYosys**
- **Action:** RISC-V 관리코어 또는 가속기 등 디지털 블록을 RTL로 확보, cocotb 회귀 구축.

### 2.8 디지털 레이아웃 자동화
- **거의 완전 자동 — 강점 영역.**
  - **OpenLane2 / OpenROAD**(Yosys+OpenROAD+Magic+Netgen)로 **RTL→GDSII 원클릭**
  - sky130 타깃 floorplan/배치/CTS/라우팅/STA/DRC/LVS 자동
- **Action:** 디지털 블록을 OpenLane2로 GDS화하고 sign-off clean 달성.

### 2.9 Target 회로 설정 (제품 정의)
- **혼성 SoC 1차 타겟 후보(1인 난이도·시장성 균형):**
  1. **센서 프론트엔드 SoC** — 아날로그 AFE(증폭/필터) + ADC + 디지털 처리/I²C·SPI. (IoT 수요↑)
  2. **저전력 PMIC형 블록** — LDO/bandgap/레퍼런스 + 디지털 제어. (재사용·범용성↑)
  3. **RISC-V MCU + 아날로그 IP** — chipIgnite Caravel 하네스에 자연스럽게 적합.
- **선정 기준:** ① 1인이 검증 가능한 복잡도 ② sky130에서 실현 가능 ③ 명확한 구매자.
- **권장 1순위: 센서 프론트엔드 SoC**(혼성신호 가치 + 모듈 판매 용이).
- **Action:** 1개를 PRD(스펙·핀맵·인터페이스·타깃가격)로 확정.

### 2.10 제작 (Tapeout & Fabrication)
- **하네스 통합:** chipIgnite **Caravel** SoC 하네스(관리용 RISC-V + 사용자 영역)에
  디지털/아날로그 블록 통합 → 셔틀 제출 형식 충족.
- **테이프아웃 게이트 체크리스트:** DRC clean · LVS clean · 안테나/밀도 룰 ·
  포스트레이아웃 시뮬 통과 · 핀/패드 확인.
- **2단 전략:** (a) TinyTapeout로 소블록 선검증 → (b) chipIgnite로 제품 테이프아웃.
- **Action:** 셔틀 마감 D-day 기준 freeze 일정 수립, 제출.

### 2.11 판매 (사업화)
- **자체 칩 제품 판매 경로:**
  - **형태:** 베어다이 → 패키징(OSAT/저가 패키지) → **평가보드/모듈** 형태로 부가가치 판매
  - **채널:** 자사몰, Tindie/Crowd Supply(메이커·소량), 이후 디스트리뷰터/대리점
  - **문서:** 데이터시트·레퍼런스 디자인·드라이버/SDK 제공이 구매 전환의 핵심
  - **소량 양산:** chipIgnite 양산옵션(예: ~$20/unit@1k)으로 초도 물량 확보 후 수요검증
- **사업 인프라:** 사업자 등록, 단가/원가표, 품질(기본 신뢰성·동작온도) 명시.
- **Action:** 첫 제품의 데이터시트 초안 + 평가보드 + 랜딩페이지로 사전수요 테스트.

---

## 3. 권장 오픈소스 툴 스택 (요약)

| 단계 | 도구 |
|---|---|
| 환경 | IIC-OSIC-TOOLS (Docker), open_pdks |
| PDK | sky130A (+필요시 ihp-sg13g2) |
| 회로 시뮬 | ngspice, Xyce |
| 스키매틱 | Xschem |
| 아날로그 레이아웃 | Magic, KLayout(파이썬 제너레이터), (실험) ALIGN/MAGICAL |
| 아날로그 사이징 | ngspice 스윕 + MOBO, Oceane, (실험) LLM 에이전트 |
| 디지털 RTL/검증 | Verilog/SV, Yosys, Verilator, cocotb, SymbiYosys |
| 디지털 RTL2GDS | OpenLane2 / OpenROAD |
| Sign-off | Magic DRC, KLayout DRC, Netgen LVS, Magic PEX, OpenSTA |
| 통합/제작 | Caravel(chipIgnite) 하네스 |
| CI/형상관리 | Git + GitHub Actions (DRC/LVS/sim 회귀) |

---

## 4. 90일 부트스트랩 체크리스트 (빠른 시작)

- [ ] IIC-OSIC-TOOLS Docker 설치 → sky130A PDK 동작 확인
- [ ] ngspice로 간단한 OpAmp/인버터 시뮬 통과
- [ ] Verilog 카운터 → OpenLane2로 RTL→GDS 통과 + LVS clean
- [ ] Xschem→Magic로 작은 아날로그 블록 1개 레이아웃 + DRC/LVS clean
- [ ] TinyTapeout 캘린더 확인, 학습용 슬롯 1개 목표 설정
- [ ] 타겟 제품(센서 프론트엔드 SoC 등) PRD 초안 작성

---

## 참고 (Sources)
- ChipFoundry chipIgnite (Efabless 후속): https://chipfoundry.io/
- SkyWater MPW/FastShuttle & sky130 PDK: https://www.skywatertechnology.com/
- open_pdks 설치기: https://github.com/RTimothyEdwards/open_pdks
- IHP sg13g2 AMS 튜토리얼: https://iic-jku.github.io/ihp-sg13g2-ams-chip-template/
- OpenLane (RTL2GDS): https://github.com/The-OpenROAD-Project/OpenLane
- 아날로그 자동화 현황: MAGICAL https://ieeexplore.ieee.org/document/8942060/ ,
  awesome-Analog-IC-Design-Automation https://github.com/parkerluxu/awesome-Analog-IC-Design-Automation
- Europractice 일정·가격: https://europractice-ic.com/services/fabrication/
- TinyTapeout: https://tinytapeout.com/
