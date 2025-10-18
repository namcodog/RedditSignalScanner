#!/bin/bash
#
# P0/P1 修复验收脚本
#
# 功能: 自动执行所有验收检查
# 使用方法: ./scripts/verify_p0_p1_fixes.sh

set -e

echo "=========================================="
echo "P0/P1 修复验收脚本"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 验收结果统计
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

check_result() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASSED${NC}: $2"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "${RED}❌ FAILED${NC}: $2"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

echo "=========================================="
echo "P0-1: posts_hot 清理任务验收"
echo "=========================================="
echo ""

# 验收1: 清理任务存在
echo "验收1: 检查清理任务是否存在..."
cd backend
python3 << 'EOF'
from app.core.celery_app import celery_app
schedule = celery_app.conf.beat_schedule
assert "cleanup-expired-posts-hot" in schedule, "清理任务不存在"
task = schedule["cleanup-expired-posts-hot"]
assert task["task"] == "tasks.maintenance.cleanup_expired_posts_hot", "任务名称错误"
print("✅ 清理任务存在")
EOF
check_result $? "清理任务存在于 Beat schedule"

# 验收2: 运行测试用例
echo ""
echo "验收2: 运行清理任务测试用例..."
pytest tests/tasks/test_cleanup_posts_hot.py -v --tb=short
check_result $? "清理任务测试用例通过"

# 验收3: 检查过期数据
echo ""
echo "验收3: 检查 posts_hot 过期数据..."
cd ..
EXPIRED_COUNT=$(psql -U postgres -d reddit_scanner -t -c "SELECT COUNT(*) FROM posts_hot WHERE expires_at < NOW();")
echo "   过期数据: $EXPIRED_COUNT 条"
if [ "$EXPIRED_COUNT" -lt 100 ]; then
    check_result 0 "posts_hot 过期数据 <100 条"
else
    check_result 1 "posts_hot 过期数据过多: $EXPIRED_COUNT 条"
fi

echo ""
echo "=========================================="
echo "P0-2: Redis maxmemory 配置验收"
echo "=========================================="
echo ""

# 验收4: 检查 maxmemory 配置
echo "验收4: 检查 Redis maxmemory 配置..."
MAXMEMORY=$(redis-cli CONFIG GET maxmemory | tail -1)
if [ "$MAXMEMORY" = "2147483648" ]; then
    check_result 0 "Redis maxmemory 配置正确 (2GB)"
else
    check_result 1 "Redis maxmemory 配置错误: $MAXMEMORY"
fi

# 验收5: 检查驱逐策略
echo ""
echo "验收5: 检查 Redis maxmemory-policy..."
POLICY=$(redis-cli CONFIG GET maxmemory-policy | tail -1)
if [ "$POLICY" = "allkeys-lru" ]; then
    check_result 0 "Redis maxmemory-policy 配置正确 (allkeys-lru)"
else
    check_result 1 "Redis maxmemory-policy 配置错误: $POLICY"
fi

# 验收6: 检查配置持久化
echo ""
echo "验收6: 检查 Redis 配置持久化..."
if grep -q "^maxmemory 2gb" /opt/homebrew/etc/redis.conf; then
    check_result 0 "Redis 配置已持久化到 redis.conf"
else
    check_result 1 "Redis 配置未持久化"
fi

echo ""
echo "=========================================="
echo "P1-1: 去重逻辑修复验收"
echo "=========================================="
echo ""

# 验收7: 运行去重测试用例
echo "验收7: 运行去重逻辑测试用例..."
cd backend
pytest tests/services/test_incremental_crawler_dedup.py -v --tb=short
check_result $? "去重逻辑测试用例通过"

# 验收8: 检查数据库去重效果
echo ""
echo "验收8: 检查数据库去重效果..."
cd ..
DUPLICATE_COUNT=$(psql -U postgres -d reddit_scanner -t -c "
SELECT COUNT(*) FROM (
    SELECT source, source_post_id, version, COUNT(*) 
    FROM posts_raw 
    GROUP BY source, source_post_id, version 
    HAVING COUNT(*) > 1
) AS duplicates;
")
if [ "$DUPLICATE_COUNT" -eq 0 ]; then
    check_result 0 "数据库无重复记录"
else
    check_result 1 "数据库存在重复记录: $DUPLICATE_COUNT 条"
fi

echo ""
echo "=========================================="
echo "P1-2: 数据库备份机制验收"
echo "=========================================="
echo ""

# 验收9: 检查备份脚本
echo "验收9: 检查备份脚本是否存在且可执行..."
if [ -x scripts/backup_database.sh ]; then
    check_result 0 "备份脚本存在且可执行"
else
    check_result 1 "备份脚本不存在或无执行权限"
fi

# 验收10: 执行备份
echo ""
echo "验收10: 执行数据库备份..."
./scripts/backup_database.sh
if [ $? -eq 0 ]; then
    check_result 0 "备份执行成功"
else
    check_result 1 "备份执行失败"
fi

# 验收11: 检查备份文件
echo ""
echo "验收11: 检查备份文件..."
BACKUP_FILE=$(ls -t backup/reddit_scanner_*.sql.gz 2>/dev/null | head -1)
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "   备份文件: $BACKUP_FILE"
    echo "   文件大小: $BACKUP_SIZE"
    check_result 0 "备份文件生成成功"
else
    check_result 1 "备份文件不存在"
fi

# 验收12: 检查 cron 配置
echo ""
echo "验收12: 检查 cron 任务配置..."
if crontab -l 2>/dev/null | grep -q "backup_database.sh"; then
    check_result 0 "Cron 任务已配置"
else
    echo -e "${YELLOW}⚠️  WARNING${NC}: Cron 任务未配置（需手动配置）"
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
fi

echo ""
echo "=========================================="
echo "验收结果汇总"
echo "=========================================="
echo ""
echo "总检查项: $TOTAL_CHECKS"
echo -e "${GREEN}通过: $PASSED_CHECKS${NC}"
echo -e "${RED}失败: $FAILED_CHECKS${NC}"
echo ""

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}🎉 所有验收项通过！${NC}"
    exit 0
else
    echo -e "${RED}❌ 存在 $FAILED_CHECKS 项验收失败，请检查修复${NC}"
    exit 1
fi

