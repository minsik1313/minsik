#!/usr/bin/env bash
set -euo pipefail

# P0/P1 current mirror smoke runner.
# 전제: 가상환경 활성화 상태에서 gdsfactory(및 sky130)를 설치해 둔 후 실행합니다.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_P0=1
RUN_P1=1

for arg in "$@"; do
  case "$arg" in
    --p0-only)
      RUN_P1=0
      ;;
    --p1-only)
      RUN_P0=0
      ;;
    *)
      echo "[warn] 알 수 없는 옵션: $arg" >&2
      ;;
  esac
done

if [[ $RUN_P0 -eq 0 && $RUN_P1 -eq 0 ]]; then
  echo "[error] 실행할 대상이 없습니다. --p0-only 또는 --p1-only 중 하나를 생략하세요." >&2
  exit 1
fi

check_module() {
  local module=$1
  if python - "$module" <<'PY'; then
    return 0
  fi
  return 1
PY
import importlib, sys
mod = sys.argv[1]
if importlib.util.find_spec(mod) is None:
    sys.exit(1)
sys.exit(0)
PY
}

require_module() {
  local module=$1
  local hint=$2
  if ! check_module "$module"; then
    echo "[error] Python 모듈 '${module}'을(를) 찾을 수 없습니다." >&2
    echo "        ${hint}" >&2
    echo "        (회사 프록시로 설치가 막히면 코드만 수정하고 집/프록시 없는 환경에서 ./run_all_gds.sh를 실행하세요.)" >&2
    echo "        (회사 정책 허용 범위에서만 trusted-host/프록시/미러 옵션을 사용하고, 그래도 403이면 실행은 집에서 진행하세요.)" >&2
    echo "        (급하게 우회하려면: pip install ${module} --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org)" >&2
    exit 1
  fi
}

echo "[info] P0/P1 GDS 스모크 테스트를 시작합니다. (ROOT=${ROOT_DIR})"

# Corporate-proxy reminder: prefer coding-only at work, execute at home/non-proxy
if [[ -n "${HTTP_PROXY:-}${http_proxy:-}${HTTPS_PROXY:-}${https_proxy:-}" ]]; then
  echo "[warn] 프록시가 감지되었습니다. 회사 정책에 따라 실행은 집/비프록시 환경에서 진행하는 것을 권장합니다." >&2
  echo "       승인된 프록시/미러만 사용하고, 설치·실행이 막히면 코드는 작성만 하고 실행은 나중에 수행하세요." >&2
fi

if [[ $RUN_P0 -eq 1 ]]; then
  require_module "gdsfactory" "p0_current_mirror/env/install_min_env.sh 실행 또는 'pip install gdsfactory' 후 다시 시도하세요."
  pushd "${ROOT_DIR}/p0_current_mirror/src" > /dev/null
  echo "[info] P0: python src/run_generator.py"
  python run_generator.py
  popd > /dev/null
fi

if [[ $RUN_P1 -eq 1 ]]; then
  require_module "gdsfactory" "p1_sky130_current_mirror/env/install_sky130_env.sh 실행 또는 'pip install gdsfactory' 후 다시 시도하세요."
  require_module "sky130" "p1_sky130_current_mirror/env/install_sky130_env.sh 실행 또는 'pip install sky130' 후 다시 시도하세요."
  pushd "${ROOT_DIR}/p1_sky130_current_mirror/src" > /dev/null
  echo "[info] P1: python src/run_cm_sky130.py"
  python run_cm_sky130.py
  popd > /dev/null
fi

echo "[info] 완료: 생성된 GDS는 각 src 디렉터리에 저장됩니다."
