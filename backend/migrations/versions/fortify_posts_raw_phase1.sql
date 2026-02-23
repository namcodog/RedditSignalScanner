-- Operation: Fortify Posts Raw (Phase 1)
-- 1. Create Quarantine Table
-- 2. Add Community ID & Score Lineage to Posts Raw
-- 3. Update Trigger for Quarantine & Lineage

BEGIN;

-- ==========================================
-- 1. Create Quarantine Table (The Dark Room)
-- ==========================================
CREATE TABLE IF NOT EXISTS public.posts_quarantine (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) DEFAULT 'reddit' NOT NULL,
    source_post_id VARCHAR(100) NOT NULL,
    subreddit VARCHAR(100),
    title TEXT,
    body TEXT,
    author_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    rejected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reject_reason TEXT,
    original_payload JSONB -- Store full raw data for future reprocessing
);

COMMENT ON TABLE public.posts_quarantine IS '小黑屋：存储被触发器拦截的低质量/不合规内容 (Ghost/Short/Blocked)';

-- ==========================================
-- 2. Enhance Posts Raw (The Fortress)
-- ==========================================

-- 2.1 Add Community ID (The Link)
ALTER TABLE public.posts_raw 
ADD COLUMN IF NOT EXISTS community_id INTEGER;

-- Create Index for the new link
CREATE INDEX IF NOT EXISTS idx_posts_raw_community_id ON public.posts_raw(community_id);

-- Backfill Community ID (Connect the wires)
-- UPDATE public.posts_raw pr
-- SET community_id = cp.id
-- FROM public.community_pool cp
-- WHERE lower(pr.subreddit) = lower(cp.name)
--   AND pr.community_id IS NULL;

-- 2.2 Add Score Lineage (The Audit Trail)
ALTER TABLE public.posts_raw 
ADD COLUMN IF NOT EXISTS score_source VARCHAR(50),
ADD COLUMN IF NOT EXISTS score_version INTEGER DEFAULT 1;

COMMENT ON COLUMN public.posts_raw.score_source IS '打分来源: rule_vX, ai_gemini_vX, manual';
COMMENT ON COLUMN public.posts_raw.score_version IS '打分规则版本号';

-- ==========================================
-- 3. Update Trigger (The New Gatekeeper)
-- ==========================================

CREATE OR REPLACE FUNCTION public.trg_func_auto_score_posts() RETURNS trigger
    LANGUAGE plpgsql
    AS $_$
DECLARE
    title_text TEXT := COALESCE(NEW.title, '');
    body_text TEXT := COALESCE(NEW.body, '');
    full_text TEXT := title_text || ' ' || body_text;
    meta JSONB := COALESCE(NEW.metadata, '{}'::jsonb);
    pool_id INTEGER;
BEGIN
    -- ===========================
    -- Step 0: Link Community
    -- ===========================
    -- Try to find community_id if not provided
    IF NEW.community_id IS NULL THEN
        SELECT id INTO pool_id FROM public.community_pool WHERE lower(name) = lower(NEW.subreddit);
        NEW.community_id := pool_id;
    END IF;

    -- ===========================
    -- Layer 1: 隔离 (Quarantine)
    -- ===========================
    
    -- 1.1 鬼魂/已删 (Ghost)
    IF body_text IN ('[deleted]', '[removed]') OR title_text = '' THEN
        INSERT INTO public.posts_quarantine (source, source_post_id, subreddit, title, body, author_name, reject_reason, original_payload)
        VALUES (NEW.source, NEW.source_post_id, NEW.subreddit, NEW.title, NEW.body, NEW.author_name, 'ghost_content', to_jsonb(NEW));
        RETURN NULL; -- 拦截入库
    END IF;

    -- 1.2 短内容 (Short) - < 10 chars
    IF LENGTH(full_text) < 10 THEN
        INSERT INTO public.posts_quarantine (source, source_post_id, subreddit, title, body, author_name, reject_reason, original_payload)
        VALUES (NEW.source, NEW.source_post_id, NEW.subreddit, NEW.title, NEW.body, NEW.author_name, 'short_content', to_jsonb(NEW));
        RETURN NULL; -- 拦截入库
    END IF;

    -- ===========================
    -- Layer 2/3: 打分 (Scoring)
    -- ===========================

    -- Set Lineage Info
    NEW.score_source := 'rule_v2';
    NEW.score_version := 2;

    -- 2.1 SPAM 检测 -> 0分
    IF (LENGTH(body_text) - LENGTH(REPLACE(body_text, 'http', ''))) / 4 > 2 
       OR body_text ~* 'bit\.ly|amzn\.to|t\.co|goo\.gl|tinyurl\.com'
       OR full_text ~* 'promo code|discount code|affiliate link|buy now|check out my|click here' THEN
        
        NEW.value_score := 0;
        NEW.spam_category := 'ad_auto_detected';
        NEW.business_pool := 'noise';
        RETURN NEW;
    END IF;

    -- 2.2 交易贴 (WTS) -> 6分
    IF title_text ~* '\[(WTS|WTT|WTB|S|B)\]' 
       OR title_text ~* '\b(selling|buying|trading)\b.*\b(price|usd|\$)\b' THEN
        NEW.value_score := 6;
        IF meta->>'value_tier' IS NULL THEN NEW.metadata := jsonb_set(meta, '{value_tier}', '"normal"'); END IF;
    
    -- 2.3 黄金决策 -> 7分
    ELSIF full_text ~* 'recommend|suggestion|which one|which should I| vs |versus|worth it|review|looking for|advice on' THEN
        NEW.value_score := 7;
        NEW.metadata := jsonb_set(meta, '{value_tier}', '"gold_decision"');
    
    -- 2.4 黄金痛点 -> 6分
    ELSIF full_text ~* 'how to|issue with|failed|broke|not working|help with|problem with|error|bug' THEN
        NEW.value_score := 6;
        NEW.metadata := jsonb_set(meta, '{value_tier}', '"gold_problem"');
    
    -- 2.5 价格敏感 -> 5分
    ELSIF title_text ~* '\b(price|budget|cost|worth)\b' AND title_text ~* '\$[0-9]+|[0-9]+(\s)?(usd|k)' THEN
        NEW.value_score := 5;
        IF meta->>'value_tier' IS NULL THEN NEW.metadata := jsonb_set(meta, '{value_tier}', '"normal"'); END IF;

    -- 2.6 默认 -> 3分
    ELSIF NEW.value_score IS NULL THEN
        NEW.value_score := 3;
        IF meta->>'value_tier' IS NULL THEN NEW.metadata := jsonb_set(meta, '{value_tier}', '"normal"'); END IF;
    END IF;

    -- ===========================
    -- Layer 4: 分池 (Pooling)
    -- ===========================
    
    IF NEW.value_score >= 8 THEN
        NEW.business_pool := 'core';
    ELSIF NEW.value_score <= 2 THEN
        NEW.business_pool := 'noise';
    ELSE
        NEW.business_pool := 'lab';
    END IF;

    RETURN NEW;
END;
$_$;

COMMIT;
