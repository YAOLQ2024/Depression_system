#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/home/ZR/data2/MCS}"

write_if_missing() {
  local target="$1"
  shift
  if [[ -e "$target" ]]; then
    return 0
  fi
  mkdir -p "$(dirname "$target")"
  cat >"$target"
}

create_python_backend_scaffold() {
  local service_root="$1"
  local service_slug="$2"
  local service_title="$3"
  local project_name="${service_slug//-/_}"

  mkdir -p \
    "$service_root/alembic/versions" \
    "$service_root/scripts" \
    "$service_root/tests" \
    "$service_root/app/api" \
    "$service_root/app/models" \
    "$service_root/app/schemas" \
    "$service_root/app/services" \
    "$service_root/app/clients" \
    "$service_root/app/rules"

  write_if_missing "$service_root/README.md" <<EOF
# ${service_title}

Phase A scaffold for ${service_slug}.
EOF

  write_if_missing "$service_root/.env.example" <<'EOF'
APP_NAME=
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
DATABASE_URL=
REDIS_URL=
EOF

  write_if_missing "$service_root/Dockerfile" <<'EOF'
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

  write_if_missing "$service_root/requirements.txt" <<'EOF'
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.36
alembic==1.13.3
pydantic-settings==2.6.0
redis==5.2.0
EOF

  write_if_missing "$service_root/pyproject.toml" <<EOF
[project]
name = "mcs-${service_slug}"
version = "0.1.0"
description = "${service_title} scaffold"
requires-python = ">=3.11"
EOF

  write_if_missing "$service_root/alembic.ini" <<EOF
[alembic]
script_location = ${service_root}/alembic
sqlalchemy.url = sqlite:///./${project_name}.db
EOF

  write_if_missing "$service_root/seed.py" <<'EOF'
def main() -> None:
    print("seed placeholder")


if __name__ == "__main__":
    main()
EOF

  write_if_missing "$service_root/app/__init__.py" <<'EOF'
"""Application package."""
EOF

  write_if_missing "$service_root/app/main.py" <<EOF
from fastapi import FastAPI

app = FastAPI(title="${service_title}")


@app.get("/health/live")
def health_live():
    return {"status": "ok", "service": "${service_slug}"}


@app.get("/health/ready")
def health_ready():
    return {"status": "ready", "service": "${service_slug}"}
EOF

  write_if_missing "$service_root/app/config.py" <<EOF
APP_NAME = "${service_title}"
EOF

  write_if_missing "$service_root/app/database.py" <<'EOF'
def get_database_url() -> str:
    return "sqlite:///./app.db"
EOF

  write_if_missing "$service_root/app/deps.py" <<'EOF'
def get_request_context() -> dict:
    return {}
EOF

  write_if_missing "$service_root/app/redis.py" <<'EOF'
def get_redis_url() -> str:
    return "redis://localhost:6379/0"
EOF

  write_if_missing "$service_root/app/permissions.py" <<'EOF'
ROLE_ADMIN = "admin"
ROLE_RESEARCHER = "researcher"
ROLE_PARTICIPANT = "participant"
EOF

  write_if_missing "$service_root/app/api/.gitkeep" <<'EOF'
# placeholder
EOF

  write_if_missing "$service_root/app/models/.gitkeep" <<'EOF'
# placeholder
EOF

  write_if_missing "$service_root/app/schemas/.gitkeep" <<'EOF'
# placeholder
EOF

  write_if_missing "$service_root/app/services/.gitkeep" <<'EOF'
# placeholder
EOF

  write_if_missing "$service_root/app/clients/.gitkeep" <<'EOF'
# placeholder
EOF

  write_if_missing "$service_root/app/rules/.gitkeep" <<'EOF'
# placeholder
EOF

  write_if_missing "$service_root/alembic/versions/.gitkeep" <<'EOF'
# placeholder
EOF

  write_if_missing "$service_root/scripts/.gitkeep" <<'EOF'
# placeholder
EOF

  write_if_missing "$service_root/tests/.gitkeep" <<'EOF'
# placeholder
EOF
}

create_app_scaffold() {
  local app_root="$1"
  local app_slug="$2"
  local app_title="$3"

  mkdir -p \
    "$app_root/client/public" \
    "$app_root/client/src" \
    "$app_root/server"

  write_if_missing "$app_root/.gitattributes" <<'EOF'
* text=auto eol=lf
EOF

  write_if_missing "$app_root/.gitignore" <<'EOF'
client/node_modules/
client/dist/
server/.venv/
server/__pycache__/
EOF

  write_if_missing "$app_root/Dockerfile" <<'EOF'
FROM node:20-alpine
WORKDIR /app
CMD ["sh", "-c", "echo app scaffold"]
EOF

  write_if_missing "$app_root/README.md" <<EOF
# ${app_title}

App envelope following the aic-coralreef client/server pattern.
EOF

  write_if_missing "$app_root/client/.env.example" <<EOF
VITE_APP_NAME=${app_title}
VITE_API_BASE_URL=http://localhost:8080/api/v1
EOF

  write_if_missing "$app_root/client/README.md" <<EOF
# ${app_title} Client

Front-end shell for ${app_slug}.
EOF

  write_if_missing "$app_root/client/package.json" <<EOF
{
  "name": "mcs-${app_slug}-client",
  "private": true,
  "version": "0.1.0"
}
EOF

  write_if_missing "$app_root/client/src/.gitkeep" <<'EOF'
# placeholder
EOF

  write_if_missing "$app_root/client/public/.gitkeep" <<'EOF'
# placeholder
EOF

  create_python_backend_scaffold "$app_root/server" "${app_slug}-app-server" "${app_title} App Server"
}

mkdir -p "$ROOT"

write_if_missing "$ROOT/.editorconfig" <<'EOF'
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
indent_style = space
indent_size = 2
trim_trailing_whitespace = true
EOF

write_if_missing "$ROOT/.gitignore" <<'EOF'
.DS_Store
.env
**/__pycache__/
**/.pytest_cache/
**/.mypy_cache/
**/node_modules/
**/dist/
**/.venv/
*.db
EOF

write_if_missing "$ROOT/.env.example" <<'EOF'
MCS_ENV=development
POSTGRES_PORT=5432
REDIS_PORT=6379
MINIO_PORT=9000
EOF

write_if_missing "$ROOT/README.md" <<'EOF'
# MCS

Multimodal Consultation System scaffold.
EOF

write_if_missing "$ROOT/Makefile" <<'EOF'
.PHONY: help phase-a up down logs

help:
	@echo "Available targets: phase-a up down logs"

phase-a:
	@bash infra/scripts/bootstrap_phase_a.sh

up:
	@docker compose -f infra/compose/docker-compose.dev.yml up -d

down:
	@docker compose -f infra/compose/docker-compose.dev.yml down

logs:
	@docker compose -f infra/compose/docker-compose.dev.yml logs -f
EOF

mkdir -p \
  "$ROOT/apps" \
  "$ROOT/services" \
  "$ROOT/packages/core-lib" \
  "$ROOT/packages/ui-kit" \
  "$ROOT/packages/workflow-resources/workflows" \
  "$ROOT/packages/workflow-resources/doctor-personas" \
  "$ROOT/packages/workflow-resources/interview-scripts/rule-v1" \
  "$ROOT/packages/workflow-resources/scales" \
  "$ROOT/packages/workflow-resources/risk-rules" \
  "$ROOT/packages/workflow-resources/intervention-programs" \
  "$ROOT/packages/workflow-resources/prompts" \
  "$ROOT/infra/compose" \
  "$ROOT/infra/nginx" \
  "$ROOT/infra/scripts" \
  "$ROOT/infra/env" \
  "$ROOT/infra/monitoring" \
  "$ROOT/docs/architecture" \
  "$ROOT/docs/api" \
  "$ROOT/docs/adr" \
  "$ROOT/docs/operations" \
  "$ROOT/docs/product" \
  "$ROOT/docs/migration"

create_app_scaffold "$ROOT/apps/consultation" "consultation" "Consultation"
create_app_scaffold "$ROOT/apps/operations-console" "operations-console" "Operations Console"

create_python_backend_scaffold "$ROOT/services/gateway-service" "gateway-service" "Gateway Service"
create_python_backend_scaffold "$ROOT/services/identity-service" "identity-service" "Identity Service"
create_python_backend_scaffold "$ROOT/services/consultation-service" "consultation-service" "Consultation Service"
create_python_backend_scaffold "$ROOT/services/assessment-service" "assessment-service" "Assessment Service"
create_python_backend_scaffold "$ROOT/services/multimodal-service" "multimodal-service" "Multimodal Service"
create_python_backend_scaffold "$ROOT/services/risk-service" "risk-service" "Risk Service"
create_python_backend_scaffold "$ROOT/services/intervention-service" "intervention-service" "Intervention Service"
create_python_backend_scaffold "$ROOT/services/followup-service" "followup-service" "Followup Service"
create_python_backend_scaffold "$ROOT/services/ai-service" "ai-service" "AI Service"

write_if_missing "$ROOT/packages/core-lib/README.md" <<'EOF'
# Core Lib

Shared library entrypoint for MCS.
EOF

write_if_missing "$ROOT/packages/ui-kit/README.md" <<'EOF'
# UI Kit

Shared UI package placeholder for MCS apps.
EOF

write_if_missing "$ROOT/packages/workflow-resources/README.md" <<'EOF'
# Workflow Resources

Canonical home for workflows, scripts, scales, risk rules, intervention programs, and prompts.
EOF

write_if_missing "$ROOT/infra/compose/docker-compose.dev.yml" <<'EOF'
services:
  postgres:
    image: postgres:16-alpine
  redis:
    image: redis:7-alpine
  minio:
    image: minio/minio:latest
    command: server /data
EOF

write_if_missing "$ROOT/infra/nginx/README.md" <<'EOF'
# Nginx

Reverse proxy configs live here.
EOF

write_if_missing "$ROOT/docs/architecture/README.md" <<'EOF'
# Architecture Docs
EOF

write_if_missing "$ROOT/docs/product/README.md" <<'EOF'
# Product Docs
EOF

echo "Phase A scaffold created under $ROOT"
