#!/usr/bin/env bash
set -euo pipefail

# Package the current Git repo into a tar.gz bundle for sharing without pushing to GitHub.
# Usage: ./package_repo.sh [output_path]
# Default output: rebalance_criteria_bundle_$(date +%Y%m%d).tar.gz

main() {
  if ! command -v git >/dev/null 2>&1; then
    echo "[package_repo] git is required to package the repository." >&2
    exit 1
  fi

  local repo_root
  repo_root=$(git rev-parse --show-toplevel)
  cd "$repo_root"

  local default_name="rebalance_criteria_bundle_$(date +%Y%m%d).tar.gz"
  local output="${1:-$default_name}"

  echo "[package_repo] Creating bundle: $output"
  git archive --format=tar.gz --output="$output" HEAD
  echo "[package_repo] Done. Share '$output' to download the current codebase."
}

main "$@"
