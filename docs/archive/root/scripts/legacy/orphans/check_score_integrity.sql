-- 🏥 Integrity Check Script: Post Scores Health
-- Run this to verify Phase D migration success.

\echo '>>> 1. Checking Total Coverage (Should match)'
SELECT 
    (SELECT COUNT(*) FROM posts_raw) as total_raw_posts,
    (SELECT COUNT(*) FROM post_scores WHERE is_latest = TRUE) as latest_scores;

\echo '>>> 2. Checking Orphans (Should be 0)'
-- Any post in RAW that does not have a LATEST score
SELECT COUNT(*) as orphan_count
FROM posts_raw p
LEFT JOIN post_scores ps ON p.id = ps.post_id AND ps.is_latest = TRUE
WHERE ps.id IS NULL;

\echo '>>> 3. Checking Version Distribution'
-- We expect mostly 'rulebook_v1' now
SELECT rule_version, COUNT(*) as count
FROM post_scores
WHERE is_latest = TRUE
GROUP BY rule_version
ORDER BY count DESC;

\echo '>>> 4. Checking Data Quality'
-- Verify JSON structure exists
SELECT COUNT(*) as invalid_json_count
FROM post_scores
WHERE is_latest = TRUE
  AND (tags_analysis IS NULL OR jsonb_typeof(tags_analysis) != 'object');
