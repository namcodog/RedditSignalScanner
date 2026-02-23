#!/bin/bash
# 一键启动所有3个分片的抓取任务
# 使用tmux创建3个窗口并发执行

set -e

echo "=========================================="
echo "🚀 次高价值社区12个月数据抓取"
echo "=========================================="
echo "📋 社区数量：15个（分3片，每片5个）"
echo "📅 时间范围：2024-01 ~ 2025-01"
echo "📊 数据类型：帖子 + 评论"
echo "=========================================="

# 检查tmux是否安装
if ! command -v tmux &> /dev/null; then
    echo "❌ 错误：tmux未安装"
    echo "请先安装tmux："
    echo "  macOS: brew install tmux"
    echo "  Ubuntu: sudo apt-get install tmux"
    exit 1
fi

# 检查Redis是否运行
if ! redis-cli ping &> /dev/null; then
    echo "⚠️ Redis未运行，正在启动..."
    make dev-redis &
    sleep 3
fi

# 创建日志目录
mkdir -p logs

# 创建tmux会话
SESSION_NAME="tier2_crawl"

# 如果会话已存在，先删除
tmux kill-session -t $SESSION_NAME 2>/dev/null || true

# 创建新会话
tmux new-session -d -s $SESSION_NAME -n "shard1"

# 窗口1：分片1
tmux send-keys -t $SESSION_NAME:0 "cd /Users/hujia/Desktop/RedditSignalScanner" C-m
tmux send-keys -t $SESSION_NAME:0 "./run_tier2_shard1.sh" C-m

# 窗口2：分片2
tmux new-window -t $SESSION_NAME -n "shard2"
tmux send-keys -t $SESSION_NAME:1 "cd /Users/hujia/Desktop/RedditSignalScanner" C-m
tmux send-keys -t $SESSION_NAME:1 "./run_tier2_shard2.sh" C-m

# 窗口3：分片3
tmux new-window -t $SESSION_NAME -n "shard3"
tmux send-keys -t $SESSION_NAME:2 "cd /Users/hujia/Desktop/RedditSignalScanner" C-m
tmux send-keys -t $SESSION_NAME:2 "./run_tier2_shard3.sh" C-m

# 窗口4：监控
tmux new-window -t $SESSION_NAME -n "monitor"
tmux send-keys -t $SESSION_NAME:3 "cd /Users/hujia/Desktop/RedditSignalScanner" C-m
tmux send-keys -t $SESSION_NAME:3 "watch -n 30 'source backend/.env && psql \"\${DATABASE_URL//+asyncpg/}\" -c \"SELECT cp.name, COUNT(DISTINCT pr.id) as posts, COUNT(DISTINCT c.id) as comments FROM community_pool cp LEFT JOIN posts_raw pr ON pr.subreddit = REPLACE(cp.name, '\"'\"'r/'\"'\"', '\"'\"''\"'\"') LEFT JOIN comments c ON c.source_post_id = pr.source_post_id WHERE cp.tier = '\"'\"'medium'\"'\"' AND cp.is_active = true GROUP BY cp.name ORDER BY posts DESC;\"'" C-m

echo ""
echo "=========================================="
echo "✅ 已启动3个分片的抓取任务！"
echo "=========================================="
echo ""
echo "📺 查看抓取进度："
echo "  tmux attach -t $SESSION_NAME"
echo ""
echo "⌨️ tmux快捷键："
echo "  Ctrl+B 然后按 0/1/2/3  - 切换窗口"
echo "  Ctrl+B 然后按 d        - 分离会话（后台运行）"
echo "  Ctrl+B 然后按 [        - 滚动查看历史"
echo ""
echo "📊 查看日志文件："
echo "  tail -f logs/tier2_shard1_*.log"
echo "  tail -f logs/tier2_shard2_*.log"
echo "  tail -f logs/tier2_shard3_*.log"
echo ""
echo "=========================================="

# 自动附加到tmux会话
tmux attach -t $SESSION_NAME

