#!/usr/bin/env bash
# Lightweight auto-healer for local/dev environments.
# - Checks Celery health via backend/scripts/check_celery_health.py
# - If failed, restarts Beat + Worker using start_warmup_crawler.sh
# - Writes a short log to reports/local-acceptance/autoheal.log

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
LOG_DIR="$ROOT_DIR/reports/local-acceptance"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/autoheal.log"

INTERVAL=${INTERVAL:-60}

ts(){ date '+%Y-%m-%d %H:%M:%S'; }

echo "[autoheal] starting at $(ts), interval=${INTERVAL}s" | tee -a "$LOG_FILE"

while true; do
  if PYTHONPATH="$ROOT_DIR/backend" /opt/homebrew/bin/python3.11 "$ROOT_DIR/backend/scripts/check_celery_health.py" >/tmp/autoheal.check 2>&1; then
    echo "[$(ts)] OK $(tr -d '\n' </tmp/autoheal.check)" >> "$LOG_FILE"
  else
    echo "[$(ts)] FAIL -> restarting Celery" | tee -a "$LOG_FILE"
    # Best-effort stop
    pkill -f 'celery.*worker' 2>/dev/null || true
    pkill -f 'celery.*beat' 2>/dev/null || true
    sleep 1
    bash "$ROOT_DIR/backend/scripts/start_warmup_crawler.sh" >> "$LOG_FILE" 2>&1 || true
  fi
  sleep "$INTERVAL"
done

