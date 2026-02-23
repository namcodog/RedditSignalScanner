#!/bin/bash
# 次高价值社区12个月数据抓取 - 后台并发执行版本
# 不依赖tmux，使用nohup后台执行

set -e

echo "=========================================="
echo "🚀 次高价值社区12个月数据抓取（后台模式）"
echo "=========================================="
echo "📋 社区数量：15个（分3片，每片5个）"
echo "📅 时间范围：2024-01 ~ 2025-01"
echo "📊 数据类型：帖子 + 评论"
echo "✅ 执行模式：后台并发（nohup）"
echo "=========================================="

# 创建日志目录
mkdir -p logs

# 启动分片1
echo "🚀 启动分片1/3..."
nohup bash -c "export PYTHONPATH=/Users/hujia/Desktop/RedditSignalScanner/backend:\$PYTHONPATH && python backend/scripts/crawl_posts_from_csv_v2.py \
  --csv 次高价值社区_15社区_shard1_of_3.csv \
  --since 2024-01 \
  --until 2025-01 \
  --per-slice 1000 \
  --safe \
  --dedupe \
  --use-watermark \
  --resume \
  --progress-file tier2_shard1_progress.json \
  --max-retries 3" > logs/tier2_shard1_$(date +%Y%m%d_%H%M%S).log 2>&1 &
SHARD1_PID=$!
echo "   ✅ 分片1 PID: $SHARD1_PID"

# 启动分片2
echo "🚀 启动分片2/3..."
nohup bash -c "export PYTHONPATH=/Users/hujia/Desktop/RedditSignalScanner/backend:\$PYTHONPATH && python backend/scripts/crawl_posts_from_csv_v2.py \
  --csv 次高价值社区_15社区_shard2_of_3.csv \
  --since 2024-01 \
  --until 2025-01 \
  --per-slice 1000 \
  --safe \
  --dedupe \
  --use-watermark \
  --resume \
  --progress-file tier2_shard2_progress.json \
  --max-retries 3" > logs/tier2_shard2_$(date +%Y%m%d_%H%M%S).log 2>&1 &
SHARD2_PID=$!
echo "   ✅ 分片2 PID: $SHARD2_PID"

# 启动分片3
echo "🚀 启动分片3/3..."
nohup bash -c "export PYTHONPATH=/Users/hujia/Desktop/RedditSignalScanner/backend:\$PYTHONPATH && python backend/scripts/crawl_posts_from_csv_v2.py \
  --csv 次高价值社区_15社区_shard3_of_3.csv \
  --since 2024-01 \
  --until 2025-01 \
  --per-slice 1000 \
  --safe \
  --dedupe \
  --use-watermark \
  --resume \
  --progress-file tier2_shard3_progress.json \
  --max-retries 3" > logs/tier2_shard3_$(date +%Y%m%d_%H%M%S).log 2>&1 &
SHARD3_PID=$!
echo "   ✅ 分片3 PID: $SHARD3_PID"

# 保存PID到文件
echo "$SHARD1_PID" > tier2_shard1.pid
echo "$SHARD2_PID" > tier2_shard2.pid
echo "$SHARD3_PID" > tier2_shard3.pid

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
echo "   查看进度: cat tier2_shard*_progress.json"
echo "   查看日志: tail -f logs/tier2_shard1_*.log"
echo "   检查进程: ps aux | grep crawl_posts_from_csv_v2"
echo "   停止抓取: kill \$(cat tier2_shard*.pid)"
echo "=========================================="

