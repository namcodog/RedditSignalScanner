-- Layer 3: Value Scoring - Step 1 (SQL Catch-up)
-- 目标：把 Normal (3分) 里明显的交易/强意图帖子捞到 6 分

BEGIN;

-- 规则 1: 显性交易贴 (WTS/WTT)
-- 特征：标题包含 [WTS], [WTT], [Selling], [Buying]
UPDATE posts_raw
SET value_score = 6
WHERE value_score = 3
  AND (
      title ~* '\[(WTS|WTT|WTB|S|B)\]'  -- 匹配 [WTS], [WTT], [S], [B]
      OR title ~* '\b(selling|buying|trading)\b.*\b(price|usd|\$)\b' -- 标题同时包含买卖动作和钱
  );

-- 规则 2: 强烈的价格敏感 (Price/Budget)
-- 特征：标题明确问价格/预算，且包含具体数字
UPDATE posts_raw
SET value_score = 5 -- 给个 5 分，比 6 分稍低，交给 LLM 决定能不能上 8
WHERE value_score = 3
  AND title ~* '\b(price|budget|cost|worth)\b'
  AND title ~* '\$[0-9]+|[0-9]+(\s)?(usd|k)';

COMMIT;
