#!/usr/bin/env bash
# Day 1 数据增长监控脚本
# 每5分钟检查一次数据增长情况

set -euo pipefail

LOG_FILE="/tmp/data_growth_monitor.log"
DB_NAME="reddit_signal_scanner"

echo "==> 数据增长监控启动 $(date)" | tee -a "$LOG_FILE"
echo "==> 监控间隔: 5分钟" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# 初始基线
BASELINE_TOTAL=$(psql -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM posts_hot;" | tr -d ' ')
BASELINE_TODAY=$(psql -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM posts_hot WHERE created_at >= CURRENT_DATE;" | tr -d ' ')

echo "📊 基线数据 ($(date +%H:%M:%S))" | tee -a "$LOG_FILE"
echo "  - 帖子总数: $BASELINE_TOTAL" | tee -a "$LOG_FILE"
echo "  - 今日新增: $BASELINE_TODAY" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

ITERATION=0

while true; do
  ITERATION=$((ITERATION + 1))
  sleep 300  # 5分钟
  
  CURRENT_TIME=$(date +%H:%M:%S)
  CURRENT_TOTAL=$(psql -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM posts_hot;" | tr -d ' ')
  CURRENT_TODAY=$(psql -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM posts_hot WHERE created_at >= CURRENT_DATE;" | tr -d ' ')
  CURRENT_HOUR=$(psql -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM posts_hot WHERE created_at >= NOW() - INTERVAL '1 hour';" | tr -d ' ')
  CURRENT_5MIN=$(psql -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM posts_hot WHERE created_at >= NOW() - INTERVAL '5 minutes';" | tr -d ' ')
  
  DELTA_TOTAL=$((CURRENT_TOTAL - BASELINE_TOTAL))
  DELTA_TODAY=$((CURRENT_TODAY - BASELINE_TODAY))
  
  echo "📈 监控 #$ITERATION ($CURRENT_TIME)" | tee -a "$LOG_FILE"
  echo "  - 帖子总数: $CURRENT_TOTAL (+$DELTA_TOTAL)" | tee -a "$LOG_FILE"
  echo "  - 今日新增: $CURRENT_TODAY (+$DELTA_TODAY)" | tee -a "$LOG_FILE"
  echo "  - 最近1小时: $CURRENT_HOUR" | tee -a "$LOG_FILE"
  echo "  - 最近5分钟: $CURRENT_5MIN" | tee -a "$LOG_FILE"
  
  # 检查是否有新数据
  if [ "$CURRENT_5MIN" -gt 0 ]; then
    echo "  ✅ 数据正在增长！" | tee -a "$LOG_FILE"
  else
    echo "  ⚠️  最近5分钟无新数据" | tee -a "$LOG_FILE"
  fi
  
  # 检查社区池
  ACTIVE_COMMUNITIES=$(psql -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM community_pool WHERE is_active = true;" | tr -d ' ')
  echo "  - 活跃社区: $ACTIVE_COMMUNITIES" | tee -a "$LOG_FILE"
  
  # 检查 Celery 任务
  CELERY_ACTIVE=$(cd /Users/hujia/Desktop/RedditSignalScanner/backend && PYTHONPATH=. python3 -c "
from app.core.celery_app import celery_app
inspect = celery_app.control.inspect()
active = inspect.active()
if active:
    total = sum(len(tasks) for tasks in active.values())
    print(total)
else:
    print(0)
" 2>/dev/null || echo "0")
  
  echo "  - Celery 活跃任务: $CELERY_ACTIVE" | tee -a "$LOG_FILE"
  echo "" | tee -a "$LOG_FILE"
  
  # 每小时生成一次详细报告
  if [ $((ITERATION % 12)) -eq 0 ]; then
    echo "📊 每小时详细报告 ($CURRENT_TIME)" | tee -a "$LOG_FILE"
    psql -d "$DB_NAME" -c "
    SELECT 
        DATE_TRUNC('hour', created_at) as hour,
        COUNT(*) as posts
    FROM posts_hot
    WHERE created_at >= NOW() - INTERVAL '24 hours'
    GROUP BY hour
    ORDER BY hour DESC
    LIMIT 24;
    " | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
  fi
done

