-- =================================================================
-- T1 Report Data Extraction Script
-- Target: Generate data for the 4 Decision Cards in "T1价值报告.md"
-- =================================================================

-- -----------------------------------------------------------------
-- Card 1: P/S Ratio (问题/解决方案比)
-- 目标：验证 "1.2 : 1" 这个结论
-- -----------------------------------------------------------------
WITH stats AS (
    SELECT 
        category,
        COUNT(*) as cnt
    FROM mv_analysis_labels
    WHERE category IN ('pain', 'solution', 'intent')
    GROUP BY category
)
SELECT 
    'Global P/S Ratio' as metric,
    pain.cnt as pain_count,
    sol.cnt as solution_count,
    ROUND(pain.cnt::numeric / NULLIF(sol.cnt, 1), 2) as ratio
FROM 
    (SELECT cnt FROM stats WHERE category = 'pain') pain,
    (SELECT cnt FROM stats WHERE category IN ('solution', 'intent')) sol;

-- -----------------------------------------------------------------
-- Card 2: Top Pain Points (核心痛点)
-- 目标：找出 Top 5 痛点，对应 "手续费", "冻结", "多平台"
-- -----------------------------------------------------------------
SELECT 
    aspect as pain_point,
    COUNT(*) as frequency,
    ROUND(AVG(sentiment::numeric), 2) as avg_sentiment,
    string_agg(DISTINCT subreddit, ', ') as found_in_subreddits
FROM mv_analysis_labels
WHERE category = 'pain'
GROUP BY aspect
ORDER BY frequency DESC
LIMIT 10;

-- -----------------------------------------------------------------
-- Card 3: Competitor Analysis (竞品/战场)
-- 目标：谁被讨论最多？情感如何？
-- -----------------------------------------------------------------
SELECT 
    entity_name as brand,
    entity_type,
    COUNT(*) as mentions,
    COUNT(DISTINCT subreddit) as subreddit_coverage
FROM mv_analysis_entities
WHERE entity_type IN ('brand', 'platform')
GROUP BY entity_name, entity_type
ORDER BY mentions DESC
LIMIT 10;

-- -----------------------------------------------------------------
-- Card 4: High Value Subreddits (核心战场)
-- 目标：找出痛点密度最高的社区
-- -----------------------------------------------------------------
SELECT 
    subreddit,
    COUNT(*) as total_mentions,
    COUNT(*) FILTER (WHERE category = 'pain') as pain_count,
    ROUND(COUNT(*) FILTER (WHERE category = 'pain') * 100.0 / COUNT(*), 1) as pain_density_pct
FROM mv_analysis_labels
GROUP BY subreddit
HAVING COUNT(*) > 5
ORDER BY pain_count DESC
LIMIT 5;

-- -----------------------------------------------------------------
-- Bonus: W2C Signals (求购信号)
-- 目标：找出具体的商机
-- -----------------------------------------------------------------
SELECT 
    p.subreddit,
    l.aspect as intent,
    p.title,
    p.url
FROM mv_analysis_labels l
JOIN posts_hot p ON l.post_id = p.id
WHERE l.category = 'intent' 
  AND l.aspect IN ('w2c', 'recommend')
ORDER BY p.created_at DESC
LIMIT 5;
