#!/usr/bin/env bash
# Bulk Worker：监听 backfill/compensation 等队列（明确不监听 patrol_queue / probe_queue）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load backend/.env if present (best-effort)
if [ -f "${SCRIPT_DIR}/.env" ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' "${SCRIPT_DIR}/.env" | xargs) || true
  echo "✅ 已加载 backend/.env"
fi

cd "${SCRIPT_DIR}"

# 注意：这里刻意不包含 patrol_queue（防止抢巡航保底资源）
QUEUE_LIST="${BULK_QUEUE_LIST:-backfill_queue,compensation_queue,analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue}"

exec python -m celery -A app.core.celery_app:celery_app worker \
  --loglevel=info \
  --pool="${CELERY_POOL:-solo}" \
  --concurrency="${BULK_WORKER_CONCURRENCY:-2}" \
  --queues="${QUEUE_LIST}"
