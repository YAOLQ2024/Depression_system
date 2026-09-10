#!/usr/bin/env bash

set -Eeuo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
minio_container="compose-minio-1"
minio_bucket="mcs-multimodal"

cd "$project_root"

if ! docker inspect --format '{{.State.Running}}' "$minio_container" 2>/dev/null | grep -qx 'true'; then
  printf 'MinIO 服务未运行，无法清理。请先启动项目后再试。\n' >&2
  exit 1
fi

printf '正在清理 MinIO 桶 %s 中的全部对象…\n' "$minio_bucket"

docker exec "$minio_container" sh -ec '
  mc alias set local-minio "http://127.0.0.1:9000" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null
  mc rm --recursive --force "local-minio/'"$minio_bucket"'"
  mc du "local-minio/'"$minio_bucket"'"
'

printf 'MinIO 数据已清理完成；数据库和存储桶本身未作修改。\n'
