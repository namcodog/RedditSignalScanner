-- AI 基础设施建设
-- 目标：启用 Vector 扩展，创建 Embedding 表和 HNSW 索引
-- 运行环境：生产库 (reddit_signal_scanner)

BEGIN;

-- 1. 启用扩展 (如果尚未启用)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 创建 Embedding 表 (垂直分表)
CREATE TABLE IF NOT EXISTS public.post_embeddings (
    post_id BIGINT NOT NULL,
    model_version VARCHAR(50) NOT NULL DEFAULT 'all-MiniLM-L6-v2',
    embedding vector(384), -- 384维，适配本地轻量模型
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 联合主键：同一个帖子即使有多个模型版本，每个版本也只能有一条
    CONSTRAINT pk_post_embeddings PRIMARY KEY (post_id, model_version),
    
    -- 外键关联：主表删除时，Embedding 自动清理
    CONSTRAINT fk_embeddings_post FOREIGN KEY (post_id) 
        REFERENCES public.posts_raw(id) ON DELETE CASCADE
);

-- 3. 创建 HNSW 索引 (高性能向量检索)
-- 使用 vector_cosine_ops (余弦相似度)，m=16, ef_construction=64 是推荐的平衡参数
CREATE INDEX IF NOT EXISTS idx_post_embeddings_hnsw 
    ON public.post_embeddings USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

COMMIT;
