# minsik — 회로설계 특화 컴퓨팅 환경

회로설계(아날로그 SPICE + 디지털 RTL/합성)와 로컬 LLM 추론을 위한 **2머신 DIY 클러스터**의
프로비저닝 스크립트 · 설정 · 문서 모음.

## 구조

```
Machine A (LLM 서버)  ◄── 10GbE 다이렉트 + NFS + Slurm ──►  Machine B (시뮬 워크스테이션)
 2x RTX 5090 / 64GB VRAM                                    Ryzen 9 9950X3D / 192GB RAM
 vLLM·SGLang (OpenAI 호환 API)                              ngspice·Xyce·Verilator·Yosys
```

| 머신 | 역할 | IP (전용망) | 핵심 사양 |
|---|---|---|---|
| **A** | 로컬 LLM 추론 | `192.168.50.10` | 2x RTX 5090(64GB VRAM), Ryzen 9 7900, 128GB |
| **B** | 회로 시뮬 + 스케줄러 | `192.168.50.11` | Ryzen 9 9950X3D, 192GB RAM, NVMe |

## 디렉터리

| 경로 | 내용 |
|---|---|
| `docs/` | 하드웨어 BOM, 아키텍처 |
| `provisioning/machine-a-llm/` | A 머신 셋업 (드라이버/CUDA/서빙) |
| `provisioning/machine-b-sim/` | B 머신 셋업 (EDA 툴체인) |
| `cluster/slurm/` · `cluster/nfs/` | 스케줄러 + 공유 스토리지 |
| `eda/spice/` · `eda/rtl/` | 시뮬 예제 + 리그레션 잡 템플릿 |
| `llm/serve/` | 서빙 설정 + 클라이언트(aider/continue) |

## 빠른 시작

```bash
# 1) 네트워크/NFS
sudo cluster/nfs/setup-nfs-server.sh      # B에서 (/projects export)
sudo cluster/nfs/setup-nfs-client.sh      # A에서 (마운트)

# 2) LLM 서버 (A)
sudo provisioning/machine-a-llm/01-nvidia-driver.sh
provisioning/machine-a-llm/02-install-vllm.sh
llm/serve/start-vllm.sh

# 3) 시뮬 워크스테이션 (B)
sudo provisioning/machine-b-sim/01-eda-toolchain.sh

# 4) 스케줄러 (양 머신)
sudo cluster/slurm/setup-slurm.sh

# 5) 검증
eda/spice/run-mc-sweep.sh        # SPICE Monte Carlo (Slurm array)
eda/rtl/run-regression.sh        # RTL 리그레션 (Slurm array)
```

자세한 단계는 [`docs/architecture.md`](docs/architecture.md) 참고.

> ⚠️ 가격·사양은 2026년 초 기준 대략치. 발주 전 [`docs/hardware-bom.md`](docs/hardware-bom.md)에서 현재가 확인.
