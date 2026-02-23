#!/bin/bash
set -e

# 数据库修复效果验证脚本
# 用途：验证 production_db_fix_manual.md 中的所有修复是否生效

echo "=========================================="
echo "  数据库修复效果验证工具"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 从 .env 读取配置
if [ -f "backend/.env" ]; then
    source backend/.env
else
    echo -e "${RED}✗ 未找到 backend/.env 文件${NC}"
    exit 1
fi

# 解析 DATABASE_URL
DB_URL_CLEAN=$(echo $DATABASE_URL | sed 's/+asyncpg//')
DB_USER=$(echo $DB_URL_CLEAN | sed -n 's|.*://\([^:]*\):.*|\1|p')
DB_PASS=$(echo $DB_URL_CLEAN | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
DB_HOST=$(echo $DB_URL_CLEAN | sed -n 's|.*@\([^:]*\):.*|\1|p')
DB_PORT=$(echo $DB_URL_CLEAN | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
DB_NAME=$(echo $DB_URL_CLEAN | sed -n 's|.*/\([^?]*\).*|\1|p')

export PGPASSWORD=$DB_PASS

echo "验证数据库: $DB_NAME @ $DB_HOST:$DB_PORT"
echo ""

# 验证计数器
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# 验证函数
check_test() {
    local test_name="$1"
    local sql_query="$2"
    local expected="$3"
    local description="$4"

    echo "检查: $test_name"
    result=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "$sql_query" 2>&1 | xargs)

    if [ "$result" = "$expected" ]; then
        echo -e "${GREEN}✓ PASS${NC} - $description"
        ((PASS_COUNT++))
    else
        echo -e "${RED}✗ FAIL${NC} - $description"
        echo "  预期: $expected"
        echo "  实际: $result"
        ((FAIL_COUNT++))
    fi
    echo ""
}

check_warning() {
    local test_name="$1"
    local sql_query="$2"
    local threshold="$3"
    local description="$4"

    echo "检查: $test_name"
    result=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "$sql_query" 2>&1 | xargs)

    if [ "$result" -le "$threshold" ]; then
        echo -e "${GREEN}✓ PASS${NC} - $description"
        ((PASS_COUNT++))
    else
        echo -e "${YELLOW}⚠ WARNING${NC} - $description"
        echo "  阈值: <=$threshold"
        echo "  实际: $result"
        ((WARN_COUNT++))
    fi
    echo ""
}

echo "=== 1. 评论表修复验证 ==="
echo ""

# 1.1 孤儿评论检查
check_test \
    "孤儿评论" \
    "SELECT count(*) FROM comments WHERE post_id IS NULL;" \
    "0" \
    "所有评论都应关联到帖子"

# 1.2 外键约束存在性
check_test \
    "外键约束" \
    "SELECT count(*) FROM information_schema.table_constraints WHERE constraint_name = 'fk_comments_posts_raw' AND table_name = 'comments';" \
    "1" \
    "comments 表应有 fk_comments_posts_raw 约束"

# 1.3 post_id 非空约束
check_test \
    "post_id 非空" \
    "SELECT is_nullable FROM information_schema.columns WHERE table_name = 'comments' AND column_name = 'post_id';" \
    "NO" \
    "post_id 列应为 NOT NULL"

# 1.4 索引存在性
check_test \
    "post_id 索引" \
    "SELECT count(*) FROM pg_indexes WHERE indexname = 'idx_comments_post_id';" \
    "1" \
    "应有 idx_comments_post_id 索引"

check_test \
    "parent_id 索引" \
    "SELECT count(*) FROM pg_indexes WHERE indexname = 'idx_comments_parent_id';" \
    "1" \
    "应有 idx_comments_parent_id 索引"

echo "=== 2. SCD2 触发器验证 ==="
echo ""

# 2.1 触发器存在性
check_test \
    "SCD2 触发器" \
    "SELECT count(*) FROM pg_trigger WHERE tgname = 'enforce_scd2_posts_raw';" \
    "1" \
    "应有 enforce_scd2_posts_raw 触发器"

# 2.2 当前版本唯一性
check_test \
    "SCD2 版本唯一" \
    "SELECT count(*) FROM (SELECT source, source_post_id FROM posts_raw GROUP BY source, source_post_id HAVING count(*) FILTER (WHERE is_current) > 1) t;" \
    "0" \
    "每个帖子应只有一个 is_current=true 版本"

# 2.3 valid_to 默认值
check_test \
    "valid_to 默认值" \
    "SELECT column_default FROM information_schema.columns WHERE table_name = 'posts_raw' AND column_name = 'valid_to';" \
    "'9999-12-31 00:00:00+00'::timestamp with time zone" \
    "valid_to 应有远未来默认值"

echo "=== 3. 缓存表约束验证 ==="
echo ""

# 3.1 默认值检查
check_test \
    "empty_hit 默认值" \
    "SELECT column_default FROM information_schema.columns WHERE table_name = 'community_cache' AND column_name = 'empty_hit';" \
    "0" \
    "empty_hit 应默认为 0"

check_test \
    "crawl_quality_score 默认值" \
    "SELECT column_default FROM information_schema.columns WHERE table_name = 'community_cache' AND column_name = 'crawl_quality_score';" \
    "0.0" \
    "crawl_quality_score 应默认为 0.0"

# 3.2 CHECK 约束存在性
check_test \
    "非负约束数量" \
    "SELECT count(*) FROM information_schema.table_constraints WHERE table_name = 'community_cache' AND constraint_type = 'CHECK' AND constraint_name LIKE 'ck_cache_%nonneg';" \
    "5" \
    "应有 5 个非负约束"

check_test \
    "质量分数范围约束" \
    "SELECT count(*) FROM information_schema.table_constraints WHERE constraint_name = 'ck_cache_quality_range';" \
    "1" \
    "应有质量分数范围约束"

# 3.3 数据有效性检查
check_test \
    "负数计数" \
    "SELECT count(*) FROM community_cache WHERE empty_hit < 0 OR success_hit < 0 OR failure_hit < 0 OR avg_valid_posts < 0 OR total_posts_fetched < 0;" \
    "0" \
    "不应有负数计数"

check_warning \
    "NULL 质量分数" \
    "SELECT count(*) FROM community_cache WHERE crawl_quality_score IS NULL;" \
    "0" \
    "quality_score 不应为 NULL"

# 3.4 调度索引
check_test \
    "TTL 活跃索引" \
    "SELECT count(*) FROM pg_indexes WHERE indexname = 'idx_cache_ttl_active';" \
    "1" \
    "应有 idx_cache_ttl_active 索引"

echo "=== 4. 热帖表索引验证 ==="
echo ""

check_test \
    "社区过期索引" \
    "SELECT count(*) FROM pg_indexes WHERE indexname = 'idx_posts_hot_subreddit_expires';" \
    "1" \
    "应有 idx_posts_hot_subreddit_expires 索引"

echo "=== 5. 性能验证（查询计划）==="
echo ""

echo "检查: 评论查询索引使用"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
EXPLAIN (COSTS OFF)
SELECT * FROM comments WHERE post_id = 1 LIMIT 10;
" | grep -q "Index Scan using idx_comments_post_id" && echo -e "${GREEN}✓ 使用 post_id 索引${NC}" || echo -e "${YELLOW}⚠ 未使用索引${NC}"
echo ""

echo "检查: 社区缓存调度查询"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
EXPLAIN (COSTS OFF)
SELECT * FROM community_cache
WHERE is_active = true
  AND last_crawled_at < now() - (ttl_seconds || ' seconds')::interval
LIMIT 10;
" | grep -q "idx_cache_ttl_active" && echo -e "${GREEN}✓ 使用 TTL 索引${NC}" || echo -e "${YELLOW}⚠ 未使用索引${NC}"
echo ""

echo "检查: 热帖过期查询"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
EXPLAIN (COSTS OFF)
SELECT * FROM posts_hot
WHERE subreddit = 'r/startups'
  AND expires_at > now()
LIMIT 10;
" | grep -q "idx_posts_hot_subreddit_expires" && echo -e "${GREEN}✓ 使用复合索引${NC}" || echo -e "${YELLOW}⚠ 未使用索引${NC}"
echo ""

echo "=== 6. 数据完整性抽查 ==="
echo ""

echo "检查: 占位帖子数量"
placeholder_count=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT count(*) FROM posts_raw WHERE title LIKE '[placeholder%';" | xargs)
echo "占位帖子数: $placeholder_count"
if [ "$placeholder_count" -gt 0 ]; then
    echo -e "${YELLOW}⚠ 建议：回填实际帖子数据后删除占位记录${NC}"
fi
echo ""

echo "检查: 评论-帖子关联完整性"
invalid_fk=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT count(*) FROM comments c
LEFT JOIN posts_raw p ON c.post_id = p.id
WHERE p.id IS NULL;
" | xargs)
if [ "$invalid_fk" -eq 0 ]; then
    echo -e "${GREEN}✓ 所有评论都关联到有效帖子${NC}"
else
    echo -e "${RED}✗ 发现 $invalid_fk 条无效关联${NC}"
fi
echo ""

echo "=========================================="
echo "  验证结果统计"
echo "=========================================="
echo ""
echo -e "${GREEN}通过: $PASS_COUNT${NC}"
echo -e "${YELLOW}警告: $WARN_COUNT${NC}"
echo -e "${RED}失败: $FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ 所有核心修复已生效！${NC}"
    exit 0
else
    echo -e "${RED}✗ 发现 $FAIL_COUNT 个问题，请检查${NC}"
    exit 1
fi
