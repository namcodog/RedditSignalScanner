#!/usr/bin/env bash
set -euo pipefail

# Cleanup script for local/test environments (Day14).
# - Truncates Postgres tables
# - Flushes Redis cache DB
# - Removes generated validation reports
#
# Usage:
#   CLEANUP_CONFIRM=1 ./scripts/cleanup_test_data.sh
#   ./scripts/cleanup_test_data.sh --yes

confirm=${CLEANUP_CONFIRM:-0}
if [[ "${1:-}" == "--yes" ]]; then
  confirm=1
fi

if [[ "$confirm" != "1" ]]; then
  echo "[SAFEGUARD] Set CLEANUP_CONFIRM=1 or pass --yes to proceed." >&2
  exit 2
fi

DATABASE_URL=${DATABASE_URL:-"postgresql://postgres:postgres@localhost:5432/reddit_scanner"}
REDIS_URL=${REDIS_URL:-"redis://localhost:6379/5"}

normalized_database_url="$DATABASE_URL"
normalized_database_url="${normalized_database_url/postgresql+asyncpg/postgresql}"
normalized_database_url="${normalized_database_url/postgresql+psycopg/postgresql}"
normalized_database_url="${normalized_database_url/postgresql+psycopg2/postgresql}"

db_name="${normalized_database_url##*/}"
db_name="${db_name%%\?*}"

if [[ -z "$db_name" ]]; then
  echo "[SAFEGUARD] Could not parse database name from DATABASE_URL." >&2
  exit 2
fi

if [[ "$db_name" != *_test && "$db_name" != "reddit_scanner" ]]; then
  if [[ "${CLEANUP_ALLOW_NONTEST_DB:-0}" != "1" ]]; then
    echo "[SAFEGUARD] Refusing to cleanup non-test DB '$db_name'." >&2
    echo "           Set CLEANUP_ALLOW_NONTEST_DB=1 to override." >&2
    exit 2
  fi
fi

DATABASE_URL="$normalized_database_url"
echo "[INFO] Target database: $db_name"

echo "[INFO] Cleaning Postgres data ..."
psql "$DATABASE_URL" <<'SQL'
BEGIN;
TRUNCATE TABLE reports RESTART IDENTITY CASCADE;
TRUNCATE TABLE analyses RESTART IDENTITY CASCADE;
TRUNCATE TABLE tasks RESTART IDENTITY CASCADE;
TRUNCATE TABLE users RESTART IDENTITY CASCADE;
TRUNCATE TABLE community_pool RESTART IDENTITY CASCADE;
TRUNCATE TABLE pending_communities RESTART IDENTITY CASCADE;
COMMIT;
SQL

echo "[INFO] Flushing Redis DB ..."
if command -v redis-cli >/dev/null 2>&1; then
  redis-cli -u "$REDIS_URL" FLUSHDB || {
    echo "[WARN] redis-cli failed (URL: $REDIS_URL). Skipping." >&2
  }
else
  echo "[WARN] redis-cli not found. Skipping Redis flush." >&2
fi

echo "[INFO] Removing generated validation reports ..."
rm -f backend/config/seed_communities_validation_report.json || true

echo "✅ Cleanup completed."
