#!/bin/bash
# Day 13: Celery Worker 启动脚本（加载环境变量）

set -e

# 加载 .env 文件
if [ -f "/Users/hujia/Desktop/RedditSignalScanner/backend/.env" ]; then
    export $(cat /Users/hujia/Desktop/RedditSignalScanner/backend/.env | grep -v '^#' | xargs)
    echo "✅ 已加载 backend/.env"
fi

# 启动 Celery Worker
cd /Users/hujia/Desktop/RedditSignalScanner/backend

exec /opt/homebrew/bin/python3.11 -m celery -A app.core.celery_app:celery_app worker \
  --loglevel=info \
  --pool=solo \
  --queues=analysis_queue,maintenance_queue,cleanup_queue,crawler_queue,monitoring_queue

