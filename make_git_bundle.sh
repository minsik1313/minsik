#!/usr/bin/env bash
set -euo pipefail

# Create a git bundle of the current repository for offline cloning.
# Usage: ./make_git_bundle.sh [output_bundle]
# Default output: rebalance_criteria.bundle in repo root.

OUT="${1:-rebalance_criteria.bundle}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[ERROR] 이 스크립트는 git 저장소 루트에서 실행해야 합니다." >&2
  exit 1
fi

git bundle create "$OUT" --all

echo "[DONE] $OUT 생성 완료"
echo "[CLONE] 로컬/다른 PC에서: ./restore_from_bundle.sh $OUT rebalance_criteria main"
