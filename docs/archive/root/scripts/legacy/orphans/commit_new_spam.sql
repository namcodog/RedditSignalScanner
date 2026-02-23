-- Final Commit: Insert newly discovered spam domains
-- 释放连接压力，使用简单 SQL

BEGIN;

-- 获取 global_filter_keywords 的 ID (假设是 4，前面查过是 global_filter_keywords)
-- 或者更稳妥地查一下
WITH concept AS (
    SELECT id FROM semantic_concepts WHERE code = 'global_filter_keywords'
)
INSERT INTO semantic_rules (concept_id, term, rule_type, weight, meta)
SELECT id, 'garlicpressseller.com', 'keyword', -0.8, '{"source": "mine_v2_domain"}'
FROM concept
ON CONFLICT (concept_id, term, rule_type) DO NOTHING;

COMMIT;
