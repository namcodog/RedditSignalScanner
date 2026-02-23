#!/bin/bash
# 高速测试脚本：小规模 + 纯抓取 + 监控吞吐

set -e

echo "=========================================="
echo "高速评论回填测试"
echo "=========================================="
echo "配置："
echo "  - BATCH_SIZE: 5"
echo "  - limit-per-post: 200"
echo "  - skip-labeling: true"
echo "  - subreddit: r/FacebookAds"
echo "  - since-days: 7"
echo "  - page-size: 100"
echo "=========================================="
echo ""

cd backend

# 记录开始时间
START_TIME=$(date +%s)

# 运行脚本
COMMENTS_BACKFILL_BATCH_SIZE=5 \
python -u scripts/backfill_comments_for_posts.py \
  --subreddits r/FacebookAds \
  --since-days 7 \
  --page-size 100 \
  --commit-interval 1 \
  --skip-labeling \
  --limit-per-post 200 \
  --mode full

# 记录结束时间
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "=========================================="
echo "测试完成！"
echo "总耗时: ${DURATION} 秒"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 检查日志中的 '每分钟处理评论数'"
echo "2. 查询数据库确认新增评论数："
echo "   SELECT COUNT(*) FROM comments WHERE created_at > NOW() - INTERVAL '10 minutes';"
echo "3. 检查是否有僵尸连接："
echo "   SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'idle in transaction';"
echo "=========================================="

