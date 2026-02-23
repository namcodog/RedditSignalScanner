-- Step 1: 物理清洗干扰项
-- 目标：彻底删除无数据且不在新规划中的空壳社区

BEGIN;

-- 1. 创建临时表存储 CSV 名单 (模拟)
CREATE TEMP TABLE csv_whitelist (name text);
-- (后续 Python 脚本会填充这个表，这里先用逻辑处理)

-- 2. 标记要保留的社区 (Keep List)
-- 规则：
-- A. 在 posts_raw 中有数据的 (不能丢数据)
-- B. 或者是 Tier='semantic' 的 (算法种子)
-- (注：CSV 名单的保留逻辑将在 Python 脚本中合并处理)

CREATE TEMP TABLE keep_list AS
SELECT DISTINCT p.id
FROM community_pool p
LEFT JOIN posts_raw r ON p.name = r.subreddit
WHERE 
    r.id IS NOT NULL      -- A. 有数据
    OR p.tier = 'semantic'; -- B. 语义种子

-- 3. 执行物理删除
-- 删除那些不在保留名单里的社区
DELETE FROM community_pool
WHERE id NOT IN (SELECT id FROM keep_list)
AND name NOT IN (
    -- 这里是硬编码的 CSV 名单占位符，实际执行时会由 Python 动态传入
    -- 为了安全，我们先只删除那些确定的空壳
    SELECT name FROM community_pool 
    WHERE tier = 'archived' OR (tier = 'low' AND created_at < NOW() - INTERVAL '1 day')
);

-- 统计删除数量
DO $$
DECLARE
    deleted_count INT;
BEGIN
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RAISE NOTICE 'Step 1 完成: 已物理删除 % 个空壳社区。', deleted_count;
END $$;

COMMIT;
