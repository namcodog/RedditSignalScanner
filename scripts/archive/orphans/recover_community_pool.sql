-- 灾难恢复脚本：从 posts_raw 重建社区池与水位线
-- 目标：恢复 community_pool 和 community_cache，让 Celery 能接手工作。

BEGIN;

-- 1. 恢复 Community Pool
-- 从现有的帖子中提取所有不重复的 subreddit
INSERT INTO community_pool (
    name, is_active, created_at, updated_at, tier, priority, 
    categories, description_keywords,
    semantic_quality_score, health_status, auto_tier_enabled,
    daily_posts, avg_comment_length, user_feedback_count, discovered_count, is_blacklisted
)
SELECT 
    subreddit, 
    true,           -- 默认激活
    MIN(fetched_at), -- 创建时间取最早抓取时间
    NOW(),
    'medium',       -- 默认 Tier 2
    'medium',
    '{}'::jsonb,    -- 默认空分类
    '{}'::jsonb,    -- 默认空关键词
    0.0,            -- 默认语义分
    'unknown',      -- 默认健康状态
    false,          -- 默认关闭自动分级（避免刚恢复就乱跳）
    0, 0, 0, 0, false -- 计数器归零
FROM posts_raw
GROUP BY subreddit
ON CONFLICT (name) DO NOTHING;

-- 2. 恢复 Community Cache (带水位线)
-- 计算每个社区的“最大时间”作为水位线
INSERT INTO community_cache (
    community_name, 
    last_seen_created_at, 
    last_seen_post_id, 
    last_crawled_at, 
    total_posts_fetched,
    created_at,
    updated_at,
    crawl_frequency_hours,
    quality_tier
)
SELECT 
    pr.subreddit,
    MAX(pr.created_at), -- 水位线：该社区最新的帖子创建时间
    (ARRAY_AGG(pr.source_post_id ORDER BY pr.created_at DESC))[1], -- 对应的 ID
    MAX(pr.fetched_at), -- 上次抓取时间
    COUNT(*),           -- 总帖数
    NOW(),
    NOW(),
    6,                  -- 默认频率 6小时
    'tier2'
FROM posts_raw pr
GROUP BY pr.subreddit
ON CONFLICT (community_name) DO UPDATE SET
    last_seen_created_at = EXCLUDED.last_seen_created_at,
    last_seen_post_id = EXCLUDED.last_seen_post_id,
    last_crawled_at = EXCLUDED.last_crawled_at,
    total_posts_fetched = EXCLUDED.total_posts_fetched;

COMMIT;
