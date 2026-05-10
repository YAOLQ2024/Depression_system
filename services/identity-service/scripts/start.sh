#!/bin/sh
set -eu

export PYTHONPATH="/app${PYTHONPATH:+:$PYTHONPATH}"

max_attempts="${MIGRATION_MAX_ATTEMPTS:-20}"
retry_delay="${MIGRATION_RETRY_DELAY_SECONDS:-3}"
attempt=1

while true; do
  if alembic upgrade head; then
    break
  fi

  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "identity-service migrations failed after ${attempt} attempts" >&2
    exit 1
  fi

  echo "identity-service migrations failed on attempt ${attempt}; retrying in ${retry_delay}s..." >&2
  attempt=$((attempt + 1))
  sleep "$retry_delay"
done

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
