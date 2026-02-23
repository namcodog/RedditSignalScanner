-- =================================================================
-- Reddit Signal Scanner - Phase D: Fix Migration Versions
-- Created by: David (Reddit Data Architect)
-- Date: 2025-12-11
-- Purpose: Extract correct model name from JSONB to distinguish AI vs Rule
-- =================================================================

BEGIN;

-- 1. 修正 AI 跑过的数据
-- 从 tags_analysis (原 metadata) 中提取 gemini_scored -> model
UPDATE public.post_scores
SET llm_version = tags_analysis->'gemini_scored'->>'model',
    rule_version = 'legacy_v1_ai'
WHERE tags_analysis->'gemini_scored' IS NOT NULL;

-- 2. 验证修正后的分布
DO $$
DECLARE
    ai_count INTEGER;
    rule_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO ai_count FROM public.post_scores WHERE rule_version = 'legacy_v1_ai';
    SELECT COUNT(*) INTO rule_count FROM public.post_scores WHERE rule_version = 'legacy_v0'; -- 剩下的就是 Rule
    
    -- 把剩下的明确标记为 legacy_rule (如果之前没标对的话，其实默认是 legacy_rule)
    UPDATE public.post_scores 
    SET llm_version = 'legacy_rule',
        rule_version = 'legacy_v1_rule'
    WHERE rule_version = 'legacy_v0';
    
    RAISE NOTICE 'Fixed Versions: AI=% (Legacy AI), Rule=% (Legacy Rule)', ai_count, rule_count;
END $$;

COMMIT;
