-- 修复 Comments 表外键约束
-- 目标：移除 DEFERRABLE 属性，提升事务性能
-- 运行环境：生产库 (reddit_signal_scanner)

BEGIN;

-- 1. 删除旧的延迟约束
ALTER TABLE public.comments 
    DROP CONSTRAINT IF EXISTS fk_comments_posts_raw;

-- 2. 添加新的立即约束 (IMMEDIATE)
-- 仍然保持 ON DELETE CASCADE 以支持级联删除
ALTER TABLE public.comments 
    ADD CONSTRAINT fk_comments_posts_raw 
    FOREIGN KEY (post_id) 
    REFERENCES public.posts_raw(id) 
    ON DELETE CASCADE;

COMMIT;
