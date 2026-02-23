-- Automatic Scoring & Cleaning Trigger
-- 该触发器在每条新帖子插入数据库 *之前* 自动执行，
-- 确保所有新数据在落库的第一秒就已经被打分和分类。

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
    -- 1. SPAM 检测 (优先级最高)
    -- 规则: 链接堆砌 / 短链 / 推广词
    IF (LENGTH(body_text) - LENGTH(REPLACE(body_text, 'http', ''))) / 4 > 2  -- >2 links
       OR body_text ~* 'bit\.ly|amzn\.to|t\.co|goo\.gl|tinyurl\.com'
       OR full_text ~* 'promo code|discount code|affiliate link|buy now|check out my|click here' THEN
        
        NEW.value_score := 0;
        NEW.spam_category := 'ad_auto_detected';
        -- 既然是垃圾，直接返回，不再往下判断
        RETURN NEW;
    END IF;

    -- 2. 交易贴检测 (WTS - 补漏逻辑)
    -- 规则: 标题包含 [WTS] 等交易词
    IF title_text ~* '\[(WTS|WTT|WTB|S|B)\]' 
       OR title_text ~* '\b(selling|buying|trading)\b.*\b(price|usd|\$)\b' THEN
        
        NEW.value_score := 6; -- 及格线
        -- 如果没有 tier，默认为 normal
        IF meta->>'value_tier' IS NULL THEN
            NEW.metadata := jsonb_set(meta, '{value_tier}', '"normal"');
        END IF;
        RETURN NEW;
    END IF;

    -- 3. 黄金决策 (Gold Decision)
    -- 规则: 决策/对比/推荐关键词
    IF full_text ~* 'recommend|suggestion|which one|which should I| vs |versus|worth it|review|looking for|advice on' THEN
        NEW.value_score := 7;
        NEW.metadata := jsonb_set(meta, '{value_tier}', '"gold_decision"');
        RETURN NEW;
    END IF;

    -- 4. 黄金痛点 (Gold Problem)
    -- 规则: 故障/求助关键词
    IF full_text ~* 'how to|issue with|failed|broke|not working|help with|problem with|error|bug' THEN
        NEW.value_score := 6;
        NEW.metadata := jsonb_set(meta, '{value_tier}', '"gold_problem"');
        RETURN NEW;
    END IF;

    -- 5. 价格/预算敏感 (Budget)
    -- 规则: 谈钱
    IF title_text ~* '\b(price|budget|cost|worth)\b' AND title_text ~* '\$[0-9]+|[0-9]+(\s)?(usd|k)' THEN
        NEW.value_score := 5;
        IF meta->>'value_tier' IS NULL THEN
            NEW.metadata := jsonb_set(meta, '{value_tier}', '"normal"');
        END IF;
        RETURN NEW;
    END IF;

    -- 6. 默认 (Normal)
    -- 如果前面都没命中，且没有预设分数
    IF NEW.value_score IS NULL THEN
        NEW.value_score := 3;
        IF meta->>'value_tier' IS NULL THEN
            NEW.metadata := jsonb_set(meta, '{value_tier}', '"normal"');
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

-- 绑定触发器到 posts_raw 表
DROP TRIGGER IF EXISTS trg_auto_score_posts ON posts_raw;

CREATE TRIGGER trg_auto_score_posts
BEFORE INSERT ON posts_raw
FOR EACH ROW
EXECUTE FUNCTION public.trg_func_auto_score_posts();
