-- Phase D retry v2: two-step to avoid partial unique conflicts

-- Step 1: clear all is_latest flags (safe because we set back right after)
UPDATE post_scores SET is_latest = FALSE WHERE is_latest = TRUE;

-- Step 2: set best row per post as latest (prefer rulebook_v1, then newest scored_at, then id)
WITH picked AS (
    SELECT DISTINCT ON (post_id)
           id
    FROM post_scores
    ORDER BY post_id,
             (rule_version = 'rulebook_v1') DESC,
             scored_at DESC NULLS LAST,
             id DESC
)
UPDATE post_scores ps
SET is_latest = TRUE
FROM picked p
WHERE ps.id = p.id;

\echo 'Posts missing rulebook_v1 scores:'
SELECT COUNT(*) AS missing_v1
FROM posts_raw p
WHERE NOT EXISTS (
    SELECT 1 FROM post_scores ps
    WHERE ps.post_id = p.id AND ps.rule_version = 'rulebook_v1'
);
