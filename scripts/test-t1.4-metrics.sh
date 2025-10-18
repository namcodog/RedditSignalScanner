#!/bin/bash
# T1.4 测试脚本 - IncrementalCrawler 埋点测试

set -e

cd "$(dirname "$0")/.."

echo "=========================================="
echo "🧪 T1.4: IncrementalCrawler 埋点测试"
echo "=========================================="
echo ""

cd backend
PYTHONPATH=. python -m pytest tests/services/test_incremental_crawler_metrics.py -v --tb=short

echo ""
echo "=========================================="
echo "✅ T1.4 测试完成"
echo "=========================================="

