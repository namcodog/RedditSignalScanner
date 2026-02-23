-- 添加全文检索能力
-- 目标：支持高效的关键词搜索
-- 运行环境：测试库/生产库

BEGIN;

-- 1. 在 posts_raw 添加生成的 tsvector 列
-- 使用 'english' 配置，合并标题和正文
-- COALESCE 防止 NULL 导致结果为 NULL
ALTER TABLE posts_raw
ADD COLUMN IF NOT EXISTS content_tsvector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(body, ''))
) STORED;

-- 2. 创建 GIN 索引
CREATE INDEX IF NOT EXISTS idx_posts_raw_content_gin
ON posts_raw USING GIN (content_tsvector);

-- 3. 对 posts_hot 也做同样操作 (如果需要热表搜索)
ALTER TABLE posts_hot
ADD COLUMN IF NOT EXISTS content_tsvector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(body, ''))
) STORED;

CREATE INDEX IF NOT EXISTS idx_posts_hot_content_gin
ON posts_hot USING GIN (content_tsvector);

COMMIT;
