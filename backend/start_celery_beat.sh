#!/usr/bin/env bash
# Celery Beat 启动脚本（只负责调度，不执行任务）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load backend/.env if present (best-effort)
if [ -f "${SCRIPT_DIR}/.env" ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' "${SCRIPT_DIR}/.env" | xargs) || true
  echo "✅ 已加载 backend/.env"
fi

cd "${SCRIPT_DIR}"

exec python -m celery -A app.core.celery_app:celery_app beat \
  --loglevel=info

