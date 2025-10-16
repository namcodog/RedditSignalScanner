-- 冷热分层存储架构迁移脚本
-- 执行方式：psql -d reddit_scanner -f backend/migrations/001_cold_hot_storage.sql

BEGIN;

-- ============================================================================
-- 1. 创建文本归一化哈希函数
-- ============================================================================
CREATE OR REPLACE FUNCTION text_norm_hash(content TEXT) 
RETURNS UUID AS $$
DECLARE
    normalized TEXT;
BEGIN
    -- 文本归一化：
    -- 1. 转小写
    -- 2. 去除多余空格
    -- 3. 去除标点符号（保留字母数字）
    normalized := regexp_replace(
        lower(trim(content)),
        '[^a-z0-9\s]',
        '',
        'g'
    );
    normalized := regexp_replace(normalized, '\s+', ' ', 'g');
    
    -- 返回 MD5 哈希的 UUID 表示
    RETURN md5(normalized)::UUID;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- 2. 创建冷库表 posts_raw（增量累积，90天滚动窗口）
-- ============================================================================
CREATE TABLE IF NOT EXISTS posts_raw (
    -- 主键：source + source_post_id + version
    id BIGSERIAL,
    source VARCHAR(50) NOT NULL DEFAULT 'reddit',
    source_post_id VARCHAR(100) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    fetched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    valid_to TIMESTAMP WITH TIME ZONE DEFAULT '9999-12-31'::TIMESTAMP,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- 作者信息
    author_id VARCHAR(100),
    author_name VARCHAR(100),
    
    -- 内容
    title TEXT NOT NULL,
    body TEXT,
    body_norm TEXT,  -- 归一化后的正文（由触发器填充）
    text_norm_hash UUID,  -- 文本归一化哈希（由触发器填充）

    -- 元数据
    url TEXT,
    subreddit VARCHAR(100) NOT NULL,
    score INTEGER DEFAULT 0,
    num_comments INTEGER DEFAULT 0,
    is_deleted BOOLEAN DEFAULT FALSE,
    edit_count INTEGER DEFAULT 0,
    lang VARCHAR(10),
    
    -- JSONB 元数据
    metadata JSONB,
    
    -- 约束
    PRIMARY KEY (source, source_post_id, version),
    CONSTRAINT ck_posts_raw_version_positive CHECK (version > 0),
    CONSTRAINT ck_posts_raw_valid_period CHECK (valid_from < valid_to OR valid_to = '9999-12-31'::TIMESTAMP)
);

COMMENT ON TABLE posts_raw IS '冷库：增量累积，保留90天滚动窗口，用于算法训练、趋势分析、回测';
COMMENT ON COLUMN posts_raw.text_norm_hash IS '文本归一化哈希，用于去重（防止转贴/改写）';
COMMENT ON COLUMN posts_raw.is_current IS 'SCD2: 是否当前版本';
COMMENT ON COLUMN posts_raw.version IS 'SCD2: 版本号，每次编辑+1';

-- ============================================================================
-- 3. 创建索引（冷库）
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_posts_raw_created_at ON posts_raw (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_raw_fetched_at ON posts_raw (fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_raw_subreddit ON posts_raw (subreddit, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_raw_text_hash ON posts_raw (text_norm_hash);
CREATE INDEX IF NOT EXISTS idx_posts_raw_source_post_id ON posts_raw (source, source_post_id);
CREATE INDEX IF NOT EXISTS idx_posts_raw_current ON posts_raw (source, source_post_id, is_current) WHERE is_current = TRUE;
CREATE INDEX IF NOT EXISTS idx_posts_raw_metadata_gin ON posts_raw USING GIN (metadata);

-- ============================================================================
-- 4. 创建物化视图 posts_latest（只保留最新版本）
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS posts_latest AS
SELECT 
    id,
    source,
    source_post_id,
    version,
    created_at,
    fetched_at,
    author_id,
    author_name,
    title,
    body,
    body_norm,
    text_norm_hash,
    url,
    subreddit,
    score,
    num_comments,
    is_deleted,
    edit_count,
    lang,
    metadata
FROM posts_raw
WHERE is_current = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_latest_unique ON posts_latest (source, source_post_id);
CREATE INDEX IF NOT EXISTS idx_posts_latest_created_at ON posts_latest (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_latest_subreddit ON posts_latest (subreddit, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_latest_text_hash ON posts_latest (text_norm_hash);

COMMENT ON MATERIALIZED VIEW posts_latest IS '物化视图：只保留最新版本，用于快速查询';

-- ============================================================================
-- 5. 创建热缓存表 posts_hot（覆盖式刷新，24-72小时TTL）
-- ============================================================================
CREATE TABLE IF NOT EXISTS posts_hot (
    -- 主键
    source VARCHAR(50) NOT NULL DEFAULT 'reddit',
    source_post_id VARCHAR(100) NOT NULL,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    cached_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW() + INTERVAL '24 hours',
    
    -- 内容（简化版）
    title TEXT NOT NULL,
    body TEXT,
    subreddit VARCHAR(100) NOT NULL,
    score INTEGER DEFAULT 0,
    num_comments INTEGER DEFAULT 0,
    
    -- 元数据
    metadata JSONB,
    
    -- 约束
    PRIMARY KEY (source, source_post_id)
);

CREATE INDEX IF NOT EXISTS idx_posts_hot_expires_at ON posts_hot (expires_at);
CREATE INDEX IF NOT EXISTS idx_posts_hot_subreddit ON posts_hot (subreddit, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_hot_created_at ON posts_hot (created_at DESC);

COMMENT ON TABLE posts_hot IS '热缓存：覆盖式刷新，保留24-72小时，用于实时分析';

-- ============================================================================
-- 6. 扩展 community_cache 表（添加水位线字段）
-- ============================================================================
ALTER TABLE community_cache 
    ADD COLUMN IF NOT EXISTS last_seen_post_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS last_seen_created_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS total_posts_fetched INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS dedup_rate NUMERIC(5, 2);

COMMENT ON COLUMN community_cache.last_seen_post_id IS '水位线：最后抓取的帖子ID';
COMMENT ON COLUMN community_cache.last_seen_created_at IS '水位线：最后抓取的帖子创建时间';
COMMENT ON COLUMN community_cache.total_posts_fetched IS '累计抓取的帖子数';
COMMENT ON COLUMN community_cache.dedup_rate IS '去重率（%）';

-- ============================================================================
-- 7. 创建触发器函数：自动填充 body_norm 和 text_norm_hash
-- ============================================================================
CREATE OR REPLACE FUNCTION fill_normalized_fields()
RETURNS TRIGGER AS $$
BEGIN
    -- 填充 body_norm
    NEW.body_norm := regexp_replace(
        regexp_replace(lower(trim(COALESCE(NEW.body, ''))), '[^a-z0-9\s]', '', 'g'),
        '\s+', ' ', 'g'
    );

    -- 填充 text_norm_hash
    NEW.text_norm_hash := md5(
        regexp_replace(
            regexp_replace(lower(trim(NEW.title || ' ' || COALESCE(NEW.body, ''))), '[^a-z0-9\s]', '', 'g'),
            '\s+', ' ', 'g'
        )
    )::UUID;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_fill_normalized_fields
BEFORE INSERT OR UPDATE ON posts_raw
FOR EACH ROW
EXECUTE FUNCTION fill_normalized_fields();

COMMENT ON FUNCTION fill_normalized_fields() IS '自动填充归一化字段';

-- ============================================================================
-- 8. 创建自动刷新物化视图的函数
-- ============================================================================
CREATE OR REPLACE FUNCTION refresh_posts_latest()
RETURNS INTEGER AS $$
DECLARE
    refresh_count INTEGER;
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY posts_latest;
    GET DIAGNOSTICS refresh_count = ROW_COUNT;
    RETURN refresh_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_posts_latest() IS '刷新 posts_latest 物化视图';

-- ============================================================================
-- 8. 创建清理过期热缓存的函数
-- ============================================================================
CREATE OR REPLACE FUNCTION cleanup_expired_hot_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM posts_hot
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_expired_hot_cache() IS '清理过期的热缓存';

-- ============================================================================
-- 9. 创建清理旧数据的函数（90天滚动窗口）
-- ============================================================================
CREATE OR REPLACE FUNCTION cleanup_old_posts(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
    cutoff_date TIMESTAMP WITH TIME ZONE;
BEGIN
    cutoff_date := NOW() - (days_to_keep || ' days')::INTERVAL;
    
    DELETE FROM posts_raw
    WHERE created_at < cutoff_date
      AND is_current = FALSE;  -- 只删除非当前版本
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_posts(INTEGER) IS '清理超过N天的旧帖子（只删除非当前版本）';

-- ============================================================================
-- 10. 创建统计函数
-- ============================================================================
CREATE OR REPLACE FUNCTION get_storage_stats()
RETURNS TABLE (
    metric VARCHAR(50),
    value BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'posts_raw_total'::VARCHAR(50), COUNT(*)::BIGINT FROM posts_raw
    UNION ALL
    SELECT 'posts_raw_current'::VARCHAR(50), COUNT(*)::BIGINT FROM posts_raw WHERE is_current = TRUE
    UNION ALL
    SELECT 'posts_hot_total'::VARCHAR(50), COUNT(*)::BIGINT FROM posts_hot
    UNION ALL
    SELECT 'posts_hot_expired'::VARCHAR(50), COUNT(*)::BIGINT FROM posts_hot WHERE expires_at < NOW()
    UNION ALL
    SELECT 'unique_subreddits'::VARCHAR(50), COUNT(DISTINCT subreddit)::BIGINT FROM posts_raw
    UNION ALL
    SELECT 'total_versions'::VARCHAR(50), SUM(version)::BIGINT FROM posts_raw WHERE is_current = TRUE;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_storage_stats() IS '获取存储统计信息';

COMMIT;

-- ============================================================================
-- 验证
-- ============================================================================
SELECT '✅ 冷热分层存储架构创建完成！' AS status;
SELECT * FROM get_storage_stats();

