-- scripts/phase6_backfill_authors.sql
-- Phase 6: 户籍警 (The Census) - Retry with extended timeout
-- 目标：解决用户孤岛问题，回填 Authors 表并建立外键

BEGIN;

-- 临时增加超时时间至 5 分钟，防止大表全量扫描超时
SET LOCAL statement_timeout = '300s';

-- 1. 确保 authors 表存在 (防止表缺失)
CREATE TABLE IF NOT EXISTS public.authors (
    author_id VARCHAR(100) PRIMARY KEY,
    author_name VARCHAR(100),
    created_utc TIMESTAMPTZ,
    is_bot BOOLEAN DEFAULT false NOT NULL,
    first_seen_at_global TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 2. 回填数据：从 posts_raw 提取所有尚未登记的作者
-- 使用 ON CONFLICT DO NOTHING 保证幂等性
INSERT INTO public.authors (author_id, author_name, first_seen_at_global)
SELECT DISTINCT author_id, author_name, MIN(created_at)
FROM public.posts_raw
WHERE author_id IS NOT NULL 
  AND author_id != ''
  AND author_id NOT IN (SELECT author_id FROM public.authors)
GROUP BY author_id, author_name
ON CONFLICT (author_id) DO NOTHING;

DO $$
BEGIN
    RAISE NOTICE 'Phase 6: Authors 表回填完成';
END $$;

-- 3. 建立外键约束 (如果尚未建立)
DO $$
BEGIN
    -- 检查外键是否存在，不存在则添加
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_posts_raw_author'
    ) THEN
        ALTER TABLE public.posts_raw 
            ADD CONSTRAINT fk_posts_raw_author 
            FOREIGN KEY (author_id) 
            REFERENCES public.authors(author_id) 
            ON DELETE SET NULL;
        RAISE NOTICE 'Phase 6: 外键 fk_posts_raw_author 已建立';
    ELSE
        RAISE NOTICE 'Phase 6: 外键 fk_posts_raw_author 已存在，跳过';
    END IF;
END $$;

COMMIT;
