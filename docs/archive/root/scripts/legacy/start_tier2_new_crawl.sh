#!/bin/bash
# 次高价值社区抓取 - 后台并发执行（使用/new端点）

set -e

echo "=========================================="
echo "🚀 次高价值社区抓取（/new端点，后台模式）"
echo "=========================================="
echo "📋 社区数量：15个（分3片，每片5个）"
echo "📅 时间过滤：month（最近30天）"
echo "📊 每社区最大：1000帖子"
echo "✅ 执行模式：后台并发（nohup）"
echo "✅ 使用/new端点（更可靠）"
echo "=========================================="

# 创建日志目录
mkdir -p logs

# 启动分片1
echo "🚀 启动分片1/3..."
nohup bash -c "export PYTHONPATH=/Users/hujia/Desktop/RedditSignalScanner/backend:\$PYTHONPATH && python backend/scripts/crawl_posts_new_endpoint.py \
  --csv 次高价值社区_15社区_shard1_of_3.csv \
  --time-filter month \
  --max-posts 1000 \
  --safe \
  --use-watermark \
  --resume \
  --progress-file tier2_new_shard1_progress.json \
  --max-retries 3" > logs/tier2_new_shard1_$(date +%Y%m%d_%H%M%S).log 2>&1 &
SHARD1_PID=$!
echo "   ✅ 分片1 PID: $SHARD1_PID"

# 启动分片2
echo "🚀 启动分片2/3..."
nohup bash -c "export PYTHONPATH=/Users/hujia/Desktop/RedditSignalScanner/backend:\$PYTHONPATH && python backend/scripts/crawl_posts_new_endpoint.py \
  --csv 次高价值社区_15社区_shard2_of_3.csv \
  --time-filter month \
  --max-posts 1000 \
  --safe \
  --use-watermark \
  --resume \
  --progress-file tier2_new_shard2_progress.json \
  --max-retries 3" > logs/tier2_new_shard2_$(date +%Y%m%d_%H%M%S).log 2>&1 &
SHARD2_PID=$!
echo "   ✅ 分片2 PID: $SHARD2_PID"

# 启动分片3
echo "🚀 启动分片3/3..."
nohup bash -c "export PYTHONPATH=/Users/hujia/Desktop/RedditSignalScanner/backend:\$PYTHONPATH && python backend/scripts/crawl_posts_new_endpoint.py \
  --csv 次高价值社区_15社区_shard3_of_3.csv \
  --time-filter month \
  --max-posts 1000 \
  --safe \
  --use-watermark \
  --resume \
  --progress-file tier2_new_shard3_progress.json \
  --max-retries 3" > logs/tier2_new_shard3_$(date +%Y%m%d_%H%M%S).log 2>&1 &
SHARD3_PID=$!
echo "   ✅ 分片3 PID: $SHARD3_PID"

# 保存PID到文件
echo "$SHARD1_PID" > tier2_new_shard1.pid
echo "$SHARD2_PID" > tier2_new_shard2.pid
echo "$SHARD3_PID" > tier2_new_shard3.pid

echo ""
echo "=========================================="
echo "✅ 所有分片已启动！"
echo "=========================================="
echo "📊 进程ID："
echo "   分片1: $SHARD1_PID"
echo "   分片2: $SHARD2_PID"
echo "   分片3: $SHARD3_PID"
echo ""
echo "📋 监控命令："
echo "   查看进度: cat tier2_new_shard*_progress.json"
echo "   查看日志: tail -f logs/tier2_new_shard1_*.log"
echo "   检查进程: ps aux | grep crawl_posts_new_endpoint"
echo "   停止抓取: kill \$(cat tier2_new_shard*.pid)"
echo "=========================================="

