# CPU vs GPU 벡터 연산기 RTL 비교

CPU(순차 처리)와 GPU(병렬 처리) 구조의 차이를 Verilog RTL로 구현하고,
testbench로 **동작 검증**과 **연산 시간(사이클) 비교**를 수행하는 예제입니다.

이 저장소에는 두 가지 버전이 있습니다.

- **v1 (`*_vec.v`)** : 자원 개수(곱셈기 1개 vs P개)만 다른 가장 단순한 비교.
- **v2 (`*_core.v`)** : 실제 ISA(명령어 집합)를 갖는 **멀티사이클 CPU**와
  **SIMT 방식 GPU**로, 진짜 프로그램(명령어 fetch/decode/execute)을 실행한다는
  점에서 v1보다 실제 CPU/GPU 구조에 더 가깝습니다.

## v1 — 단순 비교판 (`cpu_vec` / `gpu_vec`)

두 설계 모두 동일한 연산을 수행합니다:

```
C[i] = A[i] * B[i]      (i = 0 .. N-1)
```

차이는 **자원을 얼마나 병렬로 두느냐**에 있습니다.

| 구분 | CPU (`cpu_vec`) | GPU (`gpu_vec`) |
|------|-----------------|-----------------|
| 곱셈기(PE) 수 | 1개 | P개 (기본 4) |
| 한 클록당 처리량 | 원소 1개 | 원소 P개 |
| 총 소요 클록 | ≈ N | ≈ N / P |
| 비유 | 단일 코어 순차 실행 | SIMD 병렬 lane |

---

## 디렉토리 구조

```
.
├── rtl/
│   ├── common/
│   │   ├── isa_defs.vh     # v2 CPU/GPU 공유 ISA(명령어 집합) 정의
│   │   ├── sync_mem.v      # 단일 포트 데이터 메모리 (v2 CPU용)
│   │   └── sync_mem_mp.v   # P포트 데이터 메모리 (v2 GPU용)
│   ├── cpu/
│   │   ├── cpu_vec.v       # v1: 순차(단일 MAC) 벡터 연산기
│   │   └── cpu_core.v      # v2: 멀티사이클 ISA 기반 CPU 코어
│   └── gpu/
│       ├── gpu_vec.v       # v1: 병렬(P개 PE) 벡터 연산기
│       └── gpu_core.v      # v2: SIMT 방식 GPU 코어
├── tb/
│   ├── tb_compare.v        # v1 비교 testbench
│   └── tb_core_compare.v   # v2 비교 testbench
├── Makefile
├── .devcontainer/devcontainer.json   # Codespaces 자동 환경 설정
└── README.md
```

---

## 실행 방법

### GitHub Codespaces

이 저장소를 Codespaces로 열면 `.devcontainer/devcontainer.json`의
`postCreateCommand`가 자동으로 `iverilog`, `gtkwave`를 설치합니다.
별도 설정 없이 바로 아래 `make` 명령을 실행할 수 있습니다.

### 로컬

[Icarus Verilog](http://iverilog.icarus.com/) 필요 (`apt-get install iverilog`).

```bash
make          # v1 기본(N=16, P=4) 컴파일 + 실행
make sweep    # v1: N 을 16→64→256→1024 로 키우며 speedup 변화 관찰
make wave     # v1 파형(sim/wave.vcd) 생성 (gtkwave 로 확인)

make run2     # v2 기본(N=16, P=4) 컴파일 + 실행
make sweep2   # v2: N 을 16→17→64→67 로 (P의 배수/비배수 포함) 검증
make wave2    # v2 파형(sim/wave_core.vcd) 생성

make clean    # 산출물 삭제
```

> `sim/wave.vcd`(v1) 와 `sim/wave_core.vcd`(v2, 기본 N=16/P=4 실행 파형)는
> 저장소에 함께 보관되어 있어 `gtkwave sim/wave_core.vcd` 로 바로 열어볼 수
> 있습니다. 컴파일 바이너리(`*.vvp`)는 매번 재생성되는 산출물이라 git에서
> 제외됩니다.

---

## 실행 결과 (N=16, P=4, 100MHz)

```
 CPU  done : 17 cycles  =>  170 ns
 GPU  done :  5 cycles  =>   50 ns
 RESULT VERIFY : PASS  (CPU == GPU == golden, all 16 elements)
 Speedup (GPU vs CPU) : 3.40 x
```

- **동작 검증**: CPU 결과 == GPU 결과 == 소프트웨어 golden 값 (전부 일치, PASS)
- **시간 비교**: GPU가 CPU보다 약 3.4배 빠름

### N 스케일링 (`make sweep`)

N이 커질수록 고정 오버헤드(시작 1클록)가 상쇄되어 speedup이 이론치 P(=4)에 수렴합니다.

| N | CPU cycles | GPU cycles | Speedup |
|------|-----------|-----------|---------|
| 16   | 17        | 5         | 3.40x |
| 64   | 65        | 17        | 3.82x |
| 256  | 257       | 65        | 3.95x |
| 1024 | 1025      | 257       | 3.98x |

---

## 설계 핵심 포인트

### CPU (`cpu_vec.v`) — 순차
- FSM이 인덱스 `idx`를 0→N-1로 증가시키며 **한 클록에 원소 1개**씩 계산.
- 곱셈기 1개만 사용 → 면적은 작지만 N에 비례한 시간 소요. **O(N)**.

### GPU (`gpu_vec.v`) — 병렬
- `generate`로 **P개의 곱셈기(PE/lane)**를 인스턴스화.
- 한 클록에 P개 원소를 동시에 계산·기록 → **O(N/P)**.
- N이 P의 배수가 아니어도 범위 밖 lane은 무시하도록 처리.
- 트레이드오프: 시간은 P배 단축되지만 곱셈기 면적이 P배 증가 (전형적인
  GPU의 throughput-vs-area 특성).

### Testbench (`tb_compare.v`)
1. 랜덤 입력 벡터 A, B 생성 및 소프트웨어 golden(`A*B`) 계산
2. CPU/GPU에 동일 입력 인가, `start`→`done` 사이 클록 수 측정
3. CPU·GPU·golden 3자 결과 비교로 정확성 검증
4. 사이클 수 / ns / speedup 출력

> 파라미터 `N`, `DW`, `P`, `CLK_NS`는 모듈/testbench에서 조정 가능하며,
> testbench는 `iverilog -P tb_compare.N=256 ...` 로 커맨드라인 override도 지원합니다.

---

## v2 — ISA 기반 멀티사이클 CPU vs SIMT GPU (`cpu_core` / `gpu_core`)

v1은 "곱셈기를 몇 개 쓰는가"만 다뤘습니다. v2는 한 단계 더 들어가
**실제 명령어를 fetch해서 실행하는 프로세서**로 CPU/GPU를 구현합니다.

### 공유 ISA (`rtl/common/isa_defs.vh`)

32비트 고정 길이 명령어, `[31:28] opcode [27:24] rd [23:20] rs1 [19:16] rs2 [15:0] imm` 포맷.

| opcode | 동작 |
|--------|------|
| `ADD/SUB/MUL` | `rd = rs1 op rs2` |
| `ADDI` | `rd = rs1 + imm` |
| `LI`   | `rd = imm` |
| `LW`   | `rd = MEM[rs1 + imm]` |
| `SW`   | `MEM[rs1 + imm] = rs2` |
| `BNE`  | `rs1 != rs2` 이면 `pc += imm` (분기) |
| `HALT` | 실행 종료 |

### CPU (`cpu_core.v`) — 멀티사이클 스칼라 프로세서
- 명령어 1개당 **FETCH → EXEC(ALU) → MEM → WB** 4단계를 4클록에 걸쳐 처리 (파이프라이닝 없는 고전적 multicycle 구조).
- 아래 **소프트웨어 루프**를 실제 명령어로 실행 (인덱스 증가·종료 판정도 명령어):
  ```
  i = 0
  loop:
    r3 = MEM[i + 0]      ; A[i]
    r4 = MEM[i + N]      ; B[i]
    r5 = r3 * r4
    MEM[i + 2N] = r5     ; C[i]
    i = i + 1
    if (i != N) goto loop
  ```
- N개 원소 처리에 `6N+3`개 명령어 실행 → `(6N+3)×4` 클록.

### GPU (`gpu_core.v`) — SIMT(P-lane) 프로세서
- CPU와 **동일한 ISA/디코더**를 P개 lane에 공유. 명령어 fetch/decode는 1번만 하고
  ALU·메모리 접근·레지스터 파일은 lane마다 독립적으로 P개 병렬 수행.
- 각 lane의 `r0`은 하드웨어가 블록 시작 시 자동으로 `thread-id`를 채워준다
  (실제 GPU의 `threadIdx`와 동일한 역할).
- 커널에는 **분기/루프 명령어가 없음** — 스레드 인덱싱이 루프를 대체:
  ```
  r1 = MEM[tid + 0]     ; A[tid]
  r2 = MEM[tid + N]     ; B[tid]
  r3 = r1 * r2
  MEM[tid + 2N] = r3    ; C[tid]
  halt
  ```
- N > P 인 경우 `ceil(N/P)`개의 "블록"으로 나누어 커널을 반복 실행.
- 데이터 메모리는 P개 lane이 동시에 접근할 수 있는 멀티포트 메모리
  (`sync_mem_mp.v`)를 사용 (실제 GPU 메모리 컨트롤러/코어레싱의 단순화 모델).

### 실행 결과 (N=16, P=4, 100MHz)

```
 CPU : 396 cycles (3960 ns)  -- 99 instrs x 4 cycles/instr (multicycle)
 GPU : 84 cycles (840 ns)    -- 4 blocks x 5 instrs x 4 cycles + block-init
 RESULT VERIFY : PASS  (CPU == GPU == golden, all 16 elements)
 Speedup (GPU vs CPU) : 4.71 x
```

GPU의 speedup(4.71x)이 lane 수 P(=4)를 **넘어서는** 점이 핵심입니다. lane 병렬성
자체로는 4배지만, GPU 커널에는 CPU가 매 원소마다 실행해야 하는 인덱스 증가
(`ADDI`)·분기(`BNE`) 명령어가 없기 때문에 추가로 더 빨라집니다 — 실제 GPU가
스레드 인덱스 하드웨어로 루프 오버헤드를 없애는 것과 같은 효과입니다.

### N 스케일링 (`make sweep2`, P의 배수/비배수 모두 포함)

| N | CPU cycles | GPU cycles | Speedup |
|------|-----------|-----------|---------|
| 16 | 396  | 84  | 4.71x |
| 17 | 420  | 105 | 4.00x |
| 64 | 1548 | 336 | 4.60x |
| 67 | 1620 | 357 | 4.53x |

(N=17, 67은 P=4의 배수가 아니라 GPU의 마지막 블록 일부 lane이 쉬는 경우로,
speedup이 살짝 낮아지는 것을 보여줍니다 — 실제 GPU에서 워프/블록이 가득 차지
않을 때 효율이 떨어지는 현상과 같은 이치입니다.)

### Testbench (`tb_core_compare.v`)
1. 랜덤 입력 A, B와 golden(`A*B`) 계산
2. CPU/GPU 각각의 데이터 메모리에 동일한 A, B를 직접 적재 (계층 참조로 `mem[]` poke)
3. `start`→`done` 사이 클록 수 측정 (CPU: 실행 명령어 수, GPU: 발행한 명령어 슬롯 수도 함께 출력)
4. 두 설계의 결과(C 영역)를 golden과 3자 비교로 검증
5. 사이클 수 / ns / speedup 출력, `sim/wave_core.vcd`로 파형 덤프
