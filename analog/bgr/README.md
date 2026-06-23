# Sub-1V Bandgap Reference (BGR) — sky130A, Vdd 1.2 V → Vref 0.8 V

전류모드(**Banba**) 밴드갭 기준전압원. **1.2 V 단일 전원에서 0.8 V 기준전압**을 생성한다.
전통적 전압모드 밴드갭은 출력이 실리콘 밴드갭(~1.25 V)에 고정되어 0.8 V·1.2 V 전원에서
구현 불가하므로, 출력을 임의 전압으로 스케일할 수 있는 전류모드 구조를 사용한다.

`docs/BLOCK_CHECKLIST.md`의 BGR 항목 구현체이며, **전부 sky130A 실소자**로 시뮬레이션한다.

## 측정 결과 (sky130A tt, `make bgr-sim`)
| 항목 | 결과 | 조건 |
|---|---|---|
| Vref @27°C | **0.799 V** | Vdd=1.2 V |
| 온도계수(TC) | **25.0 ppm/°C** | −40 ~ 125°C, span 3.3 mV |
| 기동 | **self-start ✓** | dead-state(Vref=0) 탈출, 0.799 V 정착 |
| 라인 감도 | ~52 mV/V | Vdd 1.1→1.3 V (개선여지: 캐스코드) |

TC 곡선은 +50°C 부근에 정점을 갖는 전형적 밴드갭 곡률을 보인다(1차 보정만 적용).

## 동작 원리
```
              Vdd
      ┌────┬────────┬────────┐
     M1   M2       M3            LVT PMOS 전류미러 (공통 게이트 pg)
      │    │        │
  ┌── na   nb ──┐   └─ vref      ← OTA가 V(na)=V(nb) 강제
  │    │   │    │       │
 Q1   Ra  Rb   R1      Rout
(1x)  │   │    │        │
  │   │   │   Q2(8x)    │
 gnd gnd gnd  gnd      gnd

 V(na)=V_EB1 (CTAT)              ← 다이오드 Q1
 V(nb)-V(nc)=ΔV_EB (PTAT)        ← R1 양단 = V_EB1-V_EB2 = V_T·ln(8)
 각 레그 전류  I = V_EB1/Rb + ΔV_EB/R1   (CTAT/Rb + PTAT/R1)
 Vref = I·Rout = (Rout/Rb)·( V_EB1 + (Rb/R1)·ΔV_EB )
                 └──────────── 브래킷 ≈ 1.25 V 밴드갭 ────────┘
```
- **저TC**: `Rb/R1` 비로 PTAT 양을 맞춰 브래킷의 d/dT를 상쇄(`l_r1`으로 튜닝).
- **0.8 V 생성**: `Rout/Rb < 1`로 1.25 V 브래킷을 **밴드갭 아래로** 스케일(`l_ro`로 튜닝).
  → ppm/°C TC는 `Rout`에 무관하므로 TC와 출력 크기를 **독립적으로** 조정할 수 있다.

### 실측 기반 사이징 (sky130 PNP)
| | 27°C | 기울기 |
|---|---|---|
| V_EB1 (1×) | 0.722 V | −1.79 mV/°C (CTAT) |
| ΔV_EB (1× vs 8×) | 54.6 mV | +0.184 mV/°C (PTAT) |

→ 영TC 조건 `d/dT[V_EB1 + M·ΔV_EB]=0`. 1차 손계산은 M≈9.8이나, 저항 단자
기생(rend/rhead)과 동작전류 차이를 반영해 **시뮬레이션으로 M≈13(l_r1=21)** 로 튜닝.

## 왜 LVT 코어/부하 PMOS인가
regular-VT pfet로 레그 전류(~2 µA)를 흘리는 게이트 바이어스는 **pg≈0.15 V(접지 근처)**
라, 단순 5T OTA의 출력 범위 밖이다. **LVT pfet**(낮은 |Vth|)을 쓰면 같은 전류의 게이트
바이어스가 **mid-rail(~0.64 V)** 로 올라와 단단 NMOS입력/PMOS부하 OTA로 구동 가능해진다.
OTA 부하도 LVT로 맞춰 출력 공통모드를 코어 요구 바이어스에 정렬했다. (이 정렬이 깨지면
루프가 레일로 latch — bring-up 중 실제로 관찰됨.)

## 구성 소자 (전부 sky130A)
| 블록 | 소자 | 크기/개수 |
|---|---|---|
| 코어 미러 M1/M2/M3 | `pfet_01v8_lvt` | W=10 L=1 ×3 |
| Q1 / Q2 | `pnp_05v5_W3p40L3p40` | 1× / 8× |
| Ra, Rb | `res_high_po_0p35` | L=276 (~250 kΩ) |
| R1 | `res_high_po_0p35` | L=21 (~19 kΩ) |
| Rout | `res_high_po_0p35` | L=164.5 (~149 kΩ) |
| OTA 입력쌍 / tail | `nfet_01v8` | W=8 / W=4, L=1 |
| OTA 부하 | `pfet_01v8_lvt` | W=8 L=1 |
| 기동 (det/pd/kick) | `pfet/nfet_01v8` | W=1·2 |

## 파일
```
analog/bgr/
├── bgr_core.spice    # .subckt sky130_bgr (vdd vref) — 코어+OTA+기동
├── tb_tc.spice       # 온도 스윕 → TC
├── tb_startup.spice  # Vdd 스텝 → 기동/정착
├── tb_line.spice     # Vdd 스윕 → 라인 감도
└── run.sh            # 셋 모두 실행 + 요약 출력
```

## 실행
```bash
pip install volare
export PDK_ROOT=$HOME/.volare
volare enable --pdk sky130 c6d73a35f524070e85faff4a6a9eef49553ebc2b
make bgr-sim       # 또는: bash analog/bgr/run.sh
```
> **검증 방식**: dead-state(Vref=0)도 유효한 DC 해이므로 bare `.op`/`.dc`는 0으로
> 수렴할 수 있다. 그래서 모든 TB는 **Vdd 램프 트랜지언트**로 풀어 실제 기동회로가
> 라이브 동작점으로 끌어올리도록 한다(물리적으로 옳은 검증).

## 다음 단계 (개선 로드맵)
- [ ] **라인 감도 개선**: 코어 미러에 캐스코드 추가 / OTA 게인↑ → 목표 < 5 mV/V
- [ ] **트림**: Rout(또는 R1)에 비트 단위 트림 탭 → 초기 오차/공정 산포 보정
- [ ] **곡률보정**: 2차 항 추가로 TC < 10 ppm/°C
- [ ] **PSRR/노이즈**: `.ac`(시동 후) PSRR, `.noise` 출력 노이즈
- [ ] **몬테카를로**: 미스매치 σ(Vref) — sky130 `.lib` mismatch 스위치 활용
- [ ] **PVT 코너**: ss/ff × Vdd±10% 자동 스윕 (`analog/sizing` 코너 루프 연동)
- [ ] **레이아웃**: PNP/저항 common-centroid·더미 → Magic/KLayout → LVS/PEX 후 재검증
