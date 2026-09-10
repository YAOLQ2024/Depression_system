#!/usr/bin/env bash

set -Eeuo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
browser="/usr/lib/chromium-browser/chromium-browser"
app_url="http://localhost:3000"
browser_profile="${XDG_STATE_HOME:-$HOME/.local/state}/depression-system-chromium-114"
browser_profile_flag="--user-data-dir=$browser_profile"
compose_files=(
  -f "$project_root/infra/compose/docker-compose.dev.yml"
  -f "$project_root/infra/compose/docker-compose.gpu.yml"
  -f "$project_root/infra/compose/docker-compose.lan-https.yml"
  -f "$project_root/infra/compose/docker-compose.jetson-eeg-bridge.yml"
)

if [[ ! -x "$browser" ]]; then
  printf '未找到 Chromium 114 浏览器：%s\n' "$browser" >&2
  exit 1
fi

cd "$project_root"

# 应急入口：不检测现有网页或容器状态，直接执行完整启动命令。
docker compose "${compose_files[@]}" up -d

printf '正在等待前端服务就绪：%s\n' "$app_url"
for _ in {1..90}; do
  if curl --fail --silent --max-time 2 --output /dev/null "$app_url"; then
    mkdir -p "$browser_profile"

    # 仅关闭本启动器的独立浏览器实例，确保 kiosk 参数重新生效。
    if pgrep --full -- "$browser_profile_flag" >/dev/null; then
      pkill --full --signal TERM -- "$browser_profile_flag"
      for _ in {1..20}; do
        pgrep --full -- "$browser_profile_flag" >/dev/null || break
        sleep 0.2
      done
    fi

    nohup "$browser" \
      "$browser_profile_flag" \
      --new-window \
      --kiosk \
      --no-first-run \
      --no-default-browser-check \
      "$app_url" >/dev/null 2>&1 &
    exit 0
  fi
  sleep 1
done

printf '前端服务未能在 90 秒内就绪：%s\n' "$app_url" >&2
exit 1
