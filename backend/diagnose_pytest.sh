#!/bin/bash
# pytest 诊断脚本
# 用于诊断 pytest 卡住问题

set -e

echo "========================================="
echo "pytest 诊断脚本"
echo "========================================="
echo ""

# 1. 检查 Python 版本
echo "1. Python 版本:"
python --version
echo ""

# 2. 检查 pytest 版本
echo "2. pytest 版本:"
python -m pytest --version
echo ""

# 3. 检查已安装的 pytest 插件
echo "3. pytest 插件:"
pip list | grep -E "(pytest|anyio)"
echo ""

# 4. 检查是否有 pytest 进程在运行
echo "4. 检查 pytest 进程:"
ps aux | grep pytest | grep -v grep || echo "没有 pytest 进程在运行"
echo ""

# 5. 清理缓存
echo "5. 清理 pytest 缓存:"
rm -rf .pytest_cache __pycache__ tests/__pycache__ tests/api/__pycache__
echo "缓存已清理"
echo ""

# 6. 测试最简单的 pytest 命令
echo "6. 测试 pytest --collect-only:"
timeout 10 python -m pytest test_standalone.py --collect-only || echo "TIMEOUT 或失败: $?"
echo ""

# 7. 测试运行最简单的测试
echo "7. 测试运行 test_standalone.py (10秒超时):"
timeout 10 python -m pytest test_standalone.py -vv || echo "TIMEOUT 或失败: $?"
echo ""

# 8. 建议的修复方案
echo "========================================="
echo "建议的修复方案:"
echo "========================================="
echo ""
echo "方案 1: 移除 anyio 插件"
echo "  pip uninstall anyio -y"
echo "  pytest test_standalone.py -vv"
echo ""
echo "方案 2: 降级 pytest-asyncio"
echo "  pip uninstall pytest-asyncio -y"
echo "  pip install pytest-asyncio==0.21.0"
echo "  pytest test_standalone.py -vv"
echo ""
echo "方案 3: 使用 pytest-timeout 获取堆栈跟踪"
echo "  pip install pytest-timeout"
echo "  pytest test_standalone.py -vv --timeout=5 --timeout-method=thread"
echo ""
echo "方案 4: 完全重建测试环境"
echo "  pip uninstall pytest pytest-asyncio anyio -y"
echo "  pip install pytest==8.4.2 pytest-asyncio==0.24.0"
echo "  pytest test_standalone.py -vv"
echo ""

