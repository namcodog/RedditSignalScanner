-- Phase C: prioritize rulebook_v1 for comment_scores safely
-- 1) Demote non-rulebook_v1 as latest when a rulebook_v1 exists for the same comment
WITH has_v1 AS (
    SELECT DISTINCT comment_id FROM comment_scores WHERE rule_version = 'rulebook_v1'
)
UPDATE comment_scores
SET is_latest = FALSE
WHERE is_latest = TRUE
  AND rule_version <> 'rulebook_v1'
  AND comment_id IN (SELECT comment_id FROM has_v1);

-- 2) Ensure rulebook_v1 rows are marked latest (idempotent)
UPDATE comment_scores
SET is_latest = TRUE
WHERE rule_version = 'rulebook_v1';

-- 3) Report remaining comments without rulebook_v1 (for re-run if needed)
\echo 'Comments missing rulebook_v1 scores:'
SELECT COUNT(*) AS missing_v1
FROM comments c
WHERE NOT EXISTS (
    SELECT 1 FROM comment_scores cs
    WHERE cs.comment_id = c.id AND cs.rule_version = 'rulebook_v1'
);
