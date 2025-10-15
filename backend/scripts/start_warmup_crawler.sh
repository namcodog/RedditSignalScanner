#!/usr/bin/env bash
# Day 13 warm-up crawler bootstrap script.
# 责任：Backend B 按任务表启动 Celery Beat + Worker。

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/tmp"
mkdir -p "${LOG_DIR}"

export PYTHONPATH="${PROJECT_ROOT}"
export CELERY_BROKER_URL="${CELERY_BROKER_URL:-redis://localhost:6379/1}"
export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-redis://localhost:6379/2}"

echo "[INFO] 启动 Celery Beat（日志: ${LOG_DIR}/celery_beat.log）"
celery -A app.core.celery_app beat --loglevel=info > "${LOG_DIR}/celery_beat.log" 2>&1 &
BEAT_PID=$!

echo "[INFO] 启动 Celery Worker（日志: ${LOG_DIR}/celery_worker.log）"
celery -A app.core.celery_app worker \
  --loglevel=info \
  --concurrency="${CELERY_WARMUP_CONCURRENCY:-2}" \
  > "${LOG_DIR}/celery_worker.log" 2>&1 &
WORKER_PID=$!

echo "[INFO] Celery Beat PID: ${BEAT_PID}"
echo "[INFO] Celery Worker PID: ${WORKER_PID}"
echo "[提示] 使用 'kill ${BEAT_PID} ${WORKER_PID}' 停止服务。"
