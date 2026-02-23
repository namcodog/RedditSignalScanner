-- Rebuild Materialized Views to point to new content_entities/content_labels tables
-- This fixes the disconnect between extraction (Phase D) and reporting (Phase E)

-- 1. Drop old views
DROP MATERIALIZED VIEW IF EXISTS mv_analysis_entities CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_analysis_labels CASCADE;

-- 2. mv_analysis_entities (Unified Posts + Comments)
CREATE MATERIALIZED VIEW mv_analysis_entities AS
SELECT 
    p.id AS post_id,
    p.subreddit,
    p.created_at,
    e.entity AS entity_name,
    e.entity_type
FROM content_entities e
JOIN posts_raw p ON e.content_id = p.id
WHERE e.content_type = 'post'
UNION ALL
SELECT 
    c.id AS post_id,
    c.subreddit,
    c.created_utc AS created_at,
    e.entity AS entity_name,
    e.entity_type
FROM content_entities e
JOIN comments c ON e.content_id = c.id
WHERE e.content_type = 'comment';

CREATE INDEX idx_mv_entities_post_id ON mv_analysis_entities(post_id);
CREATE INDEX idx_mv_entities_name_type ON mv_analysis_entities(entity_name, entity_type);

-- 3. mv_analysis_labels (Unified Posts + Comments)
CREATE MATERIALIZED VIEW mv_analysis_labels AS
SELECT 
    p.id AS post_id,
    p.subreddit,
    p.created_at,
    p.score,
    p.num_comments,
    l.category,
    l.aspect,
    l.sentiment_label::text AS sentiment, -- Now using actual column
    l.sentiment_score,
    l.confidence
FROM content_labels l
JOIN posts_raw p ON l.content_id = p.id
WHERE l.content_type = 'post'
UNION ALL
SELECT 
    c.id AS post_id,
    c.subreddit,
    c.created_utc AS created_at,
    c.score,
    0 AS num_comments,
    l.category,
    l.aspect,
    l.sentiment_label::text AS sentiment, -- Now using actual column
    l.sentiment_score,
    l.confidence
FROM content_labels l
JOIN comments c ON l.content_id = c.id
WHERE l.content_type = 'comment';

CREATE INDEX idx_mv_labels_post_id ON mv_analysis_labels(post_id);
