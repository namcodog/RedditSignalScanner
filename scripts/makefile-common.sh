#!/usr/bin/env bash
# Common helper functions for Makefile targets.
# These functions allow us to keep the Makefile declarative while
# centralising shell logic that used to be duplicated across many targets.

set -euo pipefail

BACKEND_DIR="backend"
FRONTEND_DIR="frontend"
PYTHON_BIN="${PYTHON_BIN:-/opt/homebrew/bin/python3.11}"
CELERY_APP="${CELERY_APP:-app.core.celery_app.celery_app}"
CELERY_LOG="${CELERY_LOG:-/tmp/celery_worker.log}"
BACKEND_PORT="${BACKEND_PORT:-8006}"
FRONTEND_PORT="${FRONTEND_PORT:-3006}"
REDIS_PORT="${REDIS_PORT:-6379}"

load_backend_env() {
  if [[ -f "${BACKEND_DIR}/.env" ]]; then
    # shellcheck disable=SC2046
    export $(grep -v '^#' "${BACKEND_DIR}/.env" | xargs)
  fi
}

require_backend_env() {
  if [[ ! -f "${BACKEND_DIR}/.env" ]]; then
    cat <<'MSG'
⚠️  警告: backend/.env 不存在，请从 backend/.env.example 复制并配置
   建议: cp backend/.env.example backend/.env
MSG
  fi
}

start_celery_worker() {
  local mode=${1:-foreground}
  load_backend_env
  pushd "${BACKEND_DIR}" >/dev/null
  local cmd=("${PYTHON_BIN}" -m celery -A "${CELERY_APP}" worker --loglevel=info --pool=solo \
    --queues=analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue)
  if [[ "${mode}" == "background" ]]; then
    nohup "${cmd[@]}" >"${CELERY_LOG}" 2>&1 &
  else
    "${cmd[@]}"
  fi
  popd >/dev/null
}

stop_celery_worker() {
  pkill -f "celery.*worker" || true
}

run_backend_dev() {
  load_backend_env
  pushd "${BACKEND_DIR}" >/dev/null
  ENABLE_CELERY_DISPATCH=${ENABLE_CELERY_DISPATCH:-1} \
    uvicorn app.main:app --reload --host 0.0.0.0 --port "${BACKEND_PORT}"
  popd >/dev/null
}

start_backend_reload() {
  load_backend_env
  pushd "${BACKEND_DIR}" >/dev/null
  ENABLE_CELERY_DISPATCH=${ENABLE_CELERY_DISPATCH:-1} \
    nohup "${PYTHON_BIN}" -m uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT}" --reload > /tmp/backend_uvicorn.log 2>&1 &
  popd >/dev/null
}

start_backend_background() {
  load_backend_env
  pushd "${BACKEND_DIR}" >/dev/null
  ENABLE_CELERY_DISPATCH=${ENABLE_CELERY_DISPATCH:-1} \
    nohup "${PYTHON_BIN}" -m uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT}" > /tmp/backend_uvicorn.log 2>&1 &
  popd >/dev/null
}

start_frontend_background() {
  pushd "${FRONTEND_DIR}" >/dev/null
  nohup npm run dev -- --port "${FRONTEND_PORT}" > /tmp/frontend_vite.log 2>&1 &
  popd >/dev/null
}

check_redis() {
  redis-cli -p "${REDIS_PORT}" ping >/dev/null
}

check_backend_health() {
  curl -sf "http://localhost:${BACKEND_PORT}/api/healthz" >/dev/null
}

check_frontend_health() {
  curl -sf "http://localhost:${FRONTEND_PORT}/" >/dev/null
}
