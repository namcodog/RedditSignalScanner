-- Automatic Scoring & Cleaning Trigger (v2 - With Pools)
-- 包含：自动打分 + 自动分池 (Core/Lab/Noise)

CREATE OR REPLACE FUNCTION public.trg_func_auto_score_posts()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    title_text TEXT := COALESCE(NEW.title, '');
    body_text TEXT := COALESCE(NEW.body, '');
    full_text TEXT := title_text || ' ' || body_text;
    meta JSONB := COALESCE(NEW.metadata, '{}'::jsonb);
BEGIN
    -- ===========================
    -- Phase 1: 打分 (Scoring)
    -- ===========================

    -- 1. SPAM 检测 (优先级最高)
    IF (LENGTH(body_text) - LENGTH(REPLACE(body_text, 'http', ''))) / 4 > 2 
       OR body_text ~* 'bit\.ly|amzn\.to|t\.co|goo\.gl|tinyurl\.com'
       OR full_text ~* 'promo code|discount code|affiliate link|buy now|check out my|click here' THEN
        
        NEW.value_score := 0;
        NEW.spam_category := 'ad_auto_detected';
        -- 这里的 return 需要注意，如果 return 了，后面的 pool 逻辑也要能处理
        -- 既然 score 已经是 0，直接在这里定池子最快
        NEW.business_pool := 'noise';
        RETURN NEW;
    END IF;

    -- 2. 交易贴 (WTS) -> 6分
    IF title_text ~* '\[(WTS|WTT|WTB|S|B)\]' 
       OR title_text ~* '\b(selling|buying|trading)\b.*\b(price|usd|\$)\b' THEN
        NEW.value_score := 6;
        IF meta->>'value_tier' IS NULL THEN NEW.metadata := jsonb_set(meta, '{value_tier}', '"normal"'); END IF;
        -- 继续往下走去定池子，不要 return
    
    -- 3. 黄金决策 -> 7分
    ELSIF full_text ~* 'recommend|suggestion|which one|which should I| vs |versus|worth it|review|looking for|advice on' THEN
        NEW.value_score := 7;
        NEW.metadata := jsonb_set(meta, '{value_tier}', '"gold_decision"');
    
    -- 4. 黄金痛点 -> 6分
    ELSIF full_text ~* 'how to|issue with|failed|broke|not working|help with|problem with|error|bug' THEN
        NEW.value_score := 6;
        NEW.metadata := jsonb_set(meta, '{value_tier}', '"gold_problem"');
    
    -- 5. 价格敏感 -> 5分
    ELSIF title_text ~* '\b(price|budget|cost|worth)\b' AND title_text ~* '\$[0-9]+|[0-9]+(\s)?(usd|k)' THEN
        NEW.value_score := 5;
        IF meta->>'value_tier' IS NULL THEN NEW.metadata := jsonb_set(meta, '{value_tier}', '"normal"'); END IF;

    -- 6. 默认 -> 3分
    ELSIF NEW.value_score IS NULL THEN
        NEW.value_score := 3;
        IF meta->>'value_tier' IS NULL THEN NEW.metadata := jsonb_set(meta, '{value_tier}', '"normal"'); END IF;
    END IF;

    -- ===========================
    -- Phase 2: 分池 (Pooling)
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
$$;

-- 重新绑定
DROP TRIGGER IF EXISTS trg_auto_score_posts ON posts_raw;

CREATE TRIGGER trg_auto_score_posts
BEFORE INSERT ON posts_raw
FOR EACH ROW
EXECUTE FUNCTION public.trg_func_auto_score_posts();
