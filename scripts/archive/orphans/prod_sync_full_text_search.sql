-- 生产同步：全文检索能力 (Full Text Search)
-- 目标：添加 tsvector 自动列和 GIN 索引
-- 运行环境：生产库

BEGIN;

-- 1. 对 posts_raw 添加全文检索能力
-- GENERATED ALWAYS ... STORED 意味着数据会自动更新，无需触发器
ALTER TABLE posts_raw
ADD COLUMN IF NOT EXISTS content_tsvector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(body, ''))
) STORED;

-- 创建 GIN 索引 (耗时操作，生产环境建议 CONCURRENTLY，但在事务块中不支持，只能硬抗或分步)
-- 本地库 10万数据量秒级完成，直接执行即可
CREATE INDEX IF NOT EXISTS idx_posts_raw_content_gin
ON posts_raw USING GIN (content_tsvector);

-- 2. 对 posts_hot 也做同样操作
ALTER TABLE posts_hot
ADD COLUMN IF NOT EXISTS content_tsvector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(body, ''))
) STORED;

CREATE INDEX IF NOT EXISTS idx_posts_hot_content_gin
ON posts_hot USING GIN (content_tsvector);

COMMIT;
