-- Phase 2: Feature Layer Alignment & Trend Purification

BEGIN;

-- ==========================================
-- 1. Standardize Feature Tables
-- ==========================================

-- 1.1 Post Embeddings
ALTER TABLE public.post_embeddings
ADD COLUMN IF NOT EXISTS source_model VARCHAR(50) DEFAULT 'BAAI/bge-m3',
ADD COLUMN IF NOT EXISTS feature_version INTEGER DEFAULT 1;

COMMENT ON COLUMN public.post_embeddings.source_model IS '向量模型名称';
COMMENT ON COLUMN public.post_embeddings.feature_version IS '向量版本号';

-- 1.2 Content Labels
ALTER TABLE public.content_labels
ADD COLUMN IF NOT EXISTS source_model VARCHAR(50) DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS feature_version INTEGER DEFAULT 1;

COMMENT ON COLUMN public.content_labels.source_model IS '标签来源模型 (e.g. gemini-1.5-flash)';
COMMENT ON COLUMN public.content_labels.feature_version IS '标签体系版本号';

-- 1.3 Content Entities
ALTER TABLE public.content_entities
ADD COLUMN IF NOT EXISTS source_model VARCHAR(50) DEFAULT 'unknown',
ADD COLUMN IF NOT EXISTS feature_version INTEGER DEFAULT 1;

COMMENT ON COLUMN public.content_entities.source_model IS '实体抽取模型';
COMMENT ON COLUMN public.content_entities.feature_version IS '实体抽取版本号';

-- ==========================================
-- 2. Purify Trend View (No Noise)
-- ==========================================

DROP MATERIALIZED VIEW IF EXISTS public.mv_monthly_trend;

CREATE MATERIALIZED VIEW public.mv_monthly_trend AS
WITH monthly AS (
    -- Posts: Only Core & Lab
    SELECT 
        (date_trunc('month'::text, posts_raw.created_at))::date AS month_start,
        count(*) AS posts_cnt,
        (0)::bigint AS comments_cnt,
        sum(posts_raw.score) AS score_sum
    FROM public.posts_raw
    WHERE posts_raw.is_current = true
      AND posts_raw.business_pool IN ('core', 'lab') -- 🛡️ 过滤噪音
    GROUP BY ((date_trunc('month'::text, posts_raw.created_at))::date)

    UNION ALL

    -- Comments: Only those belonging to Core & Lab posts
    -- Note: This join ensures we don't count comments on spam/noise posts
    SELECT 
        (date_trunc('month'::text, c.created_utc))::date AS month_start,
        (0)::bigint AS posts_cnt,
        count(*) AS comments_cnt,
        sum(c.score) AS score_sum
    FROM public.comments c
    JOIN public.posts_raw p ON c.post_id = p.id
    WHERE p.business_pool IN ('core', 'lab') -- 🛡️ 过滤噪音
    GROUP BY ((date_trunc('month'::text, c.created_utc))::date)
), 
agg AS (
    SELECT 
        monthly.month_start,
        sum(monthly.posts_cnt) AS posts_cnt,
        sum(monthly.comments_cnt) AS comments_cnt,
        sum(monthly.score_sum) AS score_sum
    FROM monthly
    GROUP BY monthly.month_start
)
SELECT 
    agg.month_start,
    agg.posts_cnt,
    agg.comments_cnt,
    agg.score_sum,
    (agg.posts_cnt - lag(agg.posts_cnt) OVER (ORDER BY agg.month_start)) AS posts_velocity_mom,
    (agg.comments_cnt - lag(agg.comments_cnt) OVER (ORDER BY agg.month_start)) AS comments_velocity_mom,
    (agg.score_sum - lag(agg.score_sum) OVER (ORDER BY agg.month_start)) AS score_velocity_mom
FROM agg
ORDER BY agg.month_start;

-- Recreate Index
CREATE INDEX idx_mv_monthly_trend_month ON public.mv_monthly_trend USING btree (month_start);

COMMIT;
