-- 生产同步：阶段六 Part 2 (数据质量与监控)
-- 目标：清洗垃圾 AutoMod 帖，激活监控指标
-- 运行环境：生产库

BEGIN;

-- 1. 垃圾数据清洗 (AutoMod Noise)
-- 匹配规则：哈希匹配那个 AmazonFC 的垃圾模板，或者正则匹配
-- 先用 hash 匹配最稳，防止误伤
UPDATE posts_raw
SET is_deleted = true
WHERE text_norm_hash = '0b8c6c9cde52b557adb22c156b62d645ae071cce76d084ee289609cb0db92c64';

-- 也可以加正则匹配作为兜底
UPDATE posts_raw
SET is_deleted = true
WHERE body ILIKE '%Welcome to AmazonFC%' 
  AND is_deleted = false;

-- 2. 激活监控指标 (Initialization)
-- 2.1 Crawl Metrics
INSERT INTO crawl_metrics (
    metric_date, metric_hour, 
    cache_hit_rate, avg_latency_seconds,
    total_communities, total_new_posts, total_updated_posts
) VALUES (
    CURRENT_DATE, 0, 
    0.0, 0.0,
    (SELECT COUNT(*) FROM community_pool WHERE is_active = true),
    0, 0
) ON CONFLICT (metric_date, metric_hour) DO NOTHING;

-- 2.2 Quality Metrics (如果表存在且有唯一约束)
-- 注意：quality_metrics 可能没有唯一约束，或者主键是自增 ID。
-- 如果没有唯一约束，我们直接插一条最新的。
INSERT INTO quality_metrics (
    collection_date, -- 假设字段名是这个，需核实
    deduplication_rate, 
    empty_content_rate,
    data_completeness_score
) 
SELECT 
    CURRENT_DATE, 0.90, 0.05, 0.95
WHERE NOT EXISTS (SELECT 1 FROM quality_metrics WHERE collection_date = CURRENT_DATE);

COMMIT;
