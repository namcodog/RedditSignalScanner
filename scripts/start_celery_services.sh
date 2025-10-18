#!/bin/bash
#
# Start Celery Worker and Beat services
# This script is idempotent - safe to run multiple times

set -euo pipefail

REPO_ROOT="/Users/hujia/Desktop/RedditSignalScanner"
BACKEND_DIR="$REPO_ROOT/backend"
VENV_PYTHON="$REPO_ROOT/venv/bin/python3"
CELERY_APP="app.core.celery_app:celery_app"
LOG_DIR="$HOME/Library/Logs/reddit-scanner"
WORKER_LOG="$LOG_DIR/celery-worker.log"
BEAT_LOG="$LOG_DIR/celery-beat.log"
HEALTH_SCRIPT="$REPO_ROOT/scripts/celery_health_check.sh"

# Create log directory
mkdir -p "$LOG_DIR"

# Function to start worker
start_worker() {
    if "$HEALTH_SCRIPT" --worker >/dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Celery Worker already running"
        return 0
    fi
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Celery Worker..."
    cd "$BACKEND_DIR"
    
    # Set environment variables
    export PYTHONPATH="$BACKEND_DIR"
    export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_scanner"
    export ENABLE_CELERY_DISPATCH=1
    
    # Start worker in background
    nohup "$VENV_PYTHON" -m celery -A "$CELERY_APP" worker \
        --loglevel=info \
        --pool=solo \
        --queues=analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue \
        >> "$WORKER_LOG" 2>&1 &
    
    sleep 2
    
    if "$HEALTH_SCRIPT" --worker >/dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Celery Worker started successfully"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ Failed to start Celery Worker"
        return 1
    fi
}

# Function to start beat
start_beat() {
    if "$HEALTH_SCRIPT" --beat >/dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Celery Beat already running"
        return 0
    fi
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Celery Beat..."
    cd "$BACKEND_DIR"
    
    # Set environment variables
    export PYTHONPATH="$BACKEND_DIR"
    export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_scanner"
    
    # Start beat in background
    nohup "$VENV_PYTHON" -m celery -A "$CELERY_APP" beat \
        --loglevel=info \
        >> "$BEAT_LOG" 2>&1 &
    
    sleep 2
    
    if "$HEALTH_SCRIPT" --beat >/dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Celery Beat started successfully"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ Failed to start Celery Beat"
        return 1
    fi
}

# Main execution
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Celery services..."

start_worker
start_beat

echo "[$(date '+%Y-%m-%d %H:%M:%S')] All services started"

# Show status
echo ""
echo "=== Celery Process Status ==="
pgrep -afl "celery" || echo "No Celery processes found"

