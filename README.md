# 1인 Fabless 설립 프로젝트

오픈소스 EDA 기반 **1인(혼자) 운영 fabless 반도체 회사** 설립을 위한 계획 저장소.

- **전략:** 오픈소스 EDA 부트스트랩(라이선스 비용 0)
- **도메인:** 혼성신호(Mixed-Signal) SoC — 디지털 코어 + 아날로그 IP
- **수익 모델:** 자체 칩 제품 판매

## 문서

- 📘 **[단계별 실행 계획 & 큰 그림 → `docs/FABLESS_PLAN.md`](docs/FABLESS_PLAN.md)**
  - 시뮬레이션 라이선스 → PDK 선정 → MPW 비용 → 설계 자동화/검증 →
    아날로그/디지털 회로·레이아웃 자동화 → 타겟 회로 설정 → 제작 → 판매
- 🛠 [환경 구축 `docs/SETUP.md`](docs/SETUP.md) · 📋 [타겟 회로 PRD 템플릿 `docs/PRD_TEMPLATE.md`](docs/PRD_TEMPLATE.md) · ✅ [진행 체크리스트 `docs/ROADMAP.md`](docs/ROADMAP.md)

## 빠른 시작 (Codespaces / devcontainer)

이 repo를 **GitHub Codespace로 열면** `.devcontainer/`가 `iverilog`·`ngspice`·`cocotb`를
자동 설치한다. 열린 뒤 바로:

```bash
make digital-sim       # 디지털 회귀 (cocotb + Icarus)
make analog-autosize   # 전압 도메인 인지 아날로그 사이징 (소자/구조/사이징 자동 선정)
```

> 레이아웃·RTL→GDS(OpenLane2, Magic, KLayout, sky130 PDK)까지 필요하면
> `hpretl/iic-osic-tools` 이미지를 사용한다 (docs/SETUP.md 참고).

## 구조
```
digital/   디지털 레인: 레퍼런스 RTL + cocotb 회귀 + OpenLane2 설정
analog/    아날로그 레인: 전압 도메인 인지 사이징 자동화 (tech/topology/autosize)
docs/      계획·환경·PRD·로드맵 문서
Makefile   digital-sim / analog-autosize / digital-gds
```
