-- =================================================================
-- Reddit Signal Scanner - Schema Fix: Expand Label Columns
-- Created by: David (Reddit Data Architect)
-- Date: 2025-12-11
-- Purpose: 
-- 1. Drop dependent view
-- 2. Expand content_labels columns to 255 chars
-- 3. Recreate view
-- =================================================================

BEGIN;

-- 1. Drop Dependency
DROP MATERIALIZED VIEW IF EXISTS public.mv_analysis_labels;

-- 2. Expand Columns
ALTER TABLE public.content_labels ALTER COLUMN aspect TYPE VARCHAR(255);
ALTER TABLE public.content_labels ALTER COLUMN category TYPE VARCHAR(255);

-- 3. Recreate View
CREATE MATERIALIZED VIEW public.mv_analysis_labels AS
 SELECT p.id AS post_id,
    p.subreddit,
    p.created_at,
    p.score,
    p.num_comments,
    l.category,
    l.aspect,
    (l.sentiment_label)::text AS sentiment,
    l.sentiment_score,
    l.confidence
   FROM (public.content_labels l
     JOIN public.posts_raw p ON ((l.content_id = p.id)))
  WHERE ((l.content_type)::text = 'post'::text)
UNION ALL
 SELECT c.id AS post_id,
    c.subreddit,
    c.created_utc AS created_at,
    c.score,
    0 AS num_comments,
    l.category,
    l.aspect,
    (l.sentiment_label)::text AS sentiment,
    l.sentiment_score,
    l.confidence
   FROM (public.content_labels l
     JOIN public.comments c ON ((l.content_id = c.id)))
  WHERE ((l.content_type)::text = 'comment'::text)
WITH NO DATA;

-- 4. Re-add Index
CREATE INDEX idx_mv_labels_post_id ON public.mv_analysis_labels (post_id);

COMMIT;
