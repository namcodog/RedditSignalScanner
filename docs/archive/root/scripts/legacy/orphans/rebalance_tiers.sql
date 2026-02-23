-- Tier Rebalancing & Final Audit Report
-- Date: 2025-12-02
-- Objective: Update tiers based on real data and export full landscape.

BEGIN;

-- 1. Auto-update Tiers based on 90-day volume
WITH stats AS (
    SELECT 
        subreddit, 
        COUNT(*) as cnt 
    FROM posts_raw 
    WHERE created_at > NOW() - INTERVAL '90 days' 
    GROUP BY subreddit
)
UPDATE community_pool c
SET tier = CASE 
    WHEN s.cnt > 500 THEN 'high'
    WHEN s.cnt > 100 THEN 'medium'
    ELSE 'low'
END,
updated_at = NOW()
FROM stats s
WHERE c.name = s.subreddit;

-- 2. Set default 'low' for communities with NO data in 90 days (Zombies)
UPDATE community_pool
SET tier = 'low'
WHERE name NOT IN (
    SELECT DISTINCT subreddit FROM posts_raw WHERE created_at > NOW() - INTERVAL '90 days'
);

COMMIT;

-- 3. Export Full Landscape Report
COPY (
    SELECT 
        c.name AS subreddit,
        c.tier AS new_tier,
        -- Get Primary Category
        (
            SELECT category_key 
            FROM community_category_map m 
            WHERE m.community_id = c.id AND m.is_primary = true 
            LIMIT 1
        ) AS primary_category,
        -- Stats
        COALESCE(s.cnt, 0) AS post_count_90d,
        COALESCE(ROUND(s.avg_com, 1), 0) AS avg_comments,
        c.is_active
    FROM community_pool c
    LEFT JOIN (
        SELECT 
            subreddit, 
            COUNT(*) as cnt, 
            AVG(num_comments) as avg_com
        FROM posts_raw 
        WHERE created_at > NOW() - INTERVAL '90 days'
        GROUP BY subreddit
    ) s ON c.name = s.subreddit
    ORDER BY 
        CASE c.tier WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
        s.cnt DESC NULLS LAST
) TO STDOUT WITH CSV HEADER;
