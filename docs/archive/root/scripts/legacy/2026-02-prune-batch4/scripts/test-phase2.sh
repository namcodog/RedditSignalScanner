#!/bin/bash
# Phase 2 测试脚本
# 用法: bash scripts/test-phase2.sh

set -e

cd "$(dirname "$0")/.."

echo "=========================================="
echo "🧪 Phase 2 测试"
echo "=========================================="
echo ""

echo "📍 步骤 1: 运行 AdaptiveCrawler 单元测试"
cd backend
PYTHONPATH=. python -m pytest tests/services/test_adaptive_crawler.py -v --tb=short
echo "✅ AdaptiveCrawler 测试通过"
echo ""

echo "📍 步骤 2: 运行 TieredScheduler 集成测试"
PYTHONPATH=. python -m pytest tests/services/test_tiered_scheduler.py -v --tb=short
echo "✅ TieredScheduler 测试通过"
echo ""

echo "📍 步骤 3: 运行 RecrawlScheduler 测试"
PYTHONPATH=. python -m pytest tests/services/test_recrawl_scheduler.py -v --tb=short
echo "✅ RecrawlScheduler 测试通过"
echo ""

echo "=========================================="
echo "🎉 Phase 2 所有测试通过！"
echo "=========================================="

