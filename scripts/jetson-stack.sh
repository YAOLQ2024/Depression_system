#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export COMPOSE_PARALLEL_LIMIT="${COMPOSE_PARALLEL_LIMIT:-1}"
compose_files=(
  -f "$ROOT_DIR/infra/compose/docker-compose.dev.yml"
  -f "$ROOT_DIR/infra/compose/docker-compose.lan-https.yml"
  -f "$ROOT_DIR/infra/compose/docker-compose.jetson-nano.yml"
)
use_tensorrt=false
case "${MCS_TENSORRT_ENABLED:-auto}" in
  1|true|yes) use_tensorrt=true ;;
  0|false|no) ;;
  auto) [[ ! -f "$ROOT_DIR/.codex-tmp/tensorrt.enabled" ]] || use_tensorrt=true ;;
  *) echo "MCS_TENSORRT_ENABLED must be true, false, or auto" >&2; exit 2 ;;
esac
if "$use_tensorrt"; then
  case "${1:-}" in
    up|start|restart|run) python3 "$ROOT_DIR/scripts/jetson-verify-engines.py" ;;
  esac
  compose_files+=(-f "$ROOT_DIR/infra/compose/docker-compose.jetson-tensorrt.yml")
fi
exec docker compose "${compose_files[@]}" "$@"
