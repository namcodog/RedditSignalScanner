#!/bin/bash
# Backend 测试运行脚本
# 自动清理残留进程和缓存，然后运行测试

set -e

echo "========================================="
echo "Backend 测试运行脚本"
echo "========================================="
echo ""

# 步骤 1: 清理残留 pytest 进程
echo "步骤 1: 清理残留 pytest 进程"
echo "-------------------"
PYTEST_PIDS=$(ps aux | grep pytest | grep -v grep | awk '{print $2}' || true)
if [ -n "$PYTEST_PIDS" ]; then
    echo "发现残留 pytest 进程: $PYTEST_PIDS"
    pkill -9 -f pytest || true
    sleep 1
    echo "✅ 已清理"
else
    echo "✅ 没有残留进程"
fi
echo ""

# 步骤 2: 清理 pytest 缓存
echo "步骤 2: 清理 pytest 缓存"
echo "-------------------"
rm -rf .pytest_cache __pycache__ tests/__pycache__ tests/api/__pycache__ tests/integration/__pycache__
echo "✅ 缓存已清理"
echo ""

# 步骤 3: 运行测试
echo "步骤 3: 运行测试"
echo "-------------------"
if [ $# -eq 0 ]; then
    # 没有参数，运行所有测试
    echo "运行所有测试..."
    python -m pytest tests/ -v --maxfail=5
else
    # 有参数，运行指定测试
    echo "运行指定测试: $@"
    python -m pytest "$@"
fi

echo ""
echo "========================================="
echo "测试完成"
echo "========================================="

