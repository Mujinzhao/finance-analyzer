#!/usr/bin/env bash
[ -z "${BASH_VERSION:-}" ] && exec bash "$0" "$@"
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/.run/services.pid"

kill_port() {
  local pids
  pids=$(lsof -ti "TCP:$1" -sTCP:LISTEN 2>/dev/null || true)
  [ -n "$pids" ] && kill $pids 2>/dev/null || true
}

if [ -f "$PID_FILE" ]; then
  source "$PID_FILE"
  kill "${BACKEND_PID:-}" 2>/dev/null || true
  kill "${FRONTEND_PID:-}" 2>/dev/null || true
  rm -f "$PID_FILE"
fi

kill_port 8000
kill_port 3000

echo "[stop.sh] done"
