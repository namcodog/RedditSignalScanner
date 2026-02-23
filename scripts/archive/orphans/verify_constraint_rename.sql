-- 验证约束重命名后的有效性
-- 运行环境：reddit_signal_scanner_test

BEGIN;

-- 1. 准备前置数据
INSERT INTO community_pool (name, tier, categories, description_keywords, semantic_quality_score)
VALUES ('r/test_constraint', 'S', '[]', '[]', 0.0)
ON CONFLICT DO NOTHING;

-- 2. 尝试触发约束违反 (期望报错)
-- 这里的 ttl_seconds = -1 应该违反 "ck_community_cache_ttl_positive"
INSERT INTO community_cache (community_name, ttl_seconds, crawl_priority, quality_tier)
VALUES ('r/test_constraint', -1, 50, 'S');

ROLLBACK; -- 无论成功失败都回滚，保持环境干净
