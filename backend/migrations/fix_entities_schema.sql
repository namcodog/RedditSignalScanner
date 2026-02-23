-- =================================================================
-- Reddit Signal Scanner - Schema Fix: Expand Entity Columns
-- Created by: David (Reddit Data Architect)
-- Date: 2025-12-11
-- Purpose: 
-- 1. Drop dependent view
-- 2. Expand content_entities columns to 255 chars
-- 3. Recreate view
-- =================================================================

BEGIN;

-- 1. Drop Dependency
DROP MATERIALIZED VIEW IF EXISTS public.mv_analysis_entities;

-- 2. Expand Columns
ALTER TABLE public.content_entities ALTER COLUMN entity TYPE VARCHAR(255);

-- 3. Recreate View
CREATE MATERIALIZED VIEW public.mv_analysis_entities AS
 SELECT p.id AS post_id,
    p.subreddit,
    p.created_at,
    e.entity AS entity_name,
    e.entity_type
   FROM (public.content_entities e
     JOIN public.posts_raw p ON ((e.content_id = p.id)))
  WHERE ((e.content_type)::text = 'post'::text)
UNION ALL
 SELECT c.id AS post_id,
    c.subreddit,
    c.created_utc AS created_at,
    e.entity AS entity_name,
    e.entity_type
   FROM (public.content_entities e
     JOIN public.comments c ON ((e.content_id = c.id)))
  WHERE ((e.content_type)::text = 'comment'::text)
WITH NO DATA;

-- 4. Re-add Indexes
CREATE INDEX idx_mv_entities_name_type ON public.mv_analysis_entities (entity_name, entity_type);
CREATE INDEX idx_mv_entities_post_id ON public.mv_analysis_entities (post_id);

COMMIT;
