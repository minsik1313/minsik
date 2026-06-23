# MTU 실행 결과 요약 (Phase 0–2)

생성: `make lint && python3 sim.py --waves` 실행 결과를 정리한 것. 원본 로그/XML/VCD는 이 디렉터리에 보관.

## 1. Verilator Lint

```
$ verilator --lint-only -Wall -Wno-DECLFILENAME --timing \
    rtl/pe/pe.sv rtl/mxu/systolic_array.sv rtl/mtu_top.sv --top-module mtu_top
```

**결과: 경고/에러 0건 (exit code 0)** → [`lint.log`](lint.log)

## 2. cocotb 테스트 (Icarus Verilog 시뮬레이션)

전체 3개 빌드(pe, systolic_array, mtu_top)에서 **7/7 테스트 전부 통과**, 실패 0건.
전체 로그: [`test_run.log`](test_run.log) · JUnit XML: [`xml/`](xml/)

| 빌드 (DUT) | 배열 크기 | 테스트 | 결과 |
|---|---|---|---|
| `pe` | 단일 MAC 셀 | `test_single_mac` | ✅ PASS |
| | | `test_random_macs` (200회 무작위 signed MAC) | ✅ PASS |
| | | `test_activation_passthrough` | ✅ PASS |
| `systolic_array` | 4×4 INT8 | `test_identity_weight` (Y = X·I) | ✅ PASS |
| | | `test_known_matmul` (수동 검증 행렬) | ✅ PASS |
| | | `test_random_matmuls` (25회 무작위 GEMM, M≤6) | ✅ PASS |
| `mtu_top` | 8×8 INT8 | `test_end_to_end_matmul` (15회 무작위 GEMM, M≤8, top-level 통합) | ✅ PASS |

**검증 방식**: 모든 테스트는 RTL 시뮬레이션 출력을 `model/golden.py`의 numpy 정수 행렬곱
레퍼런스와 **비트정확(bit-exact)** 비교하여 통과/실패를 판정함 (랜덤 INT8 범위: -128~127).

총 시뮬레이션 시간: 약 16μs(논리 시간) / 0.6초(실제 실행 시간), 처리율 최대 ~110K ns/s.

## 3. 파형 (VCD)

각 빌드의 전체 신호 트레이스를 표준 텍스트 VCD로 덤프함 (`$dumpfile`/`$dumpvars`,
`pe`/`systolic_array`/`mtu_top` 전체 계층, 모든 신호 depth=0 → 전부 포함).

| 파일 | 대상 | 크기 |
|---|---|---|
| [`waves/pe.vcd`](waves/pe.vcd) | 단일 PE | ~40KB |
| [`waves/systolic_array.vcd`](waves/systolic_array.vcd) | 4×4 시스톨릭 어레이 | ~190KB |
| [`waves/mtu_top.vcd`](waves/mtu_top.vcd) | 8×8 mtu_top 통합 | ~700KB |

GTKWave 등 임의의 VCD 뷰어로 열어 weight 로드 시프트, 활성화 스큐, 부분합 전파를 사이클 단위로
확인 가능. 재생성: `make waves` (또는 `python3 sim.py --waves`).

## 4. 결론

Phase 0–2(PE → 시스톨릭 MXU → mtu_top 통합)의 RTL이 설계 의도대로 동작하며, lint 클린 +
전체 테스트 통과로 **다음 단계(Phase 3: Unified Buffer/컨트롤러) 진행 가능 상태**임을 확인.

## 디렉터리 구성

```
results/
├── SUMMARY.md      ← 이 파일
├── lint.log         Verilator lint 원본 출력
├── test_run.log     cocotb 전체 실행 원본 로그 (3개 빌드 통합, --waves 포함)
├── xml/
│   ├── pe.xml             JUnit 결과 (pe 빌드)
│   ├── systolic_array.xml JUnit 결과 (systolic_array 빌드)
│   └── mtu_top.xml        JUnit 결과 (mtu_top 빌드)
└── waves/
    ├── pe.vcd
    ├── systolic_array.vcd
    └── mtu_top.vcd
```

재실행 방법: `make lint && make test` · 파형까지 함께: `make waves` (또는 `python3 sim.py --waves`).
