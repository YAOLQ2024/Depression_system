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
export DISPLAY="${DISPLAY:-:0}"
if [[ -z "${XAUTHORITY:-}" && -r "/run/user/$(id -u)/gdm/Xauthority" ]]; then
  export XAUTHORITY="/run/user/$(id -u)/gdm/Xauthority"
fi
# Both shortcuts share one lock so repeated clicks cannot race Compose.
exec 9>"$LOG_DIR/launch.lock"
if ! flock -n 9; then
  if command -v notify-send >/dev/null 2>&1; then
    timeout 3 notify-send --expire-time=3000 '系统正在启动' '请稍候，启动完成后会自动打开页面。' >/dev/null 2>&1 || true
  fi
  exit 0
fi
touch "$LOG_FILE"

PROGRESS_PID=''
PROGRESS_DIR=''
PROGRESS_OPEN=false

close_progress() {
  if [[ -n "$PROGRESS_PID" ]]; then
    kill "$PROGRESS_PID" 2>/dev/null || true
    wait "$PROGRESS_PID" 2>/dev/null || true
    PROGRESS_PID=''
  fi
  if "$PROGRESS_OPEN"; then
    exec 8>&-
    PROGRESS_OPEN=false
  fi
  if [[ -n "$PROGRESS_DIR" ]]; then
    rm -f "$PROGRESS_DIR/status"
    rmdir "$PROGRESS_DIR" 2>/dev/null || true
    PROGRESS_DIR=''
  fi
}

trap close_progress EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

show_progress() {
  command -v zenity >/dev/null 2>&1 || return 0
  PROGRESS_DIR="$(mktemp -d "$LOG_DIR/progress.XXXXXX")"
  mkfifo "$PROGRESS_DIR/status"
  # Keep a reader open so closing the dialog cannot interrupt startup writes.
  exec 8<>"$PROGRESS_DIR/status"
  PROGRESS_OPEN=true
  zenity --progress --pulsate --no-cancel --auto-close \
    --title='系统正在启动' --width=480 --height=160 \
    --text=$'正在检查系统，请稍候…\n启动完成后会自动打开页面，无需重复点击。' \
    <"$PROGRESS_DIR/status" >>"$LOG_FILE" 2>&1 8>&- 9>&- &
  PROGRESS_PID=$!
}

progress() {
  if "$PROGRESS_OPEN"; then
    printf '# %s\n' "$1" >&8
  fi
}

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG_FILE"
}

fail() {
  local message="$1"
  log "ERROR: $message"
  close_progress
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
  progress '正在准备项目页面，请稍候…'
  if hmr_ready; then
    log 'Vite 热更新服务已就绪（3443）。'
    return
  fi

  log '启动 Vite 热更新服务（3443）。'
  nohup npm --prefix "$ROOT_DIR/apps/consultation/client" run dev:jetson >>"$VITE_LOG" 2>&1 </dev/null 8>&- 9>&- &
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
  progress '正在启动系统服务（含脑电），通常需要约半分钟，请稍候…'
  log '启动 Orin NX 全量服务（包含 EEG bridge）。'
  if ! stack up -d >>"$LOG_FILE" 2>&1; then
    fail "Docker 全量启动失败。请查看 $LOG_FILE"
  fi
  progress '服务已启动，正在等待系统就绪…'
  local ready=false
  for _ in $(seq 1 60); do
    if service_containers_ready; then
      ready=true
      break
    fi
    sleep 2
  done
  "$ready" || fail "部分系统服务尚未就绪。请查看 $LOG_FILE"
  ensure_hmr
}

open_kiosk() {
  progress '系统已就绪，正在打开全屏页面…'
  # Run with host NVIDIA graphics libraries, as verified on this Jetson.
  local browser="${MCS_CHROMIUM_BINARY:-/snap/chromium/current/usr/lib/chromium-browser/chrome}"
  [[ -x "$browser" ]] || fail "找不到 Chromium：$browser"

  export DISPLAY="${DISPLAY:-:0}"
  if [[ -z "${XAUTHORITY:-}" && -r "/run/user/$(id -u)/gdm/Xauthority" ]]; then
    export XAUTHORITY="/run/user/$(id -u)/gdm/Xauthority"
  fi

  # A separate profile prevents forwarding to an already running Snap instance.
  local profile="$HOME/.local/share/mcs-project-gpu"
  mkdir -p "$profile"
  log '打开项目封面并进入浏览器全屏模式。'
  nohup "$browser" --user-data-dir="$profile" --no-first-run \
    --no-default-browser-check --new-window --start-fullscreen \
    https://localhost:3443/ >>"$LOG_DIR/chromium.log" 2>&1 </dev/null 8>&- 9>&- &
}

show_progress

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
