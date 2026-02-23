#!/bin/bash
# 次高价值社区 - 分片2/3 抓取脚本（改进版v2）
# 社区：r/Flipping, r/InstacartShoppers, r/ShopifyDropship, r/WalmartEmployees, r/amazonreviews

set -e

echo "=========================================="
echo "🚀 开始抓取：次高价值社区 - 分片2/3 (v2)"
echo "=========================================="
echo "📋 社区数量：5个"
echo "📅 时间范围：2024-01 ~ 2025-01（12个月）"
echo "📊 数据类型：帖子 + 评论"
echo "✅ 水位线：启用"
echo "✅ 断点续抓：启用"
echo "✅ 指数退避：最大重试3次"
echo "=========================================="

# 激活虚拟环境
source backend/.venv/bin/activate

# 执行抓取（改进版v2）
python -u backend/scripts/crawl_posts_from_csv_v2.py \
  --csv 次高价值社区_15社区_shard2_of_3.csv \
  --since 2024-01 \
  --until 2025-01 \
  --per-slice 1000 \
  --safe \
  --dedupe \
  --use-watermark \
  --resume \
  --progress-file tier2_shard2_progress.json \
  --max-retries 3 \
  2>&1 | tee logs/tier2_shard2_v2_$(date +%Y%m%d_%H%M%S).log

echo ""
echo "=========================================="
echo "✅ 分片2/3 抓取完成！"
echo "=========================================="

