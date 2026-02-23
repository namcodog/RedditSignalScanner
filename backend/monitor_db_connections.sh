#!/bin/bash
# 监控数据库连接状态

echo "=========================================="
echo "数据库连接监控"
echo "=========================================="
echo ""

# 默认监控 Dev 库；需要对照金库请手动传 DB_NAME=reddit_signal_scanner
DB_NAME="${DB_NAME:-reddit_signal_scanner_dev}"

# 检查僵尸连接
echo "1. 僵尸连接（idle in transaction）："
psql -U postgres -d "$DB_NAME" -c "
SELECT 
    COUNT(*) as zombie_count,
    state
FROM pg_stat_activity 
WHERE state LIKE '%idle in transaction%'
GROUP BY state;
" || echo "  无僵尸连接"

echo ""

# 检查活跃连接
echo "2. 活跃连接总数："
psql -U postgres -d "$DB_NAME" -c "
SELECT 
    state,
    COUNT(*) as count
FROM pg_stat_activity 
WHERE datname = '$DB_NAME'
GROUP BY state
ORDER BY count DESC;
"

echo ""

# 检查锁
echo "3. 事务锁（transactionid）："
psql -U postgres -d "$DB_NAME" -c "
SELECT 
    locktype,
    COUNT(*) as lock_count
FROM pg_locks 
WHERE locktype = 'transactionid'
GROUP BY locktype;
" || echo "  无事务锁"

echo ""
echo "=========================================="
echo "监控完成"
echo "=========================================="
