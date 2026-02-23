-- scripts/phase9_fix_semantic_layer.sql
-- Phase 9: 语义层大扫除 (Semantic Hygiene) - With Timeout
-- 目标：规范化词典，清理孤儿标签

BEGIN;

SET LOCAL statement_timeout = '600s';

-- 1. 词典规范化 (Lowercase Terms)
-- A. 删除那些 "转小写后会和现有词条冲突" 的大写词条
DELETE FROM public.semantic_terms
WHERE canonical ~ '[A-Z]'
  AND LOWER(canonical) IN (SELECT canonical FROM public.semantic_terms);

-- B. 剩下的都是安全的，直接 UPDATE
UPDATE public.semantic_terms
SET canonical = LOWER(canonical)
WHERE canonical ~ '[A-Z]';

-- 2. 清理孤儿标签 (Orphaned Labels)
-- content_labels 表使用多态关联，没有硬外键，需要手动清理

-- A. 清理指向不存在帖子的标签
DELETE FROM public.content_labels
WHERE content_type = 'post'
  AND content_id NOT IN (SELECT id FROM public.posts_raw);

-- B. 清理指向不存在评论的标签
DELETE FROM public.content_labels
WHERE content_type = 'comment'
  AND content_id NOT IN (SELECT id FROM public.comments);

COMMIT;
