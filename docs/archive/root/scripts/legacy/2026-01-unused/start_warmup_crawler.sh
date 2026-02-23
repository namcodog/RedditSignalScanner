#!/usr/bin/env bash
# Day 13 warm-up crawler bootstrap script.
# 责任：Backend B 按任务表启动 Celery Beat + Worker。

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/tmp"
mkdir -p "${LOG_DIR}"

ENV_FILE="${PROJECT_ROOT}/.env"
if [ -f "${ENV_FILE}" ]; then
  set -a
  source "${ENV_FILE}"
  set +a
fi
# 默认开启统一词库，并指定词库路径（如需覆盖可通过外部环境变量）
export ENABLE_UNIFIED_LEXICON="${ENABLE_UNIFIED_LEXICON:-true}"
export SEMANTIC_LEXICON_PATH="${SEMANTIC_LEXICON_PATH:-${PROJECT_ROOT}/config/semantic_sets/crossborder_v2.1.yml}"

export PYTHONPATH="${PROJECT_ROOT}"
export CELERY_BROKER_URL="${CELERY_BROKER_URL:-redis://localhost:6379/1}"
export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-redis://localhost:6379/2}"
# 固定节点名，避免 DuplicateNodenameWarning；%h 会替换主机名
HOST="$(hostname)"
BEAT_NODE="warmup-beat@${HOST}"
WORKER_NODE="warmup-worker@${HOST}"

SCHED_FILE="${LOG_DIR}/celerybeat-schedule.db"
echo "[INFO] 启动 Celery Beat（日志: ${LOG_DIR}/celery_beat.log, schedule: ${SCHED_FILE}）"
celery -A app.core.celery_app beat \
  --loglevel=info \
  --hostname="${BEAT_NODE}" \
  --schedule "${SCHED_FILE}" > "${LOG_DIR}/celery_beat.log" 2>&1 &
BEAT_PID=$!

echo "[INFO] 启动 Celery Worker（日志: ${LOG_DIR}/celery_worker.log）"
celery -A app.core.celery_app worker \
  --hostname="${WORKER_NODE}" \
  --loglevel=info \
  --concurrency="${CELERY_WARMUP_CONCURRENCY:-2}" \
  > "${LOG_DIR}/celery_worker.log" 2>&1 &
WORKER_PID=$!

echo "[INFO] Celery Beat PID: ${BEAT_PID}"
echo "[INFO] Celery Worker PID: ${WORKER_PID}"
echo "[提示] 使用 'kill ${BEAT_PID} ${WORKER_PID}' 停止服务。"
