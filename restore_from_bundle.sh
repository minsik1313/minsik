#!/usr/bin/env bash
set -euo pipefail

# Restore a repo from a git bundle and check out a working branch.
# Usage: ./restore_from_bundle.sh <bundle_path> [dest_dir] [branch_name]
#  - bundle_path: path to *.bundle file
#  - dest_dir: target directory name (default: rebalance_criteria)
#  - branch_name: branch to check out (default: main)

BUNDLE_PATH="${1:-}"
DEST_DIR="${2:-rebalance_criteria}"
BRANCH_NAME="${3:-main}"

if [[ -z "$BUNDLE_PATH" ]]; then
  echo "Usage: $0 <bundle_path> [dest_dir] [branch_name]" >&2
  exit 1
fi

if [[ ! -f "$BUNDLE_PATH" ]]; then
  echo "[ERROR] bundle not found: $BUNDLE_PATH" >&2
  exit 1
fi

# Show available heads to help users understand what is inside.
HEAD_LINE=$(git bundle list-heads "$BUNDLE_PATH" | awk -v b="refs/heads/$BRANCH_NAME" '$2==b {print $0}' | head -n1)
if [[ -z "$HEAD_LINE" ]]; then
  # If the requested branch is not present, fall back to the first head.
  HEAD_LINE=$(git bundle list-heads "$BUNDLE_PATH" | head -n1)
  if [[ -z "$HEAD_LINE" ]]; then
    echo "[ERROR] bundle has no heads" >&2
    exit 1
  fi
  echo "[WARN] requested branch '$BRANCH_NAME' not found; using: $HEAD_LINE" >&2
fi
HEAD_SHA=$(echo "$HEAD_LINE" | awk '{print $1}')
HEAD_REF=$(echo "$HEAD_LINE" | awk '{print $2}')

if [[ -e "$DEST_DIR" ]]; then
  echo "[ERROR] destination already exists: $DEST_DIR" >&2
  exit 1
fi

echo "[CLONE] git clone $BUNDLE_PATH $DEST_DIR"
git clone "$BUNDLE_PATH" "$DEST_DIR"
cd "$DEST_DIR"

echo "[CHECKOUT] git checkout -b $BRANCH_NAME $HEAD_SHA  # $HEAD_REF"
git checkout -b "$BRANCH_NAME" "$HEAD_SHA"

echo "[DONE] Restored into $DEST_DIR on branch $BRANCH_NAME"
