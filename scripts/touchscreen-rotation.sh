#!/usr/bin/env bash
set -euo pipefail

# Keep the JRT touchscreen coordinate transform aligned with the active RandR
# rotation. This is useful on X11 when GNOME rotates the display but leaves
# the touchscreen's Coordinate Transformation Matrix unchanged.

OUTPUT="${TOUCH_ROTATION_OUTPUT:-DP-1}"
DEVICE="${TOUCH_ROTATION_DEVICE:-JRT Technology JRT T-YSD55LS-20P}"
POLL_SECONDS="${TOUCH_ROTATION_POLL_SECONDS:-0.15}"

usage() {
  echo "Usage: $0 [--watch | --rotate normal|left|right|inverted]" >&2
  exit 2
}

rotation_matrix() {
  case "$1" in
    normal)   echo "1 0 0 0 1 0 0 0 1" ;;
    left)     echo "0 -1 1 1 0 0 0 0 1" ;;
    right)    echo "0 1 0 -1 0 1 0 0 1" ;;
    inverted) echo "-1 0 1 0 -1 1 0 0 1" ;;
    *) usage ;;
  esac
}

current_rotation() {
  xrandr --query | awk -v output="$OUTPUT" '
    $1 == output && $2 == "connected" {
      for (i = 3; i <= NF; i++) {
        if ($i ~ /^[0-9]+x[0-9]+\+/) {
          if ($(i + 1) == "left" || $(i + 1) == "right" || $(i + 1) == "inverted") {
            print $(i + 1)
          } else {
            print "normal"
          }
          exit
        }
      }
    }
  '
}

apply_rotation_matrix() {
  local rotation="$1"
  local matrix
  matrix="$(rotation_matrix "$rotation")"
  # The property is stable on this touchscreen, even if its numeric XInput ID changes.
  xinput set-prop "$DEVICE" "Coordinate Transformation Matrix" $matrix || return 1
  logger -t touchscreen-rotation "Applied $rotation transform to '$DEVICE' on $OUTPUT"
}

case "${1:---watch}" in
  --watch)
    ;;
  --rotate)
    [ "$#" -eq 2 ] || usage
    case "$2" in normal|left|right|inverted) ;; *) usage ;; esac
    xrandr --output "$OUTPUT" --rotate "$2"
    ;;
  *) usage ;;
esac

last_rotation=""
while true; do
  rotation="$(current_rotation || true)"
  if [[ -n "$rotation" && "$rotation" != "$last_rotation" ]]; then
    if apply_rotation_matrix "$rotation"; then
      last_rotation="$rotation"
    fi
  fi
  sleep "$POLL_SECONDS"
done
