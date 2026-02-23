-- 验证约束重命名后的有效性 V2
-- 运行环境：reddit_signal_scanner_test

BEGIN;

-- 1. 准备前置数据
INSERT INTO community_pool (name, tier, categories, description_keywords, semantic_quality_score)
VALUES ('r/test_constraint', 'S', '[]', '[]', 0.0)
ON CONFLICT DO NOTHING;

-- 2. 尝试触发约束违反
-- 填补所有 NOT NULL 字段，确保唯一报错源是 ttl_seconds
INSERT INTO community_cache (
    community_name, 
    ttl_seconds, 
    crawl_priority, 
    quality_tier,
    empty_hit, success_hit, failure_hit, avg_valid_posts, total_posts_fetched, crawl_quality_score
)
VALUES (
    'r/test_constraint', 
    -1,  -- 违规值
    50, 
    'S',
    0, 0, 0, 0, 0, 0.0
);

ROLLBACK;
