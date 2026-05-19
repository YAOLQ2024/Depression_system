#!/bin/sh
set -eu

export PYTHONPATH="/app${PYTHONPATH:+:$PYTHONPATH}"

auto_fetch_dolphin_asr() {
  auto_fetch=$(printf '%s' "${AUTO_FETCH_DOLPHIN_ASR:-true}" | tr '[:upper:]' '[:lower:]')
  case "$auto_fetch" in
    0|false|no|off)
      return 0
      ;;
  esac

  model_name="${DOLPHIN_MODEL_NAME:-base.cn.streaming}"
  model_dir="${DOLPHIN_MODEL_DIR:-/app/runtime-assets/asr/$model_name}"
  if [ -d "$model_dir" ] && find "$model_dir" -maxdepth 1 -type f ! -name 'README.md' ! -name '.gitkeep' | grep -q .; then
    return 0
  fi

  echo "[INFO] Dolphin ASR assets are missing; downloading $model_name runtime assets..."
  python ./scripts/fetch_dolphin_model.py
}

auto_fetch_dolphin_asr
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
