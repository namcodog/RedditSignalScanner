-- 生产同步：阶段四 4.1 (元数据清洗)
-- 目标：清洗 Pool/Cache/Posts，建立约束
-- 运行环境：生产库

BEGIN;
SET statement_timeout = '60s'; --稍微放宽一点

-- 0. 卸载外键
ALTER TABLE community_cache DROP CONSTRAINT fk_community_cache_pool;

-- 1. 清洗 Pool
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
            DELETE FROM community_pool WHERE id = r.id;
        ELSE
            UPDATE community_pool SET name = r.normalized_name WHERE id = r.id;
        END IF;
    END LOOP;
END $$;

-- 2. 清洗 Cache
DELETE FROM community_cache 
WHERE community_name <> 'r/' || LOWER(REGEXP_REPLACE(community_name, '^r/', '', 'i'))
  AND EXISTS (SELECT 1 FROM community_cache c2 WHERE c2.community_name = 'r/' || LOWER(REGEXP_REPLACE(community_cache.community_name, '^r/', '', 'i')));

UPDATE community_cache
SET community_name = 'r/' || LOWER(REGEXP_REPLACE(community_name, '^r/', '', 'i'))
WHERE community_name <> 'r/' || LOWER(REGEXP_REPLACE(community_name, '^r/', '', 'i'));

-- 3. 恢复外键
DELETE FROM community_cache WHERE community_name NOT IN (SELECT name FROM community_pool);
ALTER TABLE community_cache ADD CONSTRAINT fk_community_cache_pool FOREIGN KEY (community_name) REFERENCES community_pool(name) ON DELETE CASCADE ON UPDATE CASCADE;

-- 4. 清洗 Posts Raw (10万级，应该很快)
UPDATE posts_raw
SET subreddit = 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'))
WHERE subreddit <> 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'));

-- 5. 建立约束
ALTER TABLE community_pool DROP CONSTRAINT IF EXISTS ck_community_pool_name_format;
ALTER TABLE community_pool ADD CONSTRAINT ck_community_pool_name_format CHECK (name ~ '^r/[a-z0-9_]+$');

ALTER TABLE community_cache DROP CONSTRAINT IF EXISTS ck_community_cache_name_format;
ALTER TABLE community_cache ADD CONSTRAINT ck_community_cache_name_format CHECK (community_name ~ '^r/[a-z0-9_]+$');

COMMIT;
