#!/bin/bash
# 监控 posts_raw / comments 数据增长情况（每次执行打印一次快照）

set -euo pipefail

echo "=== $(date) ==="

# 默认 DATABASE_URL（本地开发环境），如果未显式设置的话
: "${DATABASE_URL:=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner}"

psql "${DATABASE_URL//+asyncpg/}" -c "
SELECT
  'posts_raw' AS table_name,
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '4 hours') AS last_4h
FROM posts_raw
UNION ALL
SELECT
  'comments' AS table_name,
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE created_utc > NOW() - INTERVAL '4 hours') AS last_4h
FROM comments;
"

echo ""
