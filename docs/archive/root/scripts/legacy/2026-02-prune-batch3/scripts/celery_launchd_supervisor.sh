#!/bin/bash
#
# launchd supervisor script to manage Celery worker and beat processes.
# Starts the processes if missing and performs periodic health checks.

set -euo pipefail

REPO_ROOT="/Users/hujia/Desktop/RedditSignalScanner"
BACKEND_DIR="$REPO_ROOT/backend"
PYTHON_BIN="/opt/homebrew/bin/python3.11"
CELERY_APP="app.core.celery_app"
LOG_DIR="$HOME/Library/Logs/reddit-scanner"
WORKER_LOG="$LOG_DIR/celery-worker.log"
BEAT_LOG="$LOG_DIR/celery-beat.log"
SUPERVISOR_LOG="$LOG_DIR/celery-supervisor.log"
HEALTH_SCRIPT="$REPO_ROOT/scripts/celery_health_check.sh"
SLEEP_SECONDS=60

mkdir -p "$LOG_DIR"

log() {
  local msg="$1"
  printf "%s %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$msg" >> "$SUPERVISOR_LOG"
}

start_worker() {
  if "$HEALTH_SCRIPT" --worker >/dev/null 2>&1; then
    return
  fi
  log "Starting Celery worker"
  cd "$BACKEND_DIR"
  PYTHONPATH="$BACKEND_DIR" "$PYTHON_BIN" -m celery -A "$CELERY_APP" worker --loglevel=info --pool=solo >> "$WORKER_LOG" 2>&1 &
  WORKER_PIDS+=("$!")
}

start_beat() {
  if "$HEALTH_SCRIPT" --beat >/dev/null 2>&1; then
    return
  fi
  log "Starting Celery beat"
  cd "$BACKEND_DIR"
  PYTHONPATH="$BACKEND_DIR" "$PYTHON_BIN" -m celery -A "$CELERY_APP" beat --loglevel=info >> "$BEAT_LOG" 2>&1 &
  BEAT_PIDS+=("$!")
}

cleanup() {
  log "Received termination signal, shutting down child processes"
  for pid in "${WORKER_PIDS[@]:-}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done
  for pid in "${BEAT_PIDS[@]:-}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done
  exit 0
}

trap cleanup INT TERM

WORKER_PIDS=()
BEAT_PIDS=()

log "Supervisor started"

while true; do
  if ! "$HEALTH_SCRIPT" --worker >/dev/null 2>&1; then
    start_worker
  fi

  if ! "$HEALTH_SCRIPT" --beat >/dev/null 2>&1; then
    start_beat
  fi

  sleep "$SLEEP_SECONDS"
done
