-- =================================================================
-- Reddit Signal Scanner - Comment Cleaning & Scoring Rules v1.0
-- Created by: David (Reddit Data Architect)
-- Date: 2025-12-11
-- Purpose: 
-- 1. Deploy Trigger for future comments (Gatekeeper)
-- 2. Backfill existing 5M+ comments (Janitor)
-- =================================================================

-- ⚠️ SAFETY: Disable timeouts for this heavy migration
SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';

BEGIN;

-- =================================================================
-- Part 1: Define the Scoring Logic (Reusable Function)
-- =================================================================

CREATE OR REPLACE FUNCTION public.calculate_comment_basic_score(body_text text) 
RETURNS smallint
LANGUAGE plpgsql IMMUTABLE
AS $$
DECLARE
    score smallint := 2; -- 基础分
BEGIN
    IF body_text IS NULL THEN
        RETURN 0;
    END IF;

    -- Rule 1: 话痨奖励 (>150 chars) -> +1
    IF length(body_text) > 150 THEN
        score := score + 1;
    END IF;

    -- Rule 2: 解决方案奖励 (Solution Keywords) -> +2
    IF body_text ~* '\b(fixed|solution|solved|bought|ordered|recommend|works well|use this|try this)\b' THEN
        score := score + 2;
    END IF;

    -- Rule 3: 提问奖励 (Question Keywords) -> +1
    IF body_text ~* '\?|\b(how|what|why|where|does anyone)\b' THEN
        score := score + 1;
    END IF;

    -- Cap at 5 (Max heuristic score)
    IF score > 5 THEN
        score := 5;
    END IF;

    RETURN score;
END;
$$;

-- =================================================================
-- Part 2: The Trigger (Future Data Gatekeeper)
-- =================================================================

CREATE OR REPLACE FUNCTION public.trg_func_auto_clean_comments() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    DECLARE
        calc_score smallint;
    BEGIN
        -- Layer 1: 扫地 (Hygiene)
        -- 1.1 显性垃圾
        IF NEW.body ~* '^\[(deleted|removed)\]$' OR NEW.body IS NULL THEN
            NEW.business_pool := 'noise';
            NEW.value_score := 0;
            NEW.is_deleted := TRUE;
            RETURN NEW;
        END IF;

        -- 1.2 短文本
        IF length(NEW.body) < 10 THEN
            NEW.business_pool := 'noise';
            NEW.value_score := 0;
            RETURN NEW;
        END IF;

        -- 1.3 垃圾关键词 (Spam)
        IF NEW.body ~* '\b(promo code|coupon|discount|affiliate|click here|whatsapp)\b' THEN
            NEW.business_pool := 'noise';
            NEW.value_score := 0;
            RETURN NEW;
        END IF;

        -- Layer 2: 算分 (Heuristic Scoring)
        calc_score := public.calculate_comment_basic_score(NEW.body);
        NEW.value_score := calc_score;

        -- Layer 3: 分池 (Pooling)
        IF calc_score >= 4 THEN
            -- 高分 -> Lab 候选 (High Potential)
            NEW.business_pool := 'lab';
        ELSIF calc_score >= 1 THEN
            -- 普通 -> Lab (Normal)
            NEW.business_pool := 'lab';
        ELSE
            -- 低分 -> Noise
            NEW.business_pool := 'noise';
        END IF;

        RETURN NEW;
    END;
    $$;

DROP TRIGGER IF EXISTS trg_clean_comments_on_insert ON public.comments;
CREATE TRIGGER trg_clean_comments_on_insert
    BEFORE INSERT ON public.comments
    FOR EACH ROW
    EXECUTE FUNCTION public.trg_func_auto_clean_comments();


-- =================================================================
-- Part 3: The Backfill (Historical Data Janitor)
-- Only processing rows that haven't been scored yet (value_score IS NULL)
-- =================================================================

-- 3.1 批量标记垃圾 (Noise Sweep)
UPDATE public.comments
SET business_pool = 'noise',
    value_score = 0,
    is_deleted = (body ~* '^\[(deleted|removed)\]$')
WHERE value_score IS NULL
  AND (
      body ~* '^\[(deleted|removed)\]$' 
      OR length(body) < 10
      OR body ~* '\b(promo code|coupon|discount|affiliate|click here|whatsapp)\b'
  );

-- 3.2 批量打分 (Scoring)
-- 对剩下的 (value_score IS NULL) 进行打分
UPDATE public.comments
SET value_score = public.calculate_comment_basic_score(body)
WHERE value_score IS NULL;

-- 3.3 批量分池 (Pooling)
-- 根据刚刚打的分数入池
UPDATE public.comments
SET business_pool = CASE 
        WHEN value_score >= 4 THEN 'lab'
        WHEN value_score >= 1 THEN 'lab'
        ELSE 'noise'
    END
WHERE (business_pool IS NULL OR business_pool = 'lab') -- 仅处理未分类或默认为lab的
  AND value_score IS NOT NULL; -- 确保已有分数

COMMIT;
