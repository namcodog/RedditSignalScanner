#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
mkdir -p "${LOG_DIR}"

# Load backend/.env if present
if [ -f "${ROOT_DIR}/backend/.env" ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' "${ROOT_DIR}/backend/.env" | xargs) || true
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is missing" >&2
  exit 1
fi

COMMUNITIES=(
  'r/aquariums' 'r/cats' 'r/chatgpt' 'r/localllama' 'r/stablediffusion' 'r/saas'
  'r/promptengineering' 'r/dogs' 'r/malelivingspace' 'r/puppy101' 'r/pets'
  'r/battlestations' 'r/askelectronics' 'r/hvac' 'r/lawncare' 'r/automation'
  'r/cozyplaces' 'r/justrolledintotheshop' 'r/desksetup' 'r/airfryer' 'r/reeftank'
  'r/femalelivingspace' 'r/homeoffice' 'r/instantpot' 'r/amateurroomporn'
  'r/cleaning' 'r/organization'
)

COMMUNITY_SQL=$(printf "'%s'," "${COMMUNITIES[@]}" | sed 's/,$//')

while true; do
  queue_len=$(redis-cli -n 1 llen backfill_queue 2>/dev/null || echo "ERR")
  pending_count=$(psql "${DATABASE_URL//+asyncpg/}" -tAc "WITH runs AS (\
    SELECT NULLIF(metrics->'vetting'->>'crawl_run_id','') AS run_id\
    FROM discovered_communities\
    WHERE name IN (${COMMUNITY_SQL}) AND metrics ? 'vetting'\
  ), targets AS (\
    SELECT status FROM crawler_run_targets\
    WHERE crawl_run_id IN (SELECT run_id::uuid FROM runs WHERE run_id IS NOT NULL)\
  )\
  SELECT COUNT(*) FROM targets WHERE status IN ('queued','running');" 2>/dev/null || echo "ERR")

  ts=$(date '+%Y-%m-%d %H:%M:%S')
  echo "${ts} backfill_queue=${queue_len} pending_targets=${pending_count}"

  if [ "${queue_len}" = "0" ] && [ "${pending_count}" = "0" ]; then
    cd "${ROOT_DIR}/backend"
    python - <<'PY'
from app.core.celery_app import celery_app
result = celery_app.send_task("tasks.discovery.run_community_evaluation", queue="probe_queue")
print(result.id)
PY
    break
  fi
  sleep 60
done
