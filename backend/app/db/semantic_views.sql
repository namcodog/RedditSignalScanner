-- Semantic task views for exporting posts/comments to LLM/Agent pipelines
-- v_post_semantic_tasks: slice of posts_raw for semantic labeling/export
-- v_comment_semantic_tasks: slice of comments for semantic labeling/export (core posts only)

-- Helper CTEs expect supporting tables:
-- - community_roles_map: derived from community_roles.yaml (subreddit -> role)
-- - vertical_map: optional mapping subreddit -> vertical

-- View: posts ready for semantic tasks
CREATE OR REPLACE VIEW v_post_semantic_tasks AS
WITH roles AS (
    SELECT lower(subreddit) AS subreddit, role
    FROM community_roles_map
), verticals AS (
    SELECT lower(subreddit) AS subreddit, vertical
    FROM vertical_map
)
SELECT
    p.id AS post_id,
    p.source_post_id,
    p.subreddit,
    p.title,
    LEFT(p.body, 1200) AS text_for_llm,
    CASE
        WHEN p.score >= 50 THEN 'high'
        WHEN p.score >= 10 THEN 'medium'
        ELSE 'low'
    END AS score_band,
    CASE
        WHEN p.num_comments >= 50 THEN 'high'
        WHEN p.num_comments >= 5 THEN 'medium'
        ELSE 'low'
    END AS comment_band,
    r.role AS community_role,
    v.vertical AS vertical,
    p.created_at,
    p.fetched_at,
    p.lang,
    p.source_track,
    p.first_seen_at
FROM posts_raw p
LEFT JOIN roles r ON lower(p.subreddit) = r.subreddit
LEFT JOIN verticals v ON lower(p.subreddit) = v.subreddit
WHERE p.is_current = TRUE;


-- View: comments ready for semantic tasks (core posts only if present)
CREATE OR REPLACE VIEW v_comment_semantic_tasks AS
WITH hv_posts AS (
-- High-value posts from latest scores (is_latest)
    SELECT source_post_id
    FROM post_scores_latest_v
    WHERE business_pool = 'core' OR value_score >= 6
)
SELECT
    c.id AS comment_id,
    c.reddit_comment_id,
    c.source_post_id,
    c.subreddit,
    LEFT(c.body, 1200) AS text_for_llm,
    c.score,
    c.depth,
    c.created_utc,
    c.fetched_at,
    c.lang,
    c.source_track,
    c.first_seen_at
FROM comments c
WHERE c.source_post_id IN (SELECT source_post_id FROM hv_posts);
