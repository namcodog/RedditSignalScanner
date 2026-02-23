-- Fix: Align Views with New Architecture
-- 1. Purify mv_monthly_trend (Filter Core/Lab)
-- 2. Update posts_latest (Expose new columns)

BEGIN;

-- ==========================================
-- 1. Fix mv_monthly_trend (The Trend Filter)
-- ==========================================
DROP MATERIALIZED VIEW IF EXISTS public.mv_monthly_trend;

CREATE MATERIALIZED VIEW public.mv_monthly_trend AS
WITH monthly AS (
    -- Posts: Only Core & Lab (Filtered)
    SELECT 
        (date_trunc('month'::text, posts_raw.created_at))::date AS month_start,
        count(*) AS posts_cnt,
        (0)::bigint AS comments_cnt,
        sum(posts_raw.score) AS score_sum
    FROM public.posts_raw
    WHERE posts_raw.is_current = true
      AND posts_raw.business_pool IN ('core', 'lab') -- ✅ 关键修正：只看有价值数据
    GROUP BY ((date_trunc('month'::text, posts_raw.created_at))::date)

    UNION ALL

    -- Comments: Only those belonging to Core & Lab posts
    SELECT 
        (date_trunc('month'::text, c.created_utc))::date AS month_start,
        (0)::bigint AS posts_cnt,
        count(*) AS comments_cnt,
        sum(c.score) AS score_sum
    FROM public.comments c
    JOIN public.posts_raw p ON c.post_id = p.id
    WHERE p.business_pool IN ('core', 'lab') -- ✅ 关键修正：只看有价值帖子的评论
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

CREATE INDEX idx_mv_monthly_trend_month ON public.mv_monthly_trend USING btree (month_start);

-- ==========================================
-- 2. Update posts_latest (Expose New Fields)
-- ==========================================
DROP MATERIALIZED VIEW IF EXISTS public.posts_latest;

CREATE MATERIALIZED VIEW public.posts_latest AS
 SELECT 
    p.id,
    p.source,
    p.source_post_id,
    p.version,
    p.created_at,
    p.fetched_at,
    p.valid_from,
    p.valid_to,
    p.is_current,
    p.author_id,
    p.author_name,
    p.title,
    p.body,
    p.body_norm,
    p.text_norm_hash,
    p.url,
    p.subreddit,
    p.community_id,    -- ✅ New
    p.score,
    p.num_comments,
    p.is_deleted,
    p.edit_count,
    p.lang,
    p.metadata,
    p.value_score,     -- ✅ New
    p.business_pool,   -- ✅ New
    p.score_source,    -- ✅ New
    p.score_version    -- ✅ New
   FROM public.posts_raw p
  WHERE (p.is_current = true);

-- Recreate Indexes for posts_latest
CREATE INDEX idx_posts_latest_created_at ON public.posts_latest USING btree (created_at DESC);
CREATE INDEX idx_posts_latest_subreddit ON public.posts_latest USING btree (subreddit, created_at DESC);
CREATE INDEX idx_posts_latest_text_hash ON public.posts_latest USING btree (text_norm_hash);
CREATE UNIQUE INDEX idx_posts_latest_unique ON public.posts_latest USING btree (source, source_post_id);
-- Add new useful indexes
CREATE INDEX idx_posts_latest_value_pool ON public.posts_latest USING btree (business_pool, value_score DESC);

COMMIT;
