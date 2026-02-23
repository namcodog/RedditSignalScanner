-- 生产同步：阶段四 (数据一致性治理)
-- 目标：强制社区名小写 + r/ 前缀
-- 风险：中 (会修改 community_pool/cache/posts_raw 数据)

BEGIN;

-- 1. 清洗 community_pool (核心元数据)
-- 逻辑：转小写，确保 r/ 前缀。
-- 注意：如果有 r/Apple 和 r/apple，这里可能会冲突，所以我们先处理冲突
-- 简单起见，对于生产库，我们先尝试直接 UPDATE。如果冲突，说明需要人工介入合并 (Fail Fast)。
UPDATE community_pool
SET name = 'r/' || LOWER(REGEXP_REPLACE(name, '^r/', '', 'i'))
WHERE name <> 'r/' || LOWER(REGEXP_REPLACE(name, '^r/', '', 'i'));

-- 2. 清洗 community_cache
UPDATE community_cache
SET community_name = 'r/' || LOWER(REGEXP_REPLACE(community_name, '^r/', '', 'i'))
WHERE community_name <> 'r/' || LOWER(REGEXP_REPLACE(community_name, '^r/', '', 'i'));

-- 3. 清洗 posts_raw (海量数据，可能慢)
UPDATE posts_raw
SET subreddit = 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'))
WHERE subreddit <> 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'));

-- 4. 清洗 comments
UPDATE comments
SET subreddit = 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'))
WHERE subreddit <> 'r/' || LOWER(REGEXP_REPLACE(subreddit, '^r/', '', 'i'));

-- 5. 建立防护网 (Check Constraints)
-- 先删除旧的（如果名字不规范）
ALTER TABLE community_pool DROP CONSTRAINT IF EXISTS ck_community_pool_name_format;
ALTER TABLE community_pool ADD CONSTRAINT ck_community_pool_name_format CHECK (name ~ '^r/[a-z0-9_]+$');

ALTER TABLE community_cache DROP CONSTRAINT IF EXISTS ck_community_cache_name_format;
ALTER TABLE community_cache ADD CONSTRAINT ck_community_cache_name_format CHECK (community_name ~ '^r/[a-z0-9_]+$');

COMMIT;
