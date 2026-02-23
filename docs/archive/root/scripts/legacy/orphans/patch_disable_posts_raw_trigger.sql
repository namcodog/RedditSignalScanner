-- 临时禁用 posts_raw 的 SCD2 触发器，避免版本号被强制改写为 1 导致冲突
DROP TRIGGER IF EXISTS enforce_scd2_posts_raw ON public.posts_raw;

-- 如需恢复，执行：
-- CREATE TRIGGER enforce_scd2_posts_raw
-- BEFORE INSERT OR UPDATE ON public.posts_raw
-- FOR EACH ROW EXECUTE FUNCTION public.trg_posts_raw_enforce_scd2();
