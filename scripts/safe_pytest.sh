#!/bin/bash
# safe_pytest.sh — Run pytest without touching the database
#
# Usage:
#   ./scripts/safe_pytest.sh              # Collect-only (verify imports)
#   ./scripts/safe_pytest.sh --run        # Run non-DB tests
#   ./scripts/safe_pytest.sh --run -k "test_foo"  # Run specific test
#
# SAFETY: Forces SKIP_DB_RESET=1 to prevent any TRUNCATE operations

set -euo pipefail

export SKIP_DB_RESET=1

cd "$(dirname "$0")/../backend"

if [[ "${1:-}" == "--run" ]]; then
    shift
    echo "🧪 Running non-DB tests (SKIP_DB_RESET=1)..."
    python -m pytest tests/ -q --ignore=tests/e2e "$@"
else
    echo "🔍 Collect-only check (no tests executed)..."
    python -m pytest tests/ -q --co "$@"
fi
