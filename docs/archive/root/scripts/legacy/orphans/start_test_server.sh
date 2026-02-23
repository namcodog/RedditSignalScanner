#!/usr/bin/env bash
# Day 9 test bootstrap script for frontend integration coverage.
# Implements tasks from reports/DAY9-TASK-ASSIGNMENT.md (lines 280-360).

set -euo pipefail

DB_NAME="reddit_scanner_test"
SERVER_PORT="${SERVER_PORT:-8006}"
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="/tmp/test_server.pid"
LOG_FILE="/tmp/test_server.log"

echo "Starting test environment..."

# 1. Truncate test database (best-effort to keep runs isolated)
if command -v psql >/dev/null 2>&1; then
  echo "-> Resetting database ${DB_NAME}"
  psql -U postgres -d "${DB_NAME}" -c "TRUNCATE users, tasks, analyses CASCADE;" >/dev/null 2>&1 || \
    echo "[WARN] Skipped truncation (first run or tables missing)"
else
  echo "[WARN] psql command not available; skipping database reset"
fi

# 2. Start FastAPI server
cd "${BACKEND_DIR}"
echo "-> Launching FastAPI on port ${SERVER_PORT}"
uvicorn app.main:app --host 0.0.0.0 --port "${SERVER_PORT}" >"${LOG_FILE}" 2>&1 &
SERVER_PID=$!

# 3. Wait for server to become ready
echo "-> Waiting for server readiness..."
sleep 3

# 4. Verify readiness
if curl -s "http://localhost:${SERVER_PORT}/docs" >/dev/null; then
  echo "[PASS] Test server started (pid=${SERVER_PID})"
  echo "${SERVER_PID}" > "${PID_FILE}"
else
  echo "[FAIL] Test server failed to start; inspect ${LOG_FILE}"
  kill "${SERVER_PID}" || true
  exit 1
fi
