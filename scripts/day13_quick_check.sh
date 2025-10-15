#!/bin/bash
# Day 13 快速验收检查脚本

echo "=========================================="
echo "🔍 Day 13 快速验收检查"
echo "=========================================="
echo ""

echo "1️⃣  检查 JSON 文件中的社区数量..."
JSON_COUNT=$(cat backend/config/seed_communities.json | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('seed_communities', [])))" 2>/dev/null || echo "0")
echo "   JSON 文件社区数: $JSON_COUNT"
echo ""

echo "2️⃣  检查数据库中的社区数量..."
cd backend
DB_COUNT=$(/opt/homebrew/bin/python3.11 -c "
import asyncio
from app.db.session import get_session
from app.models.community_pool import CommunityPool
from sqlalchemy import select, func

async def check():
    async for session in get_session():
        count = await session.execute(select(func.count()).select_from(CommunityPool))
        print(count.scalar())
        break

asyncio.run(check())
" 2>/dev/null || echo "0")
echo "   数据库社区数: $DB_COUNT"
cd ..
echo ""

echo "3️⃣  检查 Excel 文件..."
if [ -f "社区筛选.xlsx" ]; then
    echo "   ✅ Excel 文件存在"
    EXCEL_COUNT=$(python3 -c "import pandas as pd; df = pd.read_excel('社区筛选.xlsx'); print(len(df))" 2>/dev/null || echo "未知")
    echo "   Excel 文件行数: $EXCEL_COUNT"
else
    echo "   ❌ Excel 文件不存在"
fi
echo ""

echo "4️⃣  检查数据库迁移状态..."
cd backend
MIGRATION_STATUS=$(alembic current 2>/dev/null | tail -1 || echo "未知")
echo "   当前迁移版本: $MIGRATION_STATUS"
cd ..
echo ""

echo "=========================================="
echo "📊 验收结果总结"
echo "=========================================="
echo ""
echo "JSON 文件社区数:    $JSON_COUNT"
echo "数据库社区数:      $DB_COUNT"
echo "Excel 文件行数:    $EXCEL_COUNT"
echo ""

if [ "$JSON_COUNT" -ge 50 ] && [ "$DB_COUNT" -ge 50 ]; then
    echo "✅ Day 13 验收通过！"
elif [ "$JSON_COUNT" -eq 5 ] && [ "$DB_COUNT" -eq 5 ]; then
    echo "⚠️  数据量不足（需要 50-100 个社区）"
    echo ""
    echo "建议执行："
    echo "  1. 补充 Excel 数据到 50-100 个社区"
    echo "  2. 运行: make day13-seed-all"
else
    echo "⚠️  数据不一致，需要检查"
fi
echo ""

