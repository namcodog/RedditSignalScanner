-- scripts/phase6_clean_automod_garbage.sql
-- Phase 6: 垃圾数据清洁工 (The Janitor)
-- 目标：软删除由 AutoMod 产生的无价值帖子，净化 AI 语义库

BEGIN;

DO $$
DECLARE
    cleaned_count integer;
BEGIN
    -- 执行软删除 (Soft Delete)
    UPDATE public.posts_raw
    SET is_deleted = true,
        metadata = jsonb_set(COALESCE(metadata, '{}'), '{deletion_reason}', '"automod_noise"')
    WHERE is_deleted = false
      AND (
        body ILIKE 'Welcome to r/%'          -- 典型欢迎语
        OR body ILIKE '%I am a bot, and this action was performed automatically%' -- 通用Bot签名
        OR author_name = 'AutoModerator'     -- 明确的Bot账号
      );

    GET DIAGNOSTICS cleaned_count = ROW_COUNT;
    RAISE NOTICE 'Phase 6: 已清理 % 条 AutoMod 垃圾数据', cleaned_count;
END $$;

COMMIT;
