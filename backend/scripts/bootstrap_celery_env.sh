#!/usr/bin/env bash
#
# Celery/Redis environment bootstrap helper aligned with
# PRD/PRD-04-任务系统.md §3.1-3.2 and docs/2025-10-10-实施检查清单.md Day1-3.
#
# Responsibilities:
#   1. Verify Redis broker connectivity before queue operations.
#   2. Validate Celery CLI availability and provide dynamic worker settings per PRD.
#   3. Offer a reproducible worker start command with health check hooks.
#
# Usage:
#   ./bootstrap_celery_env.sh check          # run Redis + Celery health checks
#   ./bootstrap_celery_env.sh start-worker   # start a worker using PRD defaults
#   ./bootstrap_celery_env.sh help           # print usage

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Ensure backend modules resolve when invoking Celery (PRD-04 §2.1).
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

log() {
    printf '[bootstrap][%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

abort() {
    log "ERROR: $*"
    exit 1
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        abort "Command '$1' not found; please install it before continuing."
    fi
}

BROKER_URL="${CELERY_BROKER_URL:-redis://localhost:6379/1}"
RESULT_BACKEND="${CELERY_RESULT_BACKEND:-redis://localhost:6379/2}"
QUEUE_NAMES="${CELERY_QUEUE_NAMES:-analysis_queue,maintenance_queue,cleanup_queue,monitoring_queue}"
LOG_LEVEL="${CELERY_LOG_LEVEL:-info}"
WORKER_NAME_DEFAULT="celery@$(hostname)-dev-%n"
WORKER_NAME="${CELERY_WORKER_NAME:-${WORKER_NAME_DEFAULT}}"

# Allow callers to inject a runner prefix (e.g. "poetry run").
read -r -a CELERY_CMD_PREFIX <<<"${CELERY_CMD_PREFIX:-}"
CELERY_BIN="${CELERY_BIN:-celery}"

calculate_concurrency() {
    if [[ -n "${CELERY_WORKER_COUNT:-}" ]]; then
        printf '%s' "${CELERY_WORKER_COUNT}"
        return
    fi

    python_cmd="${PYTHON_BIN:-python3}"
    if ! command -v "${python_cmd}" >/dev/null 2>&1; then
        python_cmd="python"
    fi

    "${python_cmd}" - <<'PYCODE' || printf '1'
import multiprocessing
print(min(multiprocessing.cpu_count(), 4))
PYCODE
}

WORKER_CONCURRENCY="$(calculate_concurrency)"

celery_exec() {
    if [[ ${#CELERY_CMD_PREFIX[@]} -gt 0 ]]; then
        "${CELERY_CMD_PREFIX[@]}" "${CELERY_BIN}" "$@"
    else
        "${CELERY_BIN}" "$@"
    fi
}

celery_app_exec() {
    celery_exec -A app.core.celery_app "$@"
}

check_redis() {
    require_cmd redis-cli
    log "Checking Redis broker connectivity at ${BROKER_URL}..."
    if ! redis-cli -u "${BROKER_URL}" --raw ping >/tmp/bootstrap_celery_ping 2>&1; then
        cat /tmp/bootstrap_celery_ping >&2 || true
        abort "Redis ping failed. Ensure Redis is running and accessible."
    fi
    if ! grep -qx 'PONG' /tmp/bootstrap_celery_ping; then
        cat /tmp/bootstrap_celery_ping >&2
        abort "Unexpected Redis ping response."
    fi
    log "Redis responded with PONG."
}

check_celery_cli() {
    log "Validating Celery CLI availability..."
    if ! celery_exec --version >/tmp/bootstrap_celery_version 2>&1; then
        cat /tmp/bootstrap_celery_version >&2 || true
        abort "Celery CLI check failed. Verify virtualenv activation and requirements."
    fi
    log "Celery CLI detected: $(head -n1 /tmp/bootstrap_celery_version)."
}

check_worker_health() {
    log "Querying Celery worker heartbeat (timeout 5s)..."
    if ! celery_app_exec inspect ping --timeout=5 >/tmp/bootstrap_celery_inspect 2>&1; then
        cat /tmp/bootstrap_celery_inspect >&2 || true
        abort "Celery inspect ping failed; ensure a worker is running."
    fi
    if grep -qiE 'Error|failed|no nodes replied' /tmp/bootstrap_celery_inspect; then
        cat /tmp/bootstrap_celery_inspect >&2
        abort "Celery reported no active workers."
    fi
    log "Celery worker responded:\n$(cat /tmp/bootstrap_celery_inspect)"
}

start_worker() {
    check_redis
    check_celery_cli

    log "Starting Celery worker with concurrency=${WORKER_CONCURRENCY}, queues=${QUEUE_NAMES}..."
    celery_app_exec worker \
        --loglevel="${LOG_LEVEL}" \
        --queues="${QUEUE_NAMES}" \
        --hostname="${WORKER_NAME}" \
        --concurrency="${WORKER_CONCURRENCY}" \
        --prefetch-multiplier=1
}

print_usage() {
    cat <<EOF
Celery/Redis bootstrap helper.

Environment (override via export):
  CELERY_BROKER_URL         Redis broker URL (default ${BROKER_URL})
  CELERY_RESULT_BACKEND     Redis backend URL (default ${RESULT_BACKEND})
  CELERY_QUEUE_NAMES        Comma-separated queue list (default ${QUEUE_NAMES})
  CELERY_WORKER_NAME        Worker hostname (default ${WORKER_NAME_DEFAULT})
  CELERY_WORKER_COUNT       Override worker concurrency (PRD-04 决策3)
  CELERY_CMD_PREFIX         Runner prefix, e.g. "poetry run"
  CELERY_LOG_LEVEL          Worker log level (default ${LOG_LEVEL})
  TASK_STATUS_REDIS_URL     Redis instance for status cache (default redis://localhost:6379/3)

Commands:
  check          Verify Redis connectivity and running workers.
  start-worker   Launch a Celery worker with PRD-aligned defaults.
  help           Show this help message.
EOF
}

main() {
    case "${1:-help}" in
        check)
            check_redis
            check_celery_cli
            check_worker_health
            ;;
        start-worker)
            start_worker
            ;;
        help|--help|-h)
            print_usage
            ;;
        *)
            print_usage
            exit 1
            ;;
    esac
}

main "$@"
