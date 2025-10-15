#!/bin/bash
# pytest 系统性诊断和修复脚本
# 按照用户建议的步骤逐步排查问题

set -e

echo "========================================="
echo "pytest 系统性诊断和修复流程"
echo "========================================="
echo ""

# 步骤 0: 环境信息收集
echo "步骤 0: 收集环境信息"
echo "-------------------"
echo "Python 版本:"
python --version
echo ""
echo "当前目录:"
pwd
echo ""
echo "已安装的 pytest 相关包:"
pip list | grep -E "(pytest|anyio|celery)" || echo "未找到相关包"
echo ""
echo "环境变量检查:"
echo "PYTHONPATH: ${PYTHONPATH:-未设置}"
echo "PYTEST_ADDOPTS: ${PYTEST_ADDOPTS:-未设置}"
echo ""

# 步骤 1: 清理缓存
echo "步骤 1: 清理 pytest 缓存"
echo "-------------------"
rm -rf .pytest_cache backend/.pytest_cache __pycache__ tests/__pycache__ tests/api/__pycache__
echo "✅ 缓存已清理"
echo ""

# 步骤 2: 测试基础 pytest 功能
echo "步骤 2: 测试 pytest --collect-only (10秒超时)"
echo "-------------------"
timeout 10 python -m pytest test_standalone.py --collect-only 2>&1 || {
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo "❌ TIMEOUT: pytest --collect-only 卡住"
    else
        echo "❌ 失败，退出码: $EXIT_CODE"
    fi
}
echo ""

# 步骤 3: 停用 pytest-asyncio
echo "步骤 3: 停用 pytest-asyncio 插件"
echo "-------------------"
echo "测试: pytest -p no:asyncio (10秒超时)"
timeout 10 python -m pytest test_standalone.py -p no:asyncio -vv 2>&1 || {
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo "❌ TIMEOUT: 停用 asyncio 插件后仍卡住"
    else
        echo "退出码: $EXIT_CODE"
    fi
}
echo ""

# 步骤 4: 停用所有插件
echo "步骤 4: 停用所有插件"
echo "-------------------"
echo "测试: pytest -p no:asyncio -p no:anyio (10秒超时)"
timeout 10 python -m pytest test_standalone.py -p no:asyncio -p no:anyio -vv 2>&1 || {
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo "❌ TIMEOUT: 停用所有插件后仍卡住"
    else
        echo "退出码: $EXIT_CODE"
    fi
}
echo ""

# 步骤 5: 使用 --trace 模式
echo "步骤 5: 使用 --trace 模式获取调用栈"
echo "-------------------"
echo "注意: 这会进入交互式调试，需要手动输入 'c' 继续或 'q' 退出"
echo "跳过此步骤（需要交互）"
echo ""

# 步骤 6: 使用 --durations=0
echo "步骤 6: 使用 --durations=0 查看耗时"
echo "-------------------"
timeout 10 python -m pytest test_standalone.py -vv --durations=0 2>&1 || {
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo "❌ TIMEOUT: --durations=0 模式下仍卡住"
    else
        echo "退出码: $EXIT_CODE"
    fi
}
echo ""

# 步骤 7: 检查是否有 pytest 进程残留
echo "步骤 7: 检查 pytest 进程"
echo "-------------------"
ps aux | grep pytest | grep -v grep || echo "✅ 没有 pytest 进程在运行"
echo ""

echo "========================================="
echo "诊断完成"
echo "========================================="
echo ""
echo "建议的修复步骤:"
echo ""
echo "1. 如果步骤 3 或 4 成功（停用插件后可运行）:"
echo "   → 问题在于 pytest-asyncio 或 anyio 插件"
echo "   → 执行: pip uninstall pytest-asyncio anyio -y"
echo "   → 重新安装: pip install pytest-asyncio==0.21.0"
echo ""
echo "2. 如果所有步骤都超时:"
echo "   → 问题可能在 pytest 本身或系统环境"
echo "   → 执行: pip uninstall pytest -y && pip install pytest==7.4.0"
echo ""
echo "3. 如果需要获取调用栈:"
echo "   → 手动运行: PYTEST_ADDOPTS='--trace' pytest test_standalone.py -vv"
echo "   → 或: python -m pytest test_standalone.py --pdb"
echo ""

