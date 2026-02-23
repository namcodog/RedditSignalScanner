#!/usr/bin/env bash
# Spec 013 日常运维巡检脚本
# 用法: ./scripts/daily_ops_check.sh [morning|noon|evening]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPORT_DIR="${PROJECT_ROOT}/reports/phase-log"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
CHECK_TYPE="${1:-full}"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "📋 Spec 013 日常运维巡检"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "类型: ${CHECK_TYPE}"
echo "=========================================="
echo ""

# 1. 检查基础服务
echo "1️⃣  检查基础服务..."
echo ""

# Redis
if ps aux | grep -E "redis-server" | grep -v grep > /dev/null; then
    echo -e "${GREEN}✅ Redis 运行中${NC}"
else
    echo -e "${RED}❌ Redis 未运行${NC}"
fi

# Celery Worker
WORKER_COUNT=$(ps aux | grep "celery.*worker" | grep -v grep | wc -l | tr -d ' ')
if [ "$WORKER_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✅ Celery Worker 运行中 (${WORKER_COUNT} 个进程)${NC}"
else
    echo -e "${RED}❌ Celery Worker 未运行${NC}"
fi

# Celery Beat
if ps aux | grep "celery.*beat" | grep -v grep > /dev/null; then
    echo -e "${GREEN}✅ Celery Beat 运行中${NC}"
else
    echo -e "${RED}❌ Celery Beat 未运行${NC}"
fi

echo ""

# 2. 数据增长检查
echo "2️⃣  数据增长检查（最近7天）..."
echo ""
cd "${PROJECT_ROOT}"
make posts-growth-7d 2>/dev/null | grep -A 10 "day,count" || echo "无法获取数据"
echo ""

# 3. Redis 任务痕迹
echo "3️⃣  Redis 任务痕迹..."
echo ""
make celery-meta-count 2>/dev/null | grep -E "db[0-9]:" || echo "无法获取数据"
echo ""

# 4. 社区池统计（仅 noon/evening）
if [ "$CHECK_TYPE" = "noon" ] || [ "$CHECK_TYPE" = "evening" ] || [ "$CHECK_TYPE" = "full" ]; then
    echo "4️⃣  社区池统计..."
    echo ""
    make pool-stats 2>/dev/null | grep -A 10 "Community Pool Stats" || echo "无法获取数据"
    echo ""
fi

# 5. 完整快照（仅 noon）
if [ "$CHECK_TYPE" = "noon" ] || [ "$CHECK_TYPE" = "full" ]; then
    echo "5️⃣  生成完整快照..."
    echo ""
    SNAPSHOT_FILE="${REPORT_DIR}/daily-check-${TIMESTAMP}.txt"
    make pipeline-health > "${SNAPSHOT_FILE}" 2>&1
    echo -e "${GREEN}✅ 快照已保存: ${SNAPSHOT_FILE}${NC}"
    echo ""
fi

# 6. 健康评分
echo "=========================================="
echo "📊 健康评分"
echo "=========================================="
echo ""

# 计算日增平均值（简化版）
GROWTH_AVG=$(make posts-growth-7d 2>/dev/null | grep -E "^2025" | awk -F',' '{sum+=$2; count++} END {if(count>0) print int(sum/count); else print 0}')
echo "日均新增帖子: ${GROWTH_AVG} 条"

if [ "$GROWTH_AVG" -ge 1000 ]; then
    echo -e "${GREEN}✅ 达标（目标 ≥1,000）${NC}"
elif [ "$GROWTH_AVG" -ge 500 ]; then
    echo -e "${YELLOW}⚠️  偏低（目标 ≥1,000）${NC}"
else
    echo -e "${RED}❌ 严重偏低（目标 ≥1,000）${NC}"
    echo ""
    echo "🔧 建议执行提拉策略:"
    echo "   make discover-crossborder LIMIT=10000"
    echo "   make import-crossborder-pool"
    echo "   make pool-stats"
fi

echo ""
echo "=========================================="
echo "✅ 巡检完成"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
