#!/usr/bin/env bash
# Start/stop the Thusa review app without systemd (runbook RB-08). Binds to 127.0.0.1 only.
#   scripts/review-app.sh start|stop|restart|status        PORT=8765 by default
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8765}"
RUN_DIR="$ROOT/data/review"
PID_FILE="$RUN_DIR/serve.pid"
LOG_FILE="$RUN_DIR/serve.log"
mkdir -p "$RUN_DIR" && chmod 700 "$RUN_DIR"

running() { [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; }

case "${1:-status}" in
  start)
    if running; then echo "already running: pid $(cat "$PID_FILE") port $PORT"; exit 0; fi
    cd "$ROOT"
    uv sync --frozen --quiet
    setsid nohup "$ROOT/.venv/bin/pf" serve --host 127.0.0.1 --port "$PORT" >>"$LOG_FILE" 2>&1 < /dev/null &
    echo $! > "$PID_FILE"
    for _ in $(seq 1 30); do
      if curl -fsS "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
        echo "started: pid $(cat "$PID_FILE") http://127.0.0.1:$PORT/ (log $LOG_FILE)"; exit 0
      fi
      sleep 0.5
    done
    echo "did not become healthy; see $LOG_FILE" >&2; exit 1 ;;
  stop)
    if running; then kill "$(cat "$PID_FILE")"; rm -f "$PID_FILE"; echo stopped; else echo "not running"; fi ;;
  restart) "$0" stop; "$0" start ;;
  status)
    if running; then echo "running: pid $(cat "$PID_FILE") port $PORT"; curl -fsS "http://127.0.0.1:$PORT/healthz"; echo
    else echo "not running"; exit 3; fi ;;
  *) echo "usage: $0 start|stop|restart|status" >&2; exit 2 ;;
esac
