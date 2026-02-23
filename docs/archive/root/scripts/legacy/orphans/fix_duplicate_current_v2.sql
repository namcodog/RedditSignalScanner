-- 终极清洗脚本：按 ID 降序保留唯一 Current
-- 逻辑：同一 Post ID 若有多个 Current，保留 ID 最大的，其余 Kill。

BEGIN;

-- 1. 锁定目标：找出有重复 Current 的 Post ID 列表
CREATE TEMP TABLE target_posts AS
SELECT source, source_post_id
FROM posts_raw
WHERE is_current = true
GROUP BY source, source_post_id
HAVING COUNT(*) > 1;

-- 2. 标记要清洗的行 (The ones to kill)
-- 逻辑：在目标组内，ID 不是最大的那些行
CREATE TEMP TABLE rows_to_kill AS
SELECT r.id
FROM posts_raw r
JOIN target_posts t ON r.source = t.source AND r.source_post_id = t.source_post_id
WHERE r.is_current = true
AND r.id < (
    -- 找出该组最大的 ID
    SELECT MAX(r2.id)
    FROM posts_raw r2
    WHERE r2.source = r.source 
      AND r2.source_post_id = r.source_post_id
      AND r2.is_current = true
);

-- 3. 执行清洗
UPDATE posts_raw
SET is_current = false,
    valid_to = NOW() -- 结束其生命周期
WHERE id IN (SELECT id FROM rows_to_kill);

-- 4. 验证
SELECT COUNT(*) as remaining_dups 
FROM (
    SELECT source, source_post_id
    FROM posts_raw
    WHERE is_current = true
    GROUP BY source, source_post_id
    HAVING COUNT(*) > 1
) sub;

COMMIT;
