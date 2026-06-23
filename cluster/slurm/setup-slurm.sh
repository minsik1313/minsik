#!/usr/bin/env bash
# Slurm + munge 설치/설정.
#   B(컨트롤러): sudo cluster/slurm/setup-slurm.sh controller
#   A(컴퓨트)  : sudo cluster/slurm/setup-slurm.sh compute
#
# 컨트롤러를 먼저 셋업한 뒤, /etc/munge/munge.key 를 A로 복사하고 compute 실행.
set -euo pipefail

ROLE="${1:-}"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ "$ROLE" != "controller" && "$ROLE" != "compute" ]]; then
  echo "사용법: $0 {controller|compute}" >&2; exit 1
fi
if [[ $EUID -ne 0 ]]; then echo "sudo 로 실행하세요." >&2; exit 1; fi

echo ">> 패키지 설치 (slurm + munge)"
apt-get update -qq
apt-get install -y slurm-wlm munge

echo ">> 디렉터리/권한"
mkdir -p /etc/slurm /var/spool/slurmctld /var/spool/slurmd /var/log/slurm
chown slurm:slurm /var/spool/slurmctld /var/log/slurm || true

echo ">> slurm.conf 배치"
cp "$REPO_DIR/slurm.conf" /etc/slurm/slurm.conf

if [[ "$ROLE" == "controller" ]]; then
  echo ">> [controller] munge 키 생성 (없으면)"
  if [[ ! -s /etc/munge/munge.key ]]; then
    /usr/sbin/mungekey -f || create-munge-key -f
  fi
  chown munge:munge /etc/munge/munge.key
  chmod 400 /etc/munge/munge.key
  systemctl enable --now munge
  systemctl enable --now slurmctld
  systemctl enable --now slurmd
  echo ""
  echo ">> munge 키를 Machine A 로 복사 후 compute 셋업하세요:"
  echo "   scp /etc/munge/munge.key machine-a:/tmp/ && ssh machine-a 'sudo mv /tmp/munge.key /etc/munge/ && sudo chown munge:munge /etc/munge/munge.key && sudo chmod 400 /etc/munge/munge.key'"
else
  echo ">> [compute] gres.conf 배치 (GPU 노드)"
  cp "$REPO_DIR/gres.conf" /etc/slurm/gres.conf
  if [[ ! -s /etc/munge/munge.key ]]; then
    echo "!! /etc/munge/munge.key 가 없습니다. 컨트롤러에서 복사 먼저." >&2; exit 1
  fi
  systemctl enable --now munge
  systemctl enable --now slurmd
fi

echo ">> 상태 확인 (잠시 후): sinfo"
sleep 3
sinfo || true
echo "완료. 'sinfo' 에 양 노드가 idle 로 보이면 정상."
