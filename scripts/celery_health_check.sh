#!/bin/bash
#
# Health check utility for Celery worker/beat processes.
# Returns 0 when all requested processes are running, non-zero otherwise.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATTERN_WORKER="celery.*app.core.celery_app.*worker"
PATTERN_BEAT="celery.*app.core.celery_app.*beat"

usage() {
  cat <<'EOF'
Usage: celery_health_check.sh [--worker] [--beat] [--all]

Checks whether Celery worker and/or beat processes are running for the
Reddit Signal Scanner project. Exit code 0 indicates healthy.
EOF
}

check_process() {
  local pattern="$1"
  if pgrep -fl "$pattern" >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

MODE_WORKER=false
MODE_BEAT=false

if [[ $# -eq 0 ]]; then
  MODE_WORKER=true
  MODE_BEAT=true
else
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --worker)
        MODE_WORKER=true
        ;;
      --beat)
        MODE_BEAT=true
        ;;
      --all)
        MODE_WORKER=true
        MODE_BEAT=true
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Unknown argument: $1" >&2
        usage
        exit 2
        ;;
    esac
    shift
  done
fi

FAILED=false

if "$MODE_WORKER"; then
  if ! check_process "$PATTERN_WORKER"; then
    echo "Celery worker not running" >&2
    FAILED=true
  fi
fi

if "$MODE_BEAT"; then
  if ! check_process "$PATTERN_BEAT"; then
    echo "Celery beat not running" >&2
    FAILED=true
  fi
fi

if "$FAILED"; then
  exit 1
fi

exit 0
