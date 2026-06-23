#!/usr/bin/env bash
# Machine A 에서 실행: B의 /projects 를 마운트 (부팅 시 자동).
set -euo pipefail

NFS_SERVER="192.168.50.11"   # Machine B
MOUNT_POINT="/projects"

if [[ $EUID -ne 0 ]]; then echo "sudo 로 실행하세요." >&2; exit 1; fi

echo ">> NFS 클라이언트 패키지 설치"
apt-get update -qq
apt-get install -y nfs-common

echo ">> 마운트 지점 준비: $MOUNT_POINT"
mkdir -p "$MOUNT_POINT"

echo ">> /etc/fstab 등록 (점보프레임/성능 옵션)"
FSTAB_LINE="${NFS_SERVER}:/projects ${MOUNT_POINT} nfs rw,hard,intr,rsize=1048576,wsize=1048576,_netdev 0 0"
if ! grep -qF "${NFS_SERVER}:/projects" /etc/fstab; then
  echo "$FSTAB_LINE" >> /etc/fstab
fi

echo ">> 마운트"
mount -a
mount | grep "$MOUNT_POINT" && echo "마운트 성공" || { echo "마운트 실패" >&2; exit 1; }

echo "완료. 'touch ${MOUNT_POINT}/hello' 로 양 머신 공유 확인 가능."
