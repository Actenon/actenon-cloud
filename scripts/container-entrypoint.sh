#!/usr/bin/env bash
set -euo pipefail

COMMAND="${1:-web}"
if [[ $# -gt 0 ]]; then
  shift
fi

HOST="${ACTION_CONTROL_PLANE_HOST:-0.0.0.0}"
PORT="${ACTION_CONTROL_PLANE_PORT:-8000}"
EVIDENCE_ROOT="${ACTION_CONTROL_PLANE_EVIDENCE_STORAGE_ROOT:-}"

if command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  echo "python runtime not found" >&2
  exit 127
fi

if [[ -n "$EVIDENCE_ROOT" ]]; then
  mkdir -p "$EVIDENCE_ROOT"
fi

case "$COMMAND" in
  migrate)
    exec "$PYTHON_BIN" -m alembic upgrade head "$@"
    ;;
  web)
    exec "$PYTHON_BIN" -m uvicorn app.main:app --host "$HOST" --port "$PORT" "$@"
    ;;
  migrate-and-web)
    "$PYTHON_BIN" -m alembic upgrade head
    exec "$PYTHON_BIN" -m uvicorn app.main:app --host "$HOST" --port "$PORT" "$@"
    ;;
  *)
    exec "$COMMAND" "$@"
    ;;
esac
