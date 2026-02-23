#!/bin/bash
# T2社区评论回填脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONPATH="${SCRIPT_DIR}/backend:$PYTHONPATH"

echo "=========================================="
echo "🔧 T2社区评论回填"
echo "=========================================="
echo "📋 社区数量: 15个次高价值社区"
echo "📅 时间范围: 全部帖子"
echo "📊 批次大小: 100帖子/批"
echo "💾 提交间隔: 每5个帖子"
echo "=========================================="
echo ""

python3 -u backend/scripts/backfill_comments_for_posts.py \
  --csv "次高价值社区池_基于165社区.csv" \
  --since-days -1 \
  --page-size 100 \
  --commit-interval 5 \
  --skip-labeling \
  --mode topn \
  --limit-per-post 200 \
  --skip-existing-check

echo ""
echo "✅ T2社区评论回填完成！"
