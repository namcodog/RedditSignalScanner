-- =================================================================
-- Reddit Signal Scanner - Comment Schema Optimization v1.0
-- Created by: David (Reddit Data Architect)
-- Date: 2025-12-11
-- Purpose: Transform comments from "storage" to "value amplifiers"
-- =================================================================

BEGIN;

-- 1. 字段改造：给评论发“身份证”
-- 添加价值分、分池、状态、语言字段
ALTER TABLE public.comments
    ADD COLUMN IF NOT EXISTS value_score SMALLINT CHECK (value_score >= 0 AND value_score <= 10),
    ADD COLUMN IF NOT EXISTS business_pool VARCHAR(10) DEFAULT 'lab' CHECK (business_pool IN ('core', 'lab', 'noise')),
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS lang VARCHAR(10);

-- 2. 索引规划：快速检索
-- 按业务分池检索（找金子）
CREATE INDEX IF NOT EXISTS idx_comments_business_pool ON public.comments (business_pool);
-- 按时间线检索（辅助分析）
CREATE INDEX IF NOT EXISTS idx_comments_subreddit_created ON public.comments (subreddit, created_utc DESC);

-- 3. TTL 分级策略：垃圾烂得快，金子永流传
-- 3.1 更新 INSERT 时的默认逻辑 (保持原状，但在 UPDATE 时会修正)
CREATE OR REPLACE FUNCTION public.set_comment_expires_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            -- 只有当没有显式指定 expires_at 时才自动计算
            IF NEW.expires_at IS NULL THEN
                NEW.expires_at := CASE
                    -- 如果一开始就有分 (极少情况)，直接应用分级策略
                    WHEN NEW.value_score >= 8 THEN NULL  -- Core: 永不过期
                    WHEN NEW.value_score <= 2 AND NEW.value_score IS NOT NULL THEN NEW.created_utc + interval '30 days' -- Noise: 30天
                    -- 默认逻辑 (基于 Reddit Score)
                    WHEN NEW.score > 100 OR NEW.awards_count > 5 THEN NEW.created_utc + interval '365 days'
                    WHEN NEW.score > 10 THEN NEW.created_utc + interval '180 days'
                    ELSE NEW.created_utc + interval '90 days'
                END;
            END IF;
            RETURN NEW;
        END;
        $$;

-- 3.2 新增 TRIGGER: 当价值分 (value_score) 变动时，自动调整 TTL
CREATE OR REPLACE FUNCTION public.adjust_comment_ttl_on_score() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        -- 只有当 value_score 发生变化时才执行
        IF NEW.value_score IS DISTINCT FROM OLD.value_score THEN
            IF NEW.value_score >= 8 THEN
                NEW.expires_at := NULL; -- 晋升 Core，永生
                NEW.business_pool := 'core';
            ELSIF NEW.value_score <= 2 THEN
                NEW.expires_at := LEAST(NEW.created_utc + interval '30 days', NOW() + interval '7 days'); -- 降级 Noise，加速腐烂
                NEW.business_pool := 'noise';
            ELSE
                -- 保持 Lab 默认或原有逻辑 (不轻易改短，防止误伤)
                -- 但确保它在 Lab 池
                NEW.business_pool := 'lab';
                -- 如果之前是无限期 (NULL)，现在降级了，给它设个期限
                IF NEW.expires_at IS NULL THEN
                    NEW.expires_at := NEW.created_utc + interval '180 days';
                END IF;
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$;

DROP TRIGGER IF EXISTS trg_adjust_ttl_on_score ON public.comments;
CREATE TRIGGER trg_adjust_ttl_on_score
    BEFORE UPDATE OF value_score ON public.comments
    FOR EACH ROW
    EXECUTE FUNCTION public.adjust_comment_ttl_on_score();


-- 4. 聚合视图：帖子的“含金量体检表”
-- 物化视图，用于快速给 Post 打分提供特征
DROP MATERIALIZED VIEW IF EXISTS public.post_comment_stats;

CREATE MATERIALIZED VIEW public.post_comment_stats AS
SELECT
    post_id,
    COUNT(*) AS comment_count,
    -- 互动质量
    AVG(score) AS avg_reddit_score,
    SUM(awards_count) AS total_awards,
    -- 深度评论 (长度 > 150 字符)
    COUNT(*) FILTER (WHERE length(body) > 150) AS long_comment_count,
    -- 提问型评论 (包含 ? 或 how/what/why 开头)
    COUNT(*) FILTER (WHERE body ~* '\?|\b(how|what|why|where)\b') AS qa_comment_count,
    -- 解决方案型评论 (包含 fixed, solution, bought, recommend, works)
    COUNT(*) FILTER (WHERE body ~* '\b(fixed|solution|solved|bought|ordered|recommend|works well|use this)\b') AS solution_comment_count,
    -- 价值分上限 (有没有大神)
    MAX(value_score) AS max_value_score,
    -- 核心评论数
    COUNT(*) FILTER (WHERE value_score >= 8) AS core_comment_count
FROM
    public.comments
GROUP BY
    post_id;

-- 给视图加唯一索引，支持并发刷新
CREATE UNIQUE INDEX idx_post_comment_stats_post_id ON public.post_comment_stats (post_id);

COMMIT;
