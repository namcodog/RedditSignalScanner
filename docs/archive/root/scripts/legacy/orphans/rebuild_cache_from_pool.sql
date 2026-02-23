-- 1. 基础填充: 从 Pool 导入所有社区
INSERT INTO community_cache (
    community_name, 
    is_active, 
    crawl_priority, 
    crawl_frequency_hours,
    quality_tier
)
SELECT 
    name, 
    is_active, 
    50, -- Default Priority
    2,  -- Default Frequency (High/T1)
    'high' -- Default Tier
FROM community_pool
ON CONFLICT (community_name) DO NOTHING;

-- 2. 智能同步: 从 posts_raw 恢复抓取状态
-- 这步可能比较慢，但在 26w 数据量下应该只需要几秒

UPDATE community_cache c
SET 
    last_crawled_at = sub.max_fetched,
    last_seen_post_id = sub.last_id,
    last_seen_created_at = sub.last_created,
    total_posts_fetched = sub.post_count
FROM (
    SELECT 
        subreddit,
        MAX(fetched_at) as max_fetched,
        COUNT(*) as post_count,
        -- 获取最新的一条记录的 ID 和 Created At (Postgres 技巧)
        (ARRAY_AGG(source_post_id ORDER BY created_at DESC))[1] as last_id,
        MAX(created_at) as last_created
    FROM posts_raw
    GROUP BY subreddit
) sub
WHERE c.community_name = sub.subreddit;

-- 3. 补充统计: Success Hit (简单设为 1，表示有过成功)
UPDATE community_cache 
SET success_hit = 1 
WHERE last_crawled_at IS NOT NULL;
