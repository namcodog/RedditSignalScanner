-- Step 3: 科学定级 (R-F-E Model)
-- 目标：根据真实数据重新计算社区等级

BEGIN;

-- 1. 计算各社区的核心指标
WITH metrics AS (
    SELECT 
        subreddit,
        -- R: 新鲜度 (最近30天是否有贴)
        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 days') as posts_30d,
        -- F: 活跃度 (最后一次发帖时间)
        MAX(created_at) as last_active,
        -- E: 互动质量 (平均评论数)
        COALESCE(AVG(num_comments), 0) as avg_interaction
    FROM posts_raw
    GROUP BY subreddit
),
tier_calc AS (
    SELECT 
        p.id,
        p.name,
        p.created_at,
        m.posts_30d,
        m.last_active,
        m.avg_interaction,
        CASE 
            -- A. 保护新导入的社区 (创建不足7天)
            WHEN p.created_at > NOW() - INTERVAL '7 days' AND m.posts_30d IS NULL THEN 'medium' -- 默认给 T2 试跑
            
            -- B. 僵尸判定：有数据但超过60天没动静 -> T3 (不再归档，只是降低频率)
            WHEN m.last_active < NOW() - INTERVAL '60 days' THEN 'low'
            
            -- C. T1 (High) 判定：
            --    标准1: 日均 > 5贴 (30天 > 150)
            --    标准2: 日均 > 2贴 且 互动极高 (>20评论)
            WHEN m.posts_30d > 150 OR (m.posts_30d > 60 AND m.avg_interaction > 20) THEN 'high'
            
            -- D. T2 (Medium) 判定：
            --    标准: 日均 > 1贴 (30天 > 30)
            WHEN m.posts_30d > 30 THEN 'medium'
            
            -- E. 剩下的就是长尾 T3 (Low)
            ELSE 'low'
        END as new_tier
    FROM community_pool p
    LEFT JOIN metrics m ON p.name = m.subreddit
    WHERE p.tier != 'archived' -- 不处理已归档的
)
-- 2. 执行更新
UPDATE community_pool p
SET 
    tier = c.new_tier,
    updated_at = NOW()
FROM tier_calc c
WHERE p.id = c.id 
  AND p.tier != c.new_tier; -- 只更新变动的

-- 3. 输出统计报告
DO $$
DECLARE
    updated_count INT;
BEGIN
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Step 3 完成: 已根据数据重新定级 % 个社区。', updated_count;
END $$;

COMMIT;
