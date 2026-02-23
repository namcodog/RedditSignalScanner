-- 数据库全系统深度体检脚本
-- 目标：发现序列失步、无效索引、残留约束等隐蔽问题
-- 运行环境：生产库 (reddit_signal_scanner)

-- 1. 检查无效索引 (Failed Indexes)
SELECT schemaname, relname as table_name, indexrelname as index_name
FROM pg_indexes
JOIN pg_class ON pg_indexes.indexrelname = pg_class.relname
JOIN pg_index ON pg_class.oid = pg_index.indexrelid
WHERE pg_index.indisvalid = FALSE;

-- 2. 检查序列是否失步 (Sequence Out of Sync)
-- 逻辑：如果 sequence 的 last_value < max(id)，下次插入会报错
SELECT 
    s.relname AS sequence_name,
    t.relname AS table_name,
    COALESCE(s.last_value, 0) AS seq_value,
    COALESCE(t.max_id, 0) AS table_max_id,
    CASE 
        WHEN COALESCE(s.last_value, 0) < COALESCE(t.max_id, 0) THEN '⚠️ DANGER: Out of Sync'
        ELSE '✅ OK' 
    END AS status
FROM pg_sequences s
JOIN (
    SELECT 'posts_raw_id_seq' AS seq, 'posts_raw' AS tbl, MAX(id) AS max_id FROM posts_raw
    UNION ALL
    SELECT 'comments_id_seq', 'comments', MAX(id) FROM comments
    UNION ALL
    SELECT 'community_pool_id_seq', 'community_pool', MAX(id) FROM community_pool
    UNION ALL
    SELECT 'posts_hot_id_seq', 'posts_hot', MAX(id) FROM posts_hot
) t ON s.sequencename = t.seq;

-- 3. 检查残留的不规范约束 (Constraint Hygiene)
-- 查找仍然包含重复表名的约束 (例如 ck_table_ck_table_...)
SELECT conname, conrelid::regclass AS table_name
FROM pg_constraint 
WHERE conname ~ 'ck_[a-z]+_ck_[a-z]+_';

-- 4. 检查是否有未启用的触发器 (Disabled Triggers)
SELECT tgname, tgrelid::regclass AS table_name, tgenabled
FROM pg_trigger
WHERE tgenabled = 'D';

-- 5. 检查关键表的统计信息 (Bloat Warning)
-- 简单查看死元组 (Dead Tuples) 比例，如果过高需要 VACUUM
SELECT 
    relname AS table_name, 
    n_live_tup AS live_rows, 
    n_dead_tup AS dead_rows,
    ROUND(n_dead_tup::numeric / (n_live_tup + n_dead_tup + 1) * 100, 2) AS dead_ratio_percent
FROM pg_stat_user_tables
WHERE relname IN ('posts_raw', 'comments', 'community_cache', 'posts_hot')
ORDER BY dead_rows DESC;
