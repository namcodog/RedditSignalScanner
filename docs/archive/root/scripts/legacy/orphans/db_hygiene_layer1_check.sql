-- Layer 1: Coarse Screening Diagnostic Script (Read-Only)
-- David's X-Ray for Reddit Signal Scanner

BEGIN;

-- 1. 鬼魂贴 (Ghosts)
SELECT 'Ghosts ([deleted]/[removed]/Empty)' as trash_type, COUNT(*) as count 
FROM posts_raw 
WHERE (title IS NULL OR trim(title) = '') 
   OR (body IS NOT NULL AND trim(body) IN ('[deleted]', '[removed]'))
   OR (is_deleted = true);

-- 2. 短命鬼 (Too Short)
-- 标题+正文 总长度小于 10 个字符，且不是已删除的（避免重复统计）
SELECT 'Too Short (<10 chars)' as trash_type, COUNT(*) as count 
FROM posts_raw 
WHERE length(coalesce(title, '') || ' ' || coalesce(body, '')) < 10
  AND NOT ((title IS NULL OR trim(title) = '') OR (body IS NOT NULL AND trim(body) IN ('[deleted]', '[removed]')) OR (is_deleted = true));

-- 3. 老古董 (Ancient)
-- 3年前的数据
SELECT 'Ancient (>3 Years)' as trash_type, COUNT(*) as count 
FROM posts_raw 
WHERE created_at < NOW() - INTERVAL '3 years';

-- 4. 重复内容 (Content Duplicates)
-- 统计有多少行是属于“内容完全重复”的冗余行
SELECT 'Duplicates (Redundant Rows)' as trash_type, SUM(cnt - 1) as count
FROM (
    SELECT text_norm_hash, COUNT(*) as cnt
    FROM posts_raw 
    WHERE text_norm_hash IS NOT NULL 
    GROUP BY text_norm_hash 
    HAVING COUNT(*) > 1
) sub;

-- 5. 语言检查 (Language Check)
SELECT 'Non-English (Tagged)' as trash_type, COUNT(*) as count
FROM posts_raw
WHERE lang IS NOT NULL AND lang != 'en';

-- 总行数参考
SELECT 'Total Rows' as trash_type, COUNT(*) as count FROM posts_raw;

ROLLBACK;
