-- Layer 2: Documentation & Tagging (Fixed Version)
-- Wrapped in DO block for safety

-- Part 1: 立规矩 (Schema Comments) - 这个可以直接跑，不用包在 DO 块里
COMMENT ON COLUMN public.posts_raw.spam_category IS 
'Layer 2 降噪标签: 记录广告/垃圾类型。
枚举值示例: 
- ad_link_farm: 链接堆砌 (http > 2)
- ad_keywords: 包含折扣/推广词 (promo, affiliate)
- ad_short_url: 包含短链/追踪链 (bit.ly, amzn.to)
- ad_seeded: 疑似种草文/软广 (emojis + links)
- null: 正常内容';

COMMENT ON COLUMN public.posts_raw.metadata IS 
'JSONB 扩展字段。
关键 Key 定义:
- value_tier (Layer 2 提纯):
  - gold_decision: 决策/对比/选品 (worth it, vs, recommend)
  - gold_problem: 痛点/具体问题 (how to, issue, fail)
  - gold_product: 提及具体品牌/参数
  - normal: 普通/待定 (默认)';

-- Part 2: 干活 (Tagging Logic) - 包在 DO 块里
DO $$
DECLARE
    count_ads_link INTEGER;
    count_ads_short INTEGER;
    count_ads_kw INTEGER;
    count_gold_decision INTEGER;
    count_gold_problem INTEGER;
    count_normal INTEGER;
BEGIN
    RAISE NOTICE 'Starting Layer 2 Execution...';

    -- 2.1 标记广告 (Ads) -> spam_category
    -- 规则 A: 链接农场
    UPDATE posts_raw
    SET spam_category = 'ad_link_farm'
    WHERE spam_category IS NULL
      AND (LENGTH(body) - LENGTH(REPLACE(body, 'http', ''))) / LENGTH('http') > 2;
    GET DIAGNOSTICS count_ads_link = ROW_COUNT;

    -- 规则 B: 包含短链
    UPDATE posts_raw
    SET spam_category = 'ad_short_url'
    WHERE spam_category IS NULL
      AND body ~* 'bit\.ly|amzn\.to|t\.co|goo\.gl|tinyurl\.com';
    GET DIAGNOSTICS count_ads_short = ROW_COUNT;

    -- 规则 C: 推广关键词
    UPDATE posts_raw
    SET spam_category = 'ad_keywords'
    WHERE spam_category IS NULL
      AND (title || ' ' || COALESCE(body, '')) ~* 'promo code|discount code|affiliate link|buy now|check out my|click here|limited time offer';
    GET DIAGNOSTICS count_ads_kw = ROW_COUNT;

    RAISE NOTICE '✅ Ads Tagged: LinkFarm=%, ShortUrl=%, Keywords=%', count_ads_link, count_ads_short, count_ads_kw;

    -- 2.2 标记高价值 (Gold) -> metadata->value_tier
    -- 先初始化 value_tier 为 normal (如果还没设)
    UPDATE posts_raw
    SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{value_tier}', '"normal"')
    WHERE metadata->>'value_tier' IS NULL AND spam_category IS NULL;

    -- 规则 A: 决策/选品 (Gold Decision)
    UPDATE posts_raw
    SET metadata = jsonb_set(metadata, '{value_tier}', '"gold_decision"')
    WHERE spam_category IS NULL
      AND (title || ' ' || COALESCE(body, '')) ~* 'recommend|suggestion|which one|which should I| vs |versus|worth it|review|looking for|advice on';
    GET DIAGNOSTICS count_gold_decision = ROW_COUNT;

    -- 规则 B: 具体问题/痛点 (Gold Problem)
    UPDATE posts_raw
    SET metadata = jsonb_set(metadata, '{value_tier}', '"gold_problem"')
    WHERE spam_category IS NULL
      AND metadata->>'value_tier' = 'normal' -- 别覆盖 decision
      AND (title || ' ' || COALESCE(body, '')) ~* 'how to|issue with|failed|broke|not working|help with|problem with|error|bug';
    GET DIAGNOSTICS count_gold_problem = ROW_COUNT;

    RAISE NOTICE '✅ Gold Content Tagged: Decision=%, Problem=%', count_gold_decision, count_gold_problem;
    
    -- 统计剩下的 Normal
    SELECT COUNT(*) INTO count_normal FROM posts_raw WHERE metadata->>'value_tier' = 'normal' AND spam_category IS NULL;
    RAISE NOTICE 'ℹ️ Remaining Normal Content: %', count_normal;

END $$;