-- Step 5: 清理非电商领域的技术社区
-- 目标：删除 categories 为数组格式的历史遗留社区 (如 python, aws, saas)

BEGIN;

-- 1. 锁定目标
CREATE TEMP TABLE to_purge AS
SELECT id, name 
FROM community_pool 
WHERE jsonb_typeof(categories) = 'array';

-- 2. 关联删除 (如果有)
DELETE FROM discovered_communities 
WHERE name IN (SELECT name FROM to_purge);

DELETE FROM tier_suggestions 
WHERE community_name IN (SELECT name FROM to_purge);

DELETE FROM community_cache
WHERE community_name IN (SELECT name FROM to_purge);

-- 3. 物理删除主表
DELETE FROM community_pool
WHERE id IN (SELECT id FROM to_purge);

-- 4. 结果验证
DO $$
DECLARE
    deleted_count INT;
BEGIN
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RAISE NOTICE '已彻底清理 % 个非业务相关的技术社区。', deleted_count;
END $$;

COMMIT;
