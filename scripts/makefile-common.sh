#!/usr/bin/env bash
# Common helper functions for Makefile targets.
# These functions allow us to keep the Makefile declarative while
# centralising shell logic that used to be duplicated across many targets.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BACKEND_DIR="backend"
FRONTEND_DIR="frontend"
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "${PYTHON_BIN}" ]]; then
  if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
    PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
  elif [[ -x "${ROOT_DIR}/venv/bin/python" ]]; then
    PYTHON_BIN="${ROOT_DIR}/venv/bin/python"
  else
    PYTHON_BIN="/opt/homebrew/bin/python3.11"
  fi
fi
CELERY_APP="${CELERY_APP:-app.core.celery_app.celery_app}"
CELERY_WORKER_LOG="${CELERY_WORKER_LOG:-/tmp/celery_worker.log}"
# Backwards compatibility: some older scripts used CELERY_LOG
CELERY_LOG="${CELERY_LOG:-$CELERY_WORKER_LOG}"
BACKEND_PORT="${BACKEND_PORT:-8006}"
FRONTEND_PORT="${FRONTEND_PORT:-3006}"
REDIS_PORT="${REDIS_PORT:-6379}"

load_backend_env() {
  if [[ -f "${BACKEND_DIR}/.env" ]]; then
    # 规则：显式环境变量优先，.env 只填“没设置的”
    while IFS= read -r line; do
      # 去掉注释与空行
      line="${line%%#*}"
      line="${line#"${line%%[![:space:]]*}"}"
      line="${line%"${line##*[![:space:]]}"}"
      [[ -z "${line}" ]] && continue
      [[ "${line}" != *"="* ]] && continue

      key="${line%%=*}"
      value="${line#*=}"
      key="${key#"${key%%[![:space:]]*}"}"
      key="${key%"${key##*[![:space:]]}"}"

      # 如果外部已经设置过（哪怕是 0/false），就别用 .env 覆盖
      if [[ -n "${!key-}" ]]; then
        continue
      fi

      # 去掉成对引号
      if [[ "${value}" == \"*\" && "${value}" == *\" ]]; then
        value="${value:1:-1}"
      elif [[ "${value}" == \'*\' && "${value}" == *\' ]]; then
        value="${value:1:-1}"
      fi

      export "${key}=${value}"
    done < "${BACKEND_DIR}/.env"
  fi
  export NO_PROXY="localhost,127.0.0.1,::1"
  export no_proxy="localhost,127.0.0.1,::1"
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
  local queues="${CELERY_QUEUES:-analysis_queue}"
  local cmd=(env SQLALCHEMY_DISABLE_POOL=1 "${PYTHON_BIN}" -m celery -A "${CELERY_APP}" worker --loglevel=info --pool=solo \
    --queues="${queues}")
  if [[ "${mode}" == "background" ]]; then
    nohup "${cmd[@]}" >"${CELERY_WORKER_LOG}" 2>&1 &
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
