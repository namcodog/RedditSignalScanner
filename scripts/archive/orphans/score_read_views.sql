-- 安全只读视图：统一从 *_scores 获取当前有效版本
CREATE OR REPLACE VIEW post_scores_latest_v AS
SELECT post_id,
       rule_version,
       llm_version,
       value_score,
       opportunity_score,
       business_pool,
       sentiment,
       purchase_intent_score,
       tags_analysis,
       entities_extracted,
       calculation_log,
       scored_at
FROM post_scores
WHERE is_latest = true
  AND rule_version = 'rulebook_v1';

CREATE OR REPLACE VIEW comment_scores_latest_v AS
SELECT comment_id,
       rule_version,
       llm_version,
       value_score,
       opportunity_score,
       business_pool,
       sentiment,
       purchase_intent_score,
       tags_analysis,
       entities_extracted,
       calculation_log,
       scored_at
FROM comment_scores
WHERE is_latest = true
  AND rule_version = 'rulebook_v1';
