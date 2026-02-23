#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
REPORT_DIR="$ROOT_DIR/reports/local-acceptance"
mkdir -p "$REPORT_DIR"

ts() { date +%Y%m%d-%H%M%S; }
STAMP=$(ts)
OUT_MD="$REPORT_DIR/pipeline-health-$STAMP.md"

BACKEND_PORT=${BACKEND_PORT:-8006}

echo "# Pipeline Health ($STAMP)" | tee "$OUT_MD"
echo "" | tee -a "$OUT_MD"

section() { echo -e "\n## $1" | tee -a "$OUT_MD"; }
code() { echo '```' | tee -a "$OUT_MD"; cat "$1" | tee -a "$OUT_MD"; echo '```' | tee -a "$OUT_MD"; }

# 1) Celery configuration + health
section "Celery"
(
  echo "### verify_celery_config.py" 
  PYTHONPATH=backend /opt/homebrew/bin/python3.11 backend/scripts/verify_celery_config.py || true
  echo
  echo "### check_celery_health.py"
  PYTHONPATH=backend /opt/homebrew/bin/python3.11 backend/scripts/check_celery_health.py || true
) 2>&1 | tee -a "$OUT_MD"

# 2) Beat schedule (short dump)
section "Beat schedule snapshot"
PYTHONPATH=backend /opt/homebrew/bin/python3.11 - <<'PY' | tee -a "$OUT_MD" || true
from app.core.celery_app import celery_app
for name, cfg in celery_app.conf.beat_schedule.items():
    task = cfg.get("task")
    sched = cfg.get("schedule")
    print(f"- {name}: {task} | minute={getattr(sched,'minute',None)} hour={getattr(sched,'hour',None)}")
PY

# 3) Community pool
section "Community pool"
make -s pool-stats 2>&1 | tee -a "$OUT_MD" || true

# 4) Posts growth (7d)
section "Posts growth (7d)"
make -s posts-growth-7d 2>&1 | tee -a "$OUT_MD" || true

# 5) Redis hot cache keys
section "Redis hot cache"
bash scripts/crawl_health_snapshot.sh 2>&1 | tee -a "$OUT_MD" || true

echo "" | tee -a "$OUT_MD"
echo "Done. Report: $OUT_MD" | tee -a "$OUT_MD"

