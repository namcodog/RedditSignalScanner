-- 数据库全系统深度体检脚本 V2 (修正版)
-- 运行环境：生产库 (reddit_signal_scanner)

-- 1. 检查无效索引 (Fixed)
SELECT n.nspname as schemaname,
       c.relname as table_name,
       i.relname as index_name
FROM pg_class c
JOIN pg_index x ON c.oid = x.indrelid
JOIN pg_class i ON i.oid = x.indexrelid
LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r' AND i.relkind = 'i' AND x.indisvalid = FALSE;

-- 2. 检查序列是否失步 (Fixed)
-- 逻辑：检查 last_value 是否小于 max(id)
SELECT 
    s.sequencename AS sequence_name,
    t.relname AS table_name,
    s.last_value AS seq_value,
    t.max_id AS table_max_id,
    CASE 
        WHEN COALESCE(s.last_value, 0) < COALESCE(t.max_id, 0) THEN '⚠️ DANGER'
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

-- 3. 补救漏网之鱼 (Fix Evidences Constraint)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_evidences_ck_evidences_score_range') THEN
        ALTER TABLE public.evidences RENAME CONSTRAINT "ck_evidences_ck_evidences_score_range" TO "ck_evidences_score_range";
    END IF;
END $$;
