-- 生产同步：阶段四 v3 (外键解绑版)
-- 目标：先卸载外键，清洗完再装回
-- 运行环境：生产库

BEGIN;

-- 0. 临时卸载外键
ALTER TABLE community_cache DROP CONSTRAINT fk_community_cache_pool;

-- 1. 清洗 community_pool (处理冲突)
-- 逻辑同 v2：有冲突删旧，无冲突改名
DO $$
DECLARE
    r RECORD;
    target_id INT;
BEGIN
    FOR r IN 
        SELECT id, name as original_name, 'r/' || LOWER(REGEXP_REPLACE(name, '^r/', '', 'i')) as normalized_name
        FROM community_pool
        WHERE name <> 'r/' || LOWER(REGEXP_REPLACE(name, '^r/', '', 'i'))
    LOOP
        SELECT id INTO target_id FROM community_pool WHERE name = r.normalized_name;
        
        IF target_id IS NOT NULL THEN
            -- 冲突：删除大写记录 (pool)
            -- 注意：此时 cache 表里还有指向 r/UpperCase 的孤儿数据，稍后会在步骤 2 清理
            DELETE FROM community_pool WHERE id = r.id;
            RAISE NOTICE 'Deleted duplicate pool: %', r.original_name;
        ELSE
            -- 无冲突：改名
            UPDATE community_pool SET name = r.normalized_name WHERE id = r.id;
        END IF;
    END LOOP;
END $$;

-- 2. 清洗 community_cache
-- 2.1 先处理冲突：如果 r/Apple 和 r/apple 都在，保留小写的数据（或者合并数据，这里简单起见我们删大写）
DELETE FROM community_cache 
WHERE community_name <> 'r/' || LOWER(REGEXP_REPLACE(community_name, '^r/', '', 'i'))
  AND EXISTS (SELECT 1 FROM community_cache c2 WHERE c2.community_name = 'r/' || LOWER(REGEXP_REPLACE(community_cache.community_name, '^r/', '', 'i')));

-- 2.2 改名
UPDATE community_cache
SET community_name = 'r/' || LOWER(REGEXP_REPLACE(community_name, '^r/', '', 'i'))
WHERE community_name <> 'r/' || LOWER(REGEXP_REPLACE(community_name, '^r/', '', 'i'));

-- 3. 恢复外键 (带上 ON UPDATE CASCADE)
-- 注意：清洗后可能仍有孤儿数据（比如 cache 里有 r/xyz，但 pool 里没有），先删掉孤儿
DELETE FROM community_cache 
WHERE community_name NOT IN (SELECT name FROM community_pool);

ALTER TABLE community_cache 
ADD CONSTRAINT fk_community_cache_pool 
FOREIGN KEY (community_name) REFERENCES community_pool(name) 
ON DELETE CASCADE ON UPDATE CASCADE;

-- 4. 清洗其他表
UPDATE posts_raw
SET subreddit = 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'))
WHERE subreddit <> 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'));

UPDATE comments
SET subreddit = 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'))
WHERE subreddit <> 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'));

-- 5. 建立 Check 约束
ALTER TABLE community_pool DROP CONSTRAINT IF EXISTS ck_community_pool_name_format;
ALTER TABLE community_pool ADD CONSTRAINT ck_community_pool_name_format CHECK (name ~ '^r/[a-z0-9_]+$');

ALTER TABLE community_cache DROP CONSTRAINT IF EXISTS ck_community_cache_name_format;
ALTER TABLE community_cache ADD CONSTRAINT ck_community_cache_name_format CHECK (community_name ~ '^r/[a-z0-9_]+$');

COMMIT;
