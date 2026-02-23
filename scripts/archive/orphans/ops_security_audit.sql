-- 数据库运维与安全深度体检脚本
-- 目标：发现权限、配置、连接层面的隐患
-- 运行环境：生产库 (reddit_signal_scanner)

-- 1. 检查当前连接用户与权限
SELECT 
    usename, 
    usesuper, 
    usecreatedb, 
    valuntil as password_expiry,
    CASE WHEN usename = 'postgres' THEN '⚠️ RISK: App using superuser?' ELSE '✅ OK' END as risk_check
FROM pg_user
WHERE usename = current_user;

-- 2. 检查连接数配置
SELECT 
    name, setting, unit, 
    CASE 
        WHEN name = 'max_connections' AND setting::int < 100 THEN '⚠️ LOW' 
        WHEN name = 'max_connections' AND setting::int > 500 THEN '⚠️ HIGH' 
        ELSE '✅ OK' 
    END as status
FROM pg_settings WHERE name = 'max_connections';

-- 3. 检查内存参数 (Performance)
-- work_mem 默认 4MB，对于大数据量排序/JOIN 很容易溢出到磁盘
SELECT 
    name, setting, unit,
    CASE 
        WHEN setting::int <= 4096 THEN '⚠️ WARNING: Default 4MB might be too small for analytics' 
        ELSE '✅ OK' 
    END as status
FROM pg_settings WHERE name = 'work_mem';

-- 4. 检查已安装插件 (Extension Sprawl)
SELECT extname, extversion, 
    CASE 
        WHEN extname IN ('plpgsql', 'vector', 'pg_trgm', 'btree_gin') THEN '✅ Standard'
        ELSE '❓ Review Needed' 
    END as review_status
FROM pg_extension;

-- 5. 检查是否有巨大的 Bloat 表 (Autovacuum 是否罢工)
-- 简单估算：死元组超过 10000 且占比超过 20%
SELECT 
    relname, 
    n_live_tup, 
    n_dead_tup, 
    last_autovacuum, 
    last_autoanalyze,
    CASE 
        WHEN n_dead_tup > 10000 AND (n_dead_tup::float / (n_live_tup + 1)) > 0.2 THEN '🚨 CRITICAL BLOAT'
        ELSE '✅ Healthy' 
    END as bloat_status
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 5;
