# 아키텍처 — 스케줄 네트워크

## 토폴로지

```
┌──────────────────────────┐    10GbE DAC 다이렉트 링크    ┌──────────────────────────┐
│  Machine A (192.168.50.10)│◄──────(스위치 불필요)───────►│  Machine B (192.168.50.11)│
│  LLM 추론 서버             │     192.168.50.0/24 전용망    │  시뮬 워크스테이션 + 스케줄러│
│                          │                              │                          │
│  • vLLM/SGLang           │     NFS: B가 /projects export │  • EDA 툴체인             │
│    :8000 (OpenAI 호환)    │◄────── A가 /projects 마운트 ───│  • slurmctld + slurmd     │
│  • slurmd (gpu 파티션)    │                              │  • aider/continue         │
│                          │                              │    → A의 :8000 호출       │
└──────────────────────────┘                              └──────────────────────────┘
        WAN/사무실 LAN은 각 머신의 2번째 NIC(온보드 1GbE)로 별도 연결
```

- **전용망**: 두 머신을 10GbE DAC 케이블로 **직결**. 2노드뿐이라 스위치 불필요.
  각 머신은 사무실 LAN/인터넷용으로 온보드 1GbE를 따로 사용.
- **공유 스토리지**: B가 `/projects`를 NFS export, A가 마운트.
  설계파일·넷리스트·리그레션 결과를 양 머신이 동일 경로로 접근.
- **잡 스케줄러**: Slurm. 컨트롤러(`slurmctld`)는 B, 컴퓨트 노드(`slurmd`)는 A·B 둘 다.
  - 파티션 `sim`(B, CPU): SPICE MC/코너 스윕, RTL 리그레션
  - 파티션 `gpu`(A, GPU): GPU 가속 잡(필요 시), LLM 보조 배치
- **LLM 연동**: A의 OpenAI 호환 엔드포인트(`http://192.168.50.10:8000/v1`)를
  B의 aider/continue.dev/Claude Code 커스텀 엔드포인트에서 호출.

## /etc/hosts (양 머신 공통)

```
192.168.50.10   machine-a   llm
192.168.50.11   machine-b   sim   slurm-ctl
```

## 구축 순서

1. **조립 & OS** — 양 머신 Ubuntu 24.04 LTS, `/etc/hosts` 등록
2. **전용망** — `cluster/nfs/netplan-private.yaml` 적용, `ping`/`iperf3` 확인
3. **NFS** — `cluster/nfs/setup-nfs-server.sh`(B) → `setup-nfs-client.sh`(A)
4. **A: LLM 스택** — `provisioning/machine-a-llm/01-nvidia-driver.sh` → `02-install-vllm.sh` → `llm/serve/start-vllm.sh`
5. **B: EDA 스택** — `provisioning/machine-b-sim/01-eda-toolchain.sh`
6. **Slurm** — `cluster/slurm/setup-slurm.sh`(양 머신, 역할 인자)
7. **통합 검증** — 아래 참조

## 검증 체크리스트

| 항목 | 명령 | 기대 |
|---|---|---|
| 전용망 대역폭 | `iperf3 -c machine-a` | ~9.4 Gbps |
| NFS 마운트 | `mount \| grep projects` | A에 `/projects` 보임 |
| GPU 인식 | `nvidia-smi` | 2x 5090 |
| LLM API | `llm/serve/healthcheck.sh` | 200 + 토큰 생성 |
| SPICE | `eda/spice/run-mc-sweep.sh` | MC 분산 실행 완료 |
| RTL | `eda/rtl/run-regression.sh` | 다중 시드 통과 |
| 스케줄러 | `sinfo` | 양 노드 `idle` |
| 통합 1사이클 | aider로 RTL 생성 → Verilator sim | 피드백 루프 동작 |

## 보안/운영 메모

- LLM API와 Slurm은 **전용망(192.168.50.0/24)에서만** 바인딩. 외부 노출 금지.
- NFS export는 `192.168.50.0/24`로 제한.
- 모델 가중치/설계자산은 로컬 디스크에 보관, 리포에는 **설정·스크립트만** 커밋(`.gitignore` 참고).
