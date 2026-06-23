#!/usr/bin/env bash
# Machine B 에서 실행: /projects 를 전용망에 NFS export.
set -euo pipefail

PRIV_SUBNET="192.168.50.0/24"
EXPORT_DIR="/projects"

if [[ $EUID -ne 0 ]]; then echo "sudo 로 실행하세요." >&2; exit 1; fi

echo ">> NFS 서버 패키지 설치"
apt-get update -qq
apt-get install -y nfs-kernel-server

echo ">> export 디렉터리 준비: $EXPORT_DIR"
mkdir -p "$EXPORT_DIR"
chown nobody:nogroup "$EXPORT_DIR"
chmod 1777 "$EXPORT_DIR"   # 공유 작업공간 (sticky)

echo ">> /etc/exports 설정"
EXPORT_LINE="$EXPORT_DIR ${PRIV_SUBNET}(rw,sync,no_subtree_check,no_root_squash)"
if ! grep -qF "$EXPORT_DIR" /etc/exports 2>/dev/null; then
  echo "$EXPORT_LINE" >> /etc/exports
else
  echo "   이미 /etc/exports 에 $EXPORT_DIR 항목 존재 — 수동 확인 권장"
fi

echo ">> export 적용"
exportfs -ra
systemctl enable --now nfs-kernel-server

echo ">> 현재 export 목록"
exportfs -v

echo "완료. 클라이언트(A)에서 setup-nfs-client.sh 실행."
