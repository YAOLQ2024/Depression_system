#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export COMPOSE_PARALLEL_LIMIT="${COMPOSE_PARALLEL_LIMIT:-1}"
export JETSON_USER_PYTHON_DIR="$ROOT_DIR/.codex-tmp/gpu-python"
files=(
  -f "$ROOT_DIR/infra/compose/docker-compose.dev.yml"
  -f "$ROOT_DIR/infra/compose/docker-compose.lan-https.yml"
  -f "$ROOT_DIR/infra/compose/docker-compose.jetson-nano.yml"
  -f "$ROOT_DIR/infra/compose/docker-compose.orin-nx.yml"
)
case "${MCS_TENSORRT_ENABLED:-auto}" in
  true|1|yes) enable_trt=true ;;
  false|0|no) enable_trt=false ;;
  auto) enable_trt=false; [[ ! -f "$ROOT_DIR/.codex-tmp/tensorrt.enabled" ]] || enable_trt=true ;;
  *) echo 'MCS_TENSORRT_ENABLED must be true, false, or auto' >&2; exit 2 ;;
esac
if "$enable_trt"; then
  case "${1:-}" in
    up|start|restart|run) python3 "$ROOT_DIR/scripts/jetson-verify-engines.py" ;;
  esac
  files+=(-f "$ROOT_DIR/infra/compose/docker-compose.jetson-tensorrt.yml")
fi
if [[ -x "$ROOT_DIR/.codex-tmp/docker-compose" ]]; then
  exec "$ROOT_DIR/.codex-tmp/docker-compose" "${files[@]}" "$@"
fi
echo 'Install the project-local Docker Compose v2.32.4 before using this stack.' >&2
exit 2
