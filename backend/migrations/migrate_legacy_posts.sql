-- =================================================================
-- Reddit Signal Scanner - Phase D: Legacy Post Migration
-- Created by: David (Reddit Data Architect)
-- Date: 2025-12-11
-- Purpose: 
-- 1. Move ALL existing post scores (AI & Rule) to post_scores table.
-- 2. Mark them as 'legacy_v0'.
-- =================================================================

BEGIN;

-- 1. 迁移数据
-- 我们把 posts_raw 里所有已经有分数的 (value_score IS NOT NULL) 搬家
INSERT INTO public.post_scores (
    post_id,
    llm_version,
    rule_version,
    scored_at,
    is_latest,
    value_score,
    opportunity_score,
    business_pool,
    sentiment,
    purchase_intent_score,
    tags_analysis,
    entities_extracted,
    calculation_log
)
SELECT
    id as post_id,
    -- 如果 metadata 里有 model 字段，说明是 AI 跑的，否则标记为 legacy_rule
    COALESCE(metadata->>'model', 'legacy_rule') as llm_version,
    'legacy_v0' as rule_version,
    NOW() as scored_at,
    TRUE as is_latest, -- 暂时都是最新的
    value_score,
    -- 只有 AI 跑过的可能有 metadata->>'opportunity_score'，否则给默认值 0
    COALESCE((metadata->>'opportunity_score')::numeric, 0) as opportunity_score,
    business_pool,
    0 as sentiment, -- 旧数据没存这个
    0 as purchase_intent_score, -- 旧数据没存这个
    -- 把旧的 metadata 暂时存进 tags_analysis 备查
    metadata as tags_analysis,
    '[]'::jsonb as entities_extracted,
    '{"source": "migration"}'::jsonb as calculation_log
FROM
    public.posts_raw
WHERE
    value_score IS NOT NULL;

-- 2. 验证迁移数量
DO $$
DECLARE
    moved_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO moved_count FROM public.post_scores WHERE rule_version = 'legacy_v0';
    RAISE NOTICE 'Migrated % posts to post_scores (legacy_v0).', moved_count;
END $$;

COMMIT;
