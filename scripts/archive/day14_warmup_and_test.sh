#!/bin/bash
# Day 14 完整验收流程：预热 + 测试

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "=========================================="
echo "Day 14 完整验收流程"
echo "=========================================="
echo ""
echo "流程："
echo "  1️⃣  缓存预热（爬取 100 个种子社区）"
echo "  2️⃣  运行端到端测试（使用真实 Reddit API + 缓存）"
echo ""

# 切换到后端目录
cd "$BACKEND_DIR"

# 设置环境变量
export APP_ENV=test
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/reddit_signal_scanner
export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"

echo "=========================================="
echo "步骤 1：缓存预热"
echo "=========================================="
echo ""
echo "⚠️  注意：此步骤需要 10-20 分钟"
echo "⚠️  将调用真实 Reddit API（约 100 次调用）"
echo ""

# 运行预热脚本（自动确认）
echo "y" | python scripts/warmup_cache_now.py

echo ""
echo "=========================================="
echo "步骤 2：验证缓存"
echo "=========================================="
echo ""

# 检查缓存数据
CACHE_COUNT=$(psql -U postgres -h localhost -d reddit_scanner -t -c "SELECT COUNT(*) FROM community_cache;" | tr -d ' ')
echo "✅ 缓存记录数：$CACHE_COUNT"

if [ "$CACHE_COUNT" -lt 50 ]; then
    echo "❌ 缓存数据不足（< 50），预热可能失败"
    exit 1
fi

echo ""
echo "=========================================="
echo "步骤 3：运行端到端测试"
echo "=========================================="
echo ""

# 移除 mock，使用真实 API + 缓存
echo "📝 配置测试环境：使用真实 Reddit API + 缓存"
export USE_REAL_REDDIT_API=1

# 运行测试
bash "$PROJECT_ROOT/scripts/day14_quick_test.sh"

echo ""
echo "=========================================="
echo "✅ Day 14 验收完成！"
echo "=========================================="
