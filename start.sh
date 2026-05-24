#!/usr/bin/env bash
[ -z "${BASH_VERSION:-}" ] && exec bash "$0" "$@"
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$SCRIPT_DIR/.run/services.pid"

mkdir -p "$LOG_DIR" "$SCRIPT_DIR/.run"

# Backend
cd "$SCRIPT_DIR/backend"
source venv/bin/activate 2>/dev/null || true
echo "[start.sh] starting backend on http://127.0.0.1:8000"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload \
  >> "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

# Frontend
cd "$SCRIPT_DIR/frontend"
echo "[start.sh] starting frontend on http://127.0.0.1:3000"
PORT=3000 npm start \
  >> "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

echo "BACKEND_PID=$BACKEND_PID" > "$PID_FILE"
echo "FRONTEND_PID=$FRONTEND_PID" >> "$PID_FILE"

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  rm -f "$PID_FILE"
}
trap cleanup INT TERM EXIT

echo "[start.sh] backend pid=$BACKEND_PID, frontend pid=$FRONTEND_PID"
echo "[start.sh] logs: $LOG_DIR/backend.log, $LOG_DIR/frontend.log"
echo "[start.sh] Press Ctrl+C to stop."

wait
