#!/bin/bash
# Day 14 快速测试脚本 - 跳过环境检查，直接运行测试

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "=========================================="
echo "Day 14 快速测试"
echo "=========================================="
echo ""

# 切换到后端目录
cd "$BACKEND_DIR"

# 设置测试环境
export APP_ENV=test
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/reddit_scanner
export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"

echo "1️⃣ 运行最小化测试（诊断）"
echo "----------------------------------------"

if pytest tests/e2e/test_minimal_perf.py -v --tb=short; then
    echo "✅ 最小化测试通过"
else
    echo "❌ 最小化测试失败"
    exit 1
fi

echo ""
echo "2️⃣ 运行完整用户旅程测试"
echo "----------------------------------------"

if pytest tests/e2e/test_complete_user_journey.py -v --tb=short; then
    echo "✅ 完整用户旅程测试通过"
else
    echo "❌ 完整用户旅程测试失败"
    exit 1
fi

echo ""
echo "3️⃣ 运行多租户隔离测试"
echo "----------------------------------------"

if pytest tests/e2e/test_multi_tenant_isolation.py -v --tb=short; then
    echo "✅ 多租户隔离测试通过"
else
    echo "❌ 多租户隔离测试失败"
    exit 1
fi

echo ""
echo "4️⃣ 运行故障注入测试"
echo "----------------------------------------"

if pytest tests/e2e/test_fault_injection.py -v --tb=short; then
    echo "✅ 故障注入测试通过"
else
    echo "❌ 故障注入测试失败"
    exit 1
fi

echo ""
echo "5️⃣ 运行性能压力测试"
echo "----------------------------------------"
echo "注意：此测试会创建 60 个任务，可能需要 2-5 分钟"
echo ""

if pytest tests/e2e/test_performance_stress.py -v --tb=short; then
    echo "✅ 性能压力测试通过"
else
    echo "❌ 性能压力测试失败"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Day 14 所有测试通过！"
echo "=========================================="

