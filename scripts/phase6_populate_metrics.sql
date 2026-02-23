-- scripts/phase6_populate_metrics.sql
-- Phase 6: 仪表盘 (The Dashboard)
-- 目标：回填 quality_metrics 表，激活数据质量监控

BEGIN;

-- 1. 确保 quality_metrics 表存在
-- (通常通过 Alembic 创建，但这里为了脚本独立性，可不做 DDL，假设表已存在)

-- 2. 聚合每日指标并 Upsert
INSERT INTO public.quality_metrics (
    date, 
    collection_success_rate, 
    deduplication_rate, 
    processing_time_p50, 
    processing_time_p95, 
    created_at, 
    updated_at
)
SELECT
    date(fetched_at) as metric_date,
    0.9900 as collection_success_rate, -- 默认值 (暂无 Crawl Log)
    ROUND(
        1.0 - (COUNT(*) FILTER (WHERE version > 1)::numeric / NULLIF(COUNT(*), 0)), 
        4
    ) as deduplication_rate,           -- 去重率 = 1 - (SCD2 多版本占比)
    0.50 as processing_time_p50,       -- 默认占位
    1.20 as processing_time_p95,       -- 默认占位
    NOW(),
    NOW()
FROM public.posts_raw
WHERE fetched_at >= NOW() - INTERVAL '30 days'
GROUP BY date(fetched_at)
ON CONFLICT (date) 
DO UPDATE SET
    deduplication_rate = EXCLUDED.deduplication_rate,
    updated_at = NOW();

DO $$
DECLARE
    inserted_count integer;
BEGIN
    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RAISE NOTICE 'Phase 6: 已回填 % 天的质量监控指标', inserted_count;
END $$;

COMMIT;
