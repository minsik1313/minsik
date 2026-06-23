# CPU vs GPU 벡터 연산기 RTL 비교

CPU(순차 처리)와 GPU(병렬 처리) 구조의 차이를 Verilog RTL로 구현하고,
testbench로 **동작 검증**과 **연산 시간(사이클) 비교**를 수행하는 예제입니다.

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
│   ├── cpu/cpu_vec.v     # 순차(단일 MAC) 벡터 연산기
│   └── gpu/gpu_vec.v     # 병렬(P개 PE) 벡터 연산기
├── tb/
│   └── tb_compare.v      # 비교 testbench (검증 + 시간 측정)
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
make          # 기본(N=16, P=4) 컴파일 + 실행
make sweep    # N 을 16→64→256→1024 로 키우며 speedup 변화 관찰
make wave     # 파형(sim/wave.vcd) 생성 (gtkwave 로 확인)
make clean    # 산출물 삭제
```

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
