-- scripts/phase10_upgrade_vector_dim.sql
-- Phase 10: 向量维度升级 (Upgrade Vector Dimension)
-- 目标：将 post_embeddings 从 384 (MiniLM) 升级到 1024 (BGE-M3)
-- 前提：当前 post_embeddings 表为空，操作是瞬时的且无损的。

BEGIN;

-- 1. 删除旧索引 (必须先删索引才能改维度)
DROP INDEX IF EXISTS public.idx_post_embeddings_hnsw;

-- 2. 修改列类型 (扩容)
-- 注意：如果表里有数据，Postgres 会抛错 "column cannot be cast automatically"，
-- 除非数据已经是符合格式的。但因为表是空的，这步是安全的。
ALTER TABLE public.post_embeddings 
ALTER COLUMN embedding TYPE vector(1024);

-- 3. 更新 model_version 默认值
-- 标记新一代模型版本
ALTER TABLE public.post_embeddings 
ALTER COLUMN model_version SET DEFAULT 'BAAI/bge-m3';

-- 4. 重建 HNSW 索引
-- 针对 1024 维，适当调大 ef_construction 以保证召回率
CREATE INDEX idx_post_embeddings_hnsw 
ON public.post_embeddings 
USING hnsw (embedding public.vector_cosine_ops) 
WITH (m='16', ef_construction='128');

COMMIT;
