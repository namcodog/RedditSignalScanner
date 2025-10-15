#!/bin/bash
# Day 14 诊断脚本 - 检查测试环境

set -e

echo "=========================================="
echo "Day 14 测试环境诊断"
echo "=========================================="
echo ""

echo "1. 检查 Redis 连接..."
if redis-cli ping > /dev/null 2>&1; then
    echo "   ✅ Redis 可用"
else
    echo "   ❌ Redis 不可用"
    echo "   请运行: docker compose up -d redis"
    exit 1
fi

echo ""
echo "2. 检查 PostgreSQL 连接..."
if psql -U postgres -h localhost -d reddit_scanner -c "SELECT 1" > /dev/null 2>&1; then
    echo "   ✅ PostgreSQL 可用"
else
    echo "   ❌ PostgreSQL 不可用"
    echo "   请运行: docker compose up -d postgres"
    exit 1
fi

echo ""
echo "3. 检查数据库表..."
TABLE_COUNT=$(psql -U postgres -h localhost -d reddit_scanner -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('users', 'tasks', 'analyses', 'reports')" 2>/dev/null || echo "0")
if [ "$TABLE_COUNT" -eq 4 ]; then
    echo "   ✅ 核心表存在 (4/4)"
else
    echo "   ⚠️  核心表不完整 ($TABLE_COUNT/4)"
    echo "   请运行: alembic upgrade head"
fi

echo ""
echo "4. 检查 Python 环境..."
python -c "import pytest; print('   ✅ pytest 版本:', pytest.__version__)"
python -c "import httpx; print('   ✅ httpx 已安装')"
python -c "import sqlalchemy; print('   ✅ sqlalchemy 已安装')"

echo ""
echo "5. 检查测试文件..."
if [ -f "tests/e2e/test_performance_stress.py" ]; then
    echo "   ✅ 性能测试文件存在"
else
    echo "   ❌ 性能测试文件不存在"
    exit 1
fi

echo ""
echo "=========================================="
echo "环境检查完成！可以运行测试。"
echo "=========================================="
echo ""
echo "运行测试命令:"
echo "  export APP_ENV=test"
echo "  pytest tests/e2e/test_performance_stress.py -v"

