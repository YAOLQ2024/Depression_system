#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$HOME/.local/state/mcs-project-launcher"
LOG_FILE="$LOG_DIR/launcher.log"
VITE_LOG="$LOG_DIR/vite.log"
VITE_PID_FILE="$LOG_DIR/vite.pid"
MODE="${1:-ensure}"
SERVICES=(postgres redis minio identity-service consultation-service assessment-service risk-service intervention-service followup-service multimodal-service gateway-service consultation operations-console caddy eeg-bridge)

mkdir -p "$LOG_DIR"
touch "$LOG_FILE"

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG_FILE"
}

fail() {
  local message="$1"
  log "ERROR: $message"
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --title='认知障碍智能检测交互系统' --text="$message\n\n日志：$LOG_FILE" >/dev/null 2>&1 || true
  elif command -v notify-send >/dev/null 2>&1; then
    notify-send '项目启动失败' "$message" >/dev/null 2>&1 || true
  fi
  exit 1
}

stack() {
  MCS_EEG_BRIDGE_ENABLED=true "$ROOT_DIR/scripts/orin-nx-stack.sh" "$@"
}

service_containers_ready() {
  local service container state health
  for service in "${SERVICES[@]}"; do
    container="$(stack ps -q "$service" 2>>"$LOG_FILE" | head -n 1 || true)"
    [[ -n "$container" ]] || return 1
    state="$(docker inspect --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container" 2>>"$LOG_FILE" || true)"
    [[ -n "$state" ]] || return 1
    health="${state#*|}"
    [[ "${state%%|*}" == running ]] || return 1
    [[ "$health" == none || "$health" == healthy ]] || return 1
  done
}

hmr_ready() {
  local code
  code="$(curl -k -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 --max-time 4 https://127.0.0.1:3443/ 2>/dev/null || true)"
  [[ "$code" == 200 ]]
}

ensure_hmr() {
  if hmr_ready; then
    log 'Vite 热更新服务已就绪（3443）。'
    return
  fi

  log '启动 Vite 热更新服务（3443）。'
  nohup npm --prefix "$ROOT_DIR/apps/consultation/client" run dev:jetson >>"$VITE_LOG" 2>&1 </dev/null &
  echo "$!" >"$VITE_PID_FILE"
  for _ in $(seq 1 45); do
    if hmr_ready; then
      log 'Vite 热更新服务已就绪（3443）。'
      return
    fi
    sleep 1
  done
  fail "Vite 热更新服务未能在 45 秒内启动。请查看 $VITE_LOG"
}

start_everything() {
  log '启动 Orin NX 全量服务（包含 EEG bridge）。'
  if ! stack up -d >>"$LOG_FILE" 2>&1; then
    fail "Docker 全量启动失败。请查看 $LOG_FILE"
  fi
  ensure_hmr
}

open_kiosk() {
  local browser="${MCS_CHROMIUM_BINARY:-/snap/bin/chromium}"
  [[ -x "$browser" ]] || fail "找不到 Chromium：$browser"

  export DISPLAY="${DISPLAY:-:0}"
  if [[ -z "${XAUTHORITY:-}" && -r "/run/user/$(id -u)/gdm/Xauthority" ]]; then
    export XAUTHORITY="/run/user/$(id -u)/gdm/Xauthority"
  fi

  local profile="$HOME/.local/share/mcs-project-kiosk"
  mkdir -p "$profile"
  log '打开项目封面并进入浏览器全屏模式。'
  nohup "$browser" --user-data-dir="$profile" --no-first-run \
    --no-default-browser-check --new-window --kiosk \
    https://localhost:3443/ >>"$LOG_DIR/chromium.log" 2>&1 </dev/null &
}

case "$MODE" in
  ensure)
    if service_containers_ready && hmr_ready; then
      log '后端服务、EEG bridge 与热更新服务均已运行。'
    else
      start_everything
    fi
    ;;
  start)
    start_everything
    ;;
  *)
    fail "未知启动模式：$MODE（支持 ensure 或 start）"
    ;;
esac

open_kiosk
