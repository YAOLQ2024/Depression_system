#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "[phase-b-check] validating compose file"
docker compose -f "$ROOT_DIR/infra/compose/docker-compose.dev.yml" config >/dev/null

echo "[phase-b-check] compiling Python app modules"
python -m py_compile $(find "$ROOT_DIR/apps" "$ROOT_DIR/services" -path '*/app/*' -name '*.py' | sort)

echo "[phase-b-check] checking local FastAPI availability"
python - <<'PY'
try:
    import fastapi
    print(f"[phase-b-check] fastapi available: {fastapi.__version__}")
except Exception as exc:
    print(f"[phase-b-check] fastapi unavailable: {type(exc).__name__}: {exc}")
PY
