# 실행 로드맵 체크리스트

`FABLESS_PLAN.md`의 단계를 추적하는 체크리스트. 진행하며 갱신한다.

## Phase 0 — 환경 구축
- [x] 오픈소스 시뮬레이터 설치 (iverilog, ngspice)
- [x] 디지털 검증 프레임워크 설치 (cocotb)
- [ ] IIC-OSIC-TOOLS 컨테이너 + sky130A PDK 셋업
- [ ] Xschem / Magic / KLayout / Netgen 동작 확인
- [ ] OpenLane2 설치 및 sky130A 타겟 확인

## Phase 1 — 자동화 파이프라인
- [x] 디지털 레퍼런스 블록 RTL (`digital/rtl/boxcar_filter.v`)
- [x] 디지털 회귀(cocotb) green (`make digital-sim`)
- [x] 전압 도메인 인지 아날로그 자동화: 소자 flavor·구조·사이징 선정 (`make analog-autosize`)
- [x] Codespaces devcontainer (`.devcontainer/`) — 열면 툴 자동설치
- [x] CI 회귀 워크플로 (`.github/workflows/ci.yml`)
- [ ] 디지털 RTL→GDS(OpenLane2) sign-off clean
- [ ] 아날로그 블록 Xschem→Magic 레이아웃 + DRC/LVS clean
- [ ] 자동화를 sky130 모델 + gm/Id + MOBO로 전환 (현재 generic Level-1 데모)

## Phase 2 — 타겟 회로 설계·검증
- [ ] PRD 확정 (`docs/PRD_TEMPLATE.md` 작성)
- [ ] 아날로그/디지털 블록 통합
- [ ] PEX 후 포스트레이아웃 시뮬 통과

## Phase 3 — 제작 (Tapeout)
- [ ] TinyTapeout 학습용 테이프아웃 1회
- [ ] chipIgnite(Caravel) 하네스 통합 + 제품 테이프아웃

## Phase 4 — 평가·양산
- [ ] 패키징 / 평가보드 제작
- [ ] 특성 평가 / 재설계

## Phase 5 — 판매
- [ ] 데이터시트 + 레퍼런스 디자인
- [ ] 랜딩페이지 / 채널(Tindie/Crowd Supply)
- [ ] 소량 양산
