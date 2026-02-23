#!/bin/bash
# Watchdog script for AI Scorer
# Ensures the scoring script keeps running

LOG_FILE="logs/scoring_fast.log"
SCRIPT="backend/scripts/score_refinement_fast_direct.py"

echo "🐶 Starting Watchdog for Scorer..."

while true; do
    if pgrep -f "$SCRIPT" > /dev/null; then
        # It's running, do nothing
        sleep 60
    else
        echo "[$(date)] ⚠️ Scorer crashed or stopped. Restarting..." >> "$LOG_FILE"
        nohup python3 "$SCRIPT" >> "$LOG_FILE" 2>&1 &
        echo "[$(date)] ✅ Scorer restarted." >> "$LOG_FILE"
        sleep 10
    fi
done
