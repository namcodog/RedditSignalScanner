-- Safe patch: ensure no is_latest before insert, then insert rulebook_v1 for target posts.

-- Target posts missing rulebook_v1
WITH target_posts AS (
    SELECT unnest(ARRAY[745525, 785709, 786001]) AS post_id
),
latest_source AS (
    -- pick the most recent existing score per target post as template
    SELECT DISTINCT ON (ps.post_id)
        ps.*
    FROM post_scores ps
    JOIN target_posts t ON t.post_id = ps.post_id
    ORDER BY ps.post_id, ps.scored_at DESC NULLS LAST, ps.id DESC
),
demote AS (
    UPDATE post_scores
    SET is_latest = FALSE
    WHERE post_id IN (SELECT post_id FROM target_posts)
    RETURNING 1
)
INSERT INTO post_scores (
    post_id, llm_version, rule_version, scored_at, is_latest,
    value_score, opportunity_score, business_pool, sentiment,
    purchase_intent_score, tags_analysis, entities_extracted, calculation_log
)
SELECT
    ls.post_id,
    COALESCE(ls.llm_version, 'legacy'),
    'rulebook_v1',
    NOW(),
    TRUE,
    ls.value_score,
    ls.opportunity_score,
    ls.business_pool,
    ls.sentiment,
    ls.purchase_intent_score,
    ls.tags_analysis,
    ls.entities_extracted,
    ls.calculation_log
FROM latest_source ls
ON CONFLICT DO NOTHING;

-- Ensure only rulebook_v1 is_latest for targets
UPDATE post_scores
SET is_latest = FALSE
WHERE post_id IN (745525, 785709, 786001)
  AND rule_version <> 'rulebook_v1';

UPDATE post_scores
SET is_latest = TRUE
WHERE post_id IN (745525, 785709, 786001)
  AND rule_version = 'rulebook_v1';
