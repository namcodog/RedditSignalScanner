#!/usr/bin/env bash
# Probe Worker：只监听 probe_queue（并发更小，避免挤占 backfill）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load backend/.env if present (best-effort)
if [ -f "${SCRIPT_DIR}/.env" ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' "${SCRIPT_DIR}/.env" | xargs) || true
  echo "✅ 已加载 backend/.env"
fi

cd "${SCRIPT_DIR}"

exec python -m celery -A app.core.celery_app:celery_app worker \
  --loglevel=info \
  --pool="${CELERY_POOL:-solo}" \
  --concurrency="${PROBE_WORKER_CONCURRENCY:-1}" \
  --queues="probe_queue"

