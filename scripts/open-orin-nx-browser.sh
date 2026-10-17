#!/usr/bin/env bash
set -euo pipefail
# Use host Jetson graphics libraries. The Snap wrapper selected software rendering
# on this board; the same browser binary uses NVIDIA EGL/GL successfully here.
browser="${MCS_CHROMIUM_BINARY:-/snap/chromium/current/usr/lib/chromium-browser/chrome}"
if [[ ! -x "$browser" ]]; then
  echo "Chromium binary not found: $browser" >&2
  exit 1
fi
export DISPLAY="${DISPLAY:-:0}"
if [[ -z "${XAUTHORITY:-}" && -r "/run/user/$(id -u)/gdm/Xauthority" ]]; then
  export XAUTHORITY="/run/user/$(id -u)/gdm/Xauthority"
fi
profile="${MCS_BROWSER_PROFILE:-$HOME/.local/share/mcs-chromium}"
mkdir -p "$profile"
# Chromium's own sandbox stays enabled; no software rendering or unsafe
# certificate bypass flags are added.
exec "$browser" --user-data-dir="$profile" --no-first-run \
  --no-default-browser-check "$@" https://localhost
