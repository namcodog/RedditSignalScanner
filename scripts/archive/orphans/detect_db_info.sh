#!/bin/bash
set -e

# 数据库信息自动检测脚本
# 用途：收集数据库连接信息和规模数据，辅助迁移规划

echo "=========================================="
echo "  数据库信息自动检测工具"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 从 .env 文件读取配置
if [ -f "backend/.env" ]; then
    echo -e "${GREEN}✓ 发现 .env 配置文件${NC}"
    source backend/.env
elif [ -f "backend/.env.example" ]; then
    echo -e "${YELLOW}⚠ 未找到 .env，使用 .env.example 作为示例${NC}"
    source backend/.env.example
else
    echo -e "${RED}✗ 未找到配置文件${NC}"
    exit 1
fi

# 解析 DATABASE_URL
# 格式: postgresql+asyncpg://user:pass@host:port/dbname
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}✗ DATABASE_URL 未设置${NC}"
    exit 1
fi

# 提取连接信息（兼容 postgresql:// 和 postgresql+asyncpg://）
DB_URL_CLEAN=$(echo $DATABASE_URL | sed 's/+asyncpg//')
DB_USER=$(echo $DB_URL_CLEAN | sed -n 's|.*://\([^:]*\):.*|\1|p')
DB_PASS=$(echo $DB_URL_CLEAN | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
DB_HOST=$(echo $DB_URL_CLEAN | sed -n 's|.*@\([^:]*\):.*|\1|p')
DB_PORT=$(echo $DB_URL_CLEAN | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
DB_NAME=$(echo $DB_URL_CLEAN | sed -n 's|.*/\([^?]*\).*|\1|p')

echo ""
echo "=== 1. 数据库连接信息 ==="
echo "主机地址: $DB_HOST"
echo "端口: $DB_PORT"
echo "数据库名: $DB_NAME"
echo "用户名: $DB_USER"
echo "密码: $(echo $DB_PASS | sed 's/./*/g')"  # 脱敏显示
echo ""

# 测试连接
echo "=== 2. 测试数据库连接 ==="
export PGPASSWORD=$DB_PASS

if psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 数据库连接成功${NC}"
else
    echo -e "${RED}✗ 数据库连接失败，请检查配置${NC}"
    echo ""
    echo "调试命令:"
    echo "  psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"
    exit 1
fi
echo ""

# 查询数据库信息
echo "=== 3. 数据库版本信息 ==="
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT version();" | head -n 1
echo ""

echo "=== 4. 当前用户权限 ==="
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\du $DB_USER" 2>/dev/null || echo "无法查询用户权限"
echo ""

echo "=== 5. SSL 配置 ==="
SSL_STATUS=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SHOW ssl;" | xargs)
echo "SSL 状态: $SSL_STATUS"
echo ""

echo "=== 6. 数据库规模 ==="
echo "数据库总大小:"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
    SELECT pg_size_pretty(pg_database_size(current_database())) AS database_size;
"
echo ""

echo "=== 7. 表数据规模（前10大表）==="
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
    SELECT
        schemaname || '.' || tablename AS table_name,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
        pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS data_size,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size,
        n_live_tup AS row_count
    FROM pg_tables
    LEFT JOIN pg_stat_user_tables ON pg_tables.tablename = pg_stat_user_tables.relname
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
    LIMIT 10;
"
echo ""

echo "=== 8. 核心表行数统计 ==="
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
    SELECT
        relname AS table_name,
        n_live_tup AS row_count,
        pg_size_pretty(pg_total_relation_size(relid)) AS total_size
    FROM pg_stat_user_tables
    WHERE relname IN ('community_pool', 'community_cache', 'posts_hot', 'posts_raw', 'comments')
    ORDER BY n_live_tup DESC;
"
echo ""

echo "=== 9. 索引统计 ==="
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
    SELECT
        schemaname || '.' || tablename AS table_name,
        indexname,
        pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
    FROM pg_indexes
    LEFT JOIN pg_stat_user_indexes ON pg_indexes.indexname = pg_stat_user_indexes.indexrelname
    WHERE schemaname = 'public'
    ORDER BY pg_relation_size(indexrelid) DESC
    LIMIT 15;
"
echo ""

echo "=== 10. 当前连接数 ==="
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
    SELECT
        count(*) AS total_connections,
        count(*) FILTER (WHERE state = 'active') AS active_connections,
        count(*) FILTER (WHERE state = 'idle') AS idle_connections
    FROM pg_stat_activity;
"
echo ""

echo "=== 11. 长查询检查 ==="
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
    SELECT
        pid,
        now() - query_start AS duration,
        state,
        LEFT(query, 100) AS query_preview
    FROM pg_stat_activity
    WHERE state != 'idle'
      AND query NOT LIKE '%pg_stat_activity%'
    ORDER BY duration DESC
    LIMIT 5;
"
echo ""

# 生成配置摘要
echo "=========================================="
echo "  配置摘要（用于迁移规划）"
echo "=========================================="
echo ""
echo "数据库连接信息:"
echo "  主机: $DB_HOST"
echo "  端口: $DB_PORT"
echo "  数据库: $DB_NAME"
echo "  用户: $DB_USER"
echo "  SSL: $SSL_STATUS"
echo ""

# 获取表行数
COMMUNITY_POOL_ROWS=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT n_live_tup FROM pg_stat_user_tables WHERE relname='community_pool';" | xargs)
POSTS_HOT_ROWS=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT n_live_tup FROM pg_stat_user_tables WHERE relname='posts_hot';" | xargs)
POSTS_RAW_ROWS=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT n_live_tup FROM pg_stat_user_tables WHERE relname='posts_raw';" | xargs)
COMMENTS_ROWS=$(psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT n_live_tup FROM pg_stat_user_tables WHERE relname='comments';" | xargs)

echo "数据规模:"
echo "  community_pool: ${COMMUNITY_POOL_ROWS:-0} 行"
echo "  posts_hot: ${POSTS_HOT_ROWS:-0} 行"
echo "  posts_raw: ${POSTS_RAW_ROWS:-0} 行"
echo "  comments: ${COMMENTS_ROWS:-0} 行"
echo ""

# 评估迁移时间
TOTAL_ROWS=$((${COMMUNITY_POOL_ROWS:-0} + ${POSTS_HOT_ROWS:-0} + ${POSTS_RAW_ROWS:-0} + ${COMMENTS_ROWS:-0}))
echo "总行数: $TOTAL_ROWS"
echo ""

if [ $TOTAL_ROWS -lt 100000 ]; then
    echo -e "${GREEN}数据规模: 小 (<10万行)${NC}"
    echo "预估迁移时间: 10-30 分钟"
elif [ $TOTAL_ROWS -lt 1000000 ]; then
    echo -e "${YELLOW}数据规模: 中 (10万-100万行)${NC}"
    echo "预估迁移时间: 30-90 分钟"
else
    echo -e "${RED}数据规模: 大 (>100万行)${NC}"
    echo "预估迁移时间: 1-3 小时"
    echo "建议: 使用分区表策略"
fi
echo ""

echo "=========================================="
echo "  检测完成！"
echo "=========================================="
echo ""
echo "下一步:"
echo "  1. 将上述信息复制到 '数据库连接信息模板.md'"
echo "  2. 确定首选维护窗口（建议: 凌晨 02:00-06:00）"
echo "  3. 告知 Claude 您的环境类型（开发/测试/生产）"
echo ""
