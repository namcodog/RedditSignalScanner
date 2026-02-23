#!/bin/bash
# 次高价值社区 - 分片1/3 抓取脚本（使用/new端点）
# 社区：r/AmazonDSPDrivers, r/AmazonFC, r/AmazonVine, r/AmazonWarehousingAndDelivery, r/FBAOnlineRetail

set -e

echo "=========================================="
echo "🚀 开始抓取：次高价值社区 - 分片1/3"
echo "=========================================="
echo "📋 社区数量：5个"
echo "📅 时间过滤：month（最近30天）"
echo "📊 每社区最大：1000帖子"
echo "✅ 使用/new端点（更可靠）"
echo "✅ 水位线：启用"
echo "✅ 断点续抓：启用"
echo "=========================================="

# 执行抓取
export PYTHONPATH=/Users/hujia/Desktop/RedditSignalScanner/backend:$PYTHONPATH
python backend/scripts/crawl_posts_new_endpoint.py \
  --csv 次高价值社区_15社区_shard1_of_3.csv \
  --time-filter month \
  --max-posts 1000 \
  --safe \
  --use-watermark \
  --resume \
  --progress-file tier2_new_shard1_progress.json \
  --max-retries 3 \
  2>&1 | tee logs/tier2_new_shard1_$(date +%Y%m%d_%H%M%S).log

echo ""
echo "=========================================="
echo "✅ 分片1/3 抓取完成！"
echo "=========================================="

