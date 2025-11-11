#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
REPORT_DIR="$ROOT_DIR/reports/local-acceptance"
LOG_FILE="/tmp/celery_worker.log"
BACKEND_PORT=${BACKEND_PORT:-8006}

mkdir -p "$REPORT_DIR"

ts() { date +%Y%m%d-%H%M%S; }
STAMP=$(ts)
OUT_MD="$REPORT_DIR/crawl-health-$STAMP.md"

echo "# Crawl Health Snapshot ($STAMP)" | tee "$OUT_MD"
echo "" | tee -a "$OUT_MD"

# 1) Pool stats
echo "## Pool Stats" | tee -a "$OUT_MD"
POOL_STATS=$(make -s pool-stats || true)
echo "```" | tee -a "$OUT_MD"
echo "$POOL_STATS" | tee -a "$OUT_MD"
echo "```" | tee -a "$OUT_MD"

# 2) Redis DB detection for reddit:posts:*
echo "## Redis Hot Cache" | tee -a "$OUT_MD"
FOUND_DB=""
for DB in 0 1 2 3 4 5; do
  if KE=$(redis-cli -n "$DB" --scan --pattern 'reddit:posts:*' | head -n 1); then
    if [[ -n "$KE" ]]; then
      FOUND_DB=$DB
      break
    fi
  fi
done

if [[ -n "$FOUND_DB" ]]; then
  KEY_COUNT=$(redis-cli -n "$FOUND_DB" --scan --pattern 'reddit:posts:*' | wc -l | tr -d ' ')
  echo "Detected DB: db$FOUND_DB" | tee -a "$OUT_MD"
  echo "Keys (reddit:posts:*): $KEY_COUNT" | tee -a "$OUT_MD"
  echo "Sample keys:" | tee -a "$OUT_MD"
  redis-cli -n "$FOUND_DB" --scan --pattern 'reddit:posts:*' | head -n 5 | tee -a "$OUT_MD"
else
  echo "No reddit:posts:* keys found in db0–db5" | tee -a "$OUT_MD"
fi

# 3) Metrics daily snapshot
echo "" | tee -a "$OUT_MD"
echo "## Metrics Daily" | tee -a "$OUT_MD"
curl -s "http://localhost:${BACKEND_PORT}/api/metrics/daily" -o "$REPORT_DIR/metrics-daily.json" || true
if [[ -s "$REPORT_DIR/metrics-daily.json" ]]; then
  echo "Saved: reports/local-acceptance/metrics-daily.json" | tee -a "$OUT_MD"
  head -n 1 "$REPORT_DIR/metrics-daily.json" | tee -a "$OUT_MD"
else
  echo "metrics-daily unavailable" | tee -a "$OUT_MD"
fi

# 4) Celery last completion summary
echo "" | tee -a "$OUT_MD"
echo "## Last Crawl Summary (from Celery log)" | tee -a "$OUT_MD"
if [[ -f "$LOG_FILE" ]]; then
  grep -E "status': 'completed'|\{\'status\': \'completed\'" "$LOG_FILE" | tail -n 1 | tee -a "$OUT_MD" || echo "No completed line yet" | tee -a "$OUT_MD"
else
  echo "Log file not found: $LOG_FILE" | tee -a "$OUT_MD"
fi

echo "" | tee -a "$OUT_MD"
echo "Done. Snapshot: $OUT_MD" | tee -a "$OUT_MD"

