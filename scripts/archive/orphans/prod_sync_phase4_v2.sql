-- 生产同步：阶段四 v2 (智能去重版)
-- 目标：处理大小写冲突，合并/删除重复社区
-- 运行环境：生产库

BEGIN;

-- 0. 临时表：找出所有标准化后会冲突的名字
CREATE TEMP TABLE conflict_map AS
SELECT 
    name as original_name,
    'r/' || LOWER(REGEXP_REPLACE(name, '^r/', '', 'i')) as normalized_name,
    id
FROM community_pool
WHERE name <> 'r/' || LOWER(REGEXP_REPLACE(name, '^r/', '', 'i'));

-- 1. 处理冲突
-- 对于每一个冲突的大写名字，检查是否已经存在对应的小写名字
DO $$
DECLARE
    r RECORD;
    target_id INT;
BEGIN
    FOR r IN SELECT * FROM conflict_map LOOP
        -- 查目标小写名字是否存在
        SELECT id INTO target_id FROM community_pool WHERE name = r.normalized_name;
        
        IF target_id IS NOT NULL THEN
            -- 冲突情况 A：小写已存在。
            -- 动作：删除大写记录 (FK 会置空或级联，需小心)
            -- 由于 community_cache 是 CASCADE，posts_raw 无 FK，所以删 pool 是安全的
            -- 但为了保险，我们先删 cache 引用
            DELETE FROM community_cache WHERE community_name = r.original_name;
            DELETE FROM community_pool WHERE id = r.id;
            RAISE NOTICE 'Merged/Deleted duplicate: % -> %', r.original_name, r.normalized_name;
        ELSE
            -- 冲突情况 B：小写不存在。
            -- 动作：直接改名
            UPDATE community_pool SET name = r.normalized_name WHERE id = r.id;
        END IF;
    END LOOP;
END $$;

-- 2. 现在 community_pool 干净了，可以处理从表
-- 2.1 Cache 表 (先删重，再改名)
-- 如果 r/Apple 和 r/apple 都在 cache 里，直接删 r/Apple (因为它对应的 pool 记录刚才已经被干掉了)
DELETE FROM community_cache 
WHERE community_name <> 'r/' || LOWER(REGEXP_REPLACE(community_name, '^r/', '', 'i'))
  AND EXISTS (SELECT 1 FROM community_cache c2 WHERE c2.community_name = 'r/' || LOWER(REGEXP_REPLACE(community_cache.community_name, '^r/', '', 'i')));

-- 剩下的直接改名
UPDATE community_cache
SET community_name = 'r/' || LOWER(REGEXP_REPLACE(community_name, '^r/', '', 'i'))
WHERE community_name <> 'r/' || LOWER(REGEXP_REPLACE(community_name, '^r/', '', 'i'));

-- 2.2 Posts Raw (直接改名，无唯一约束冲突风险)
UPDATE posts_raw
SET subreddit = 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'))
WHERE subreddit <> 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'));

-- 2.3 Comments
UPDATE comments
SET subreddit = 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'))
WHERE subreddit <> 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'));

-- 3. 建立防护网
ALTER TABLE community_pool DROP CONSTRAINT IF EXISTS ck_community_pool_name_format;
ALTER TABLE community_pool ADD CONSTRAINT ck_community_pool_name_format CHECK (name ~ '^r/[a-z0-9_]+$');

ALTER TABLE community_cache DROP CONSTRAINT IF EXISTS ck_community_cache_name_format;
ALTER TABLE community_cache ADD CONSTRAINT ck_community_cache_name_format CHECK (community_name ~ '^r/[a-z0-9_]+$');

COMMIT;
