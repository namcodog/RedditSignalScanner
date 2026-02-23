-- =================================================================
-- Reddit Signal Scanner - Phase A: Score Archives
-- Created by: David (Reddit Data Architect)
-- Date: 2025-12-11
-- Purpose: Create the "Interpretation Layer" (Score Tables)
-- =================================================================

BEGIN;

-- 1. Create post_scores (Archive for Post Interpretations)
CREATE TABLE IF NOT EXISTS public.post_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id BIGINT NOT NULL REFERENCES public.posts_raw(id) ON DELETE CASCADE,
    
    -- Versioning (Provenance)
    llm_version VARCHAR(50) NOT NULL, -- e.g. 'gemini-1.5-flash-v1'
    rule_version VARCHAR(50) NOT NULL, -- e.g. 'rulebook_v1'
    scored_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_latest BOOLEAN DEFAULT TRUE,
    
    -- Quantitative Results (The Standard Metrics)
    value_score NUMERIC(4,2), -- 0-10, supports decimals like 8.5
    opportunity_score NUMERIC(4,2), -- 0-1
    business_pool VARCHAR(20) CHECK (business_pool IN ('core', 'lab', 'noise')),
    sentiment NUMERIC(4,3), -- -1.0 to 1.0
    purchase_intent_score NUMERIC(4,2), -- 0-1
    
    -- Qualitative Evidence (The Structured Analysis)
    tags_analysis JSONB DEFAULT '{}', -- { "main_intent": "...", "pain_tags": [], "aspect_tags": [] }
    entities_extracted JSONB DEFAULT '[]', -- [ { "name": "...", "type": "..." } ]
    calculation_log JSONB DEFAULT '{}' -- Debug info: { "base": 3, "bonus": 2 }
);

-- Indexes for post_scores
CREATE INDEX IF NOT EXISTS idx_post_scores_post_latest ON public.post_scores (post_id) WHERE is_latest = TRUE;
CREATE INDEX IF NOT EXISTS idx_post_scores_rule_version ON public.post_scores (rule_version);
CREATE INDEX IF NOT EXISTS idx_post_scores_pool ON public.post_scores (business_pool) WHERE is_latest = TRUE;


-- 2. Create comment_scores (Archive for Comment Interpretations)
CREATE TABLE IF NOT EXISTS public.comment_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id BIGINT NOT NULL REFERENCES public.comments(id) ON DELETE CASCADE,
    
    -- Versioning
    llm_version VARCHAR(50) NOT NULL,
    rule_version VARCHAR(50) NOT NULL,
    scored_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_latest BOOLEAN DEFAULT TRUE,
    
    -- Quantitative
    value_score NUMERIC(4,2), -- 0-10
    opportunity_score NUMERIC(4,2), -- 0-1
    business_pool VARCHAR(20) CHECK (business_pool IN ('core', 'lab', 'noise')),
    sentiment NUMERIC(4,3),
    purchase_intent_score NUMERIC(4,2),
    
    -- Qualitative
    tags_analysis JSONB DEFAULT '{}', -- { "actor_type": "...", "pain_tags": [] }
    entities_extracted JSONB DEFAULT '[]',
    calculation_log JSONB DEFAULT '{}'
);

-- Indexes for comment_scores
CREATE INDEX IF NOT EXISTS idx_comment_scores_comment_latest ON public.comment_scores (comment_id) WHERE is_latest = TRUE;
CREATE INDEX IF NOT EXISTS idx_comment_scores_rule_version ON public.comment_scores (rule_version);
CREATE INDEX IF NOT EXISTS idx_comment_scores_pool ON public.comment_scores (business_pool) WHERE is_latest = TRUE;

COMMIT;
