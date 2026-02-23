-- 检查序列同步 V3 (Final)
SELECT 
    s.sequencename,
    t.tbl,
    s.last_value,
    t.max_id,
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
