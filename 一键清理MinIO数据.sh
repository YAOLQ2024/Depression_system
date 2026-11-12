#!/usr/bin/env bash
set -Eeuo pipefail

# Use the project's running application container: its MinIO SDK and connection
# settings match the storage used by the deployed system.
container="$(docker ps --filter 'label=com.docker.compose.project=mcs-jetson' --filter 'label=com.docker.compose.service=multimodal-service' --format '{{.Names}}')"
if [[ -z "$container" || "$container" == *$'\n'* ]]; then
  printf '无法找到唯一运行中的项目多模态服务，请先启动项目。\n' >&2
  exit 1
fi

docker exec -i "$container" python - <<'PY'
import os
from urllib.parse import urlparse
from minio import Minio
from minio.deleteobjects import DeleteObject

bucket = "mcs-multimodal"
configured_bucket = os.getenv("MULTIMODAL_BUCKET", bucket)
if configured_bucket != bucket:
    raise SystemExit(f"配置的存储桶为 {configured_bucket}，与预期的 {bucket} 不一致，已停止。")
endpoint = os.environ["MINIO_ENDPOINT"]
parsed = urlparse(endpoint if "://" in endpoint else "//" + endpoint)
secure = parsed.scheme == "https" if parsed.scheme else os.getenv("MINIO_SECURE", "false").lower() in ("true", "1", "yes")
client = Minio(parsed.netloc, access_key=os.environ["MINIO_ACCESS_KEY"],
               secret_key=os.environ["MINIO_SECRET_KEY"], secure=secure)
if not client.bucket_exists(bucket):
    raise SystemExit(f"存储桶 {bucket} 不存在，已停止。")
print(f"正在清理 {bucket} 中的对象……", flush=True)
objects = (DeleteObject(obj.object_name) for obj in client.list_objects(bucket, recursive=True))
errors = list(client.remove_objects(bucket, objects))
if errors:
    for error in errors:
        print(error, flush=True)
    raise SystemExit("部分对象清理失败，请检查上面的错误。")
if next(client.list_objects(bucket, recursive=True), None) is not None:
    raise SystemExit("桶内仍有对象，可能有新数据正在写入，请稍后重试。")
print("清理完成。数据库和存储桶本身未作修改。", flush=True)
PY
