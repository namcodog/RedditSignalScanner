-- 生产同步：阶段六 (业务模型优化)
-- 目标：打通用户画像，开启分析多版本
-- 运行环境：生产库

BEGIN;

-- 1. 清洗 posts_raw.author_id
-- 把空字符串转 NULL，把 ID 转小写（如果本来就乱的话）
-- 假设 author_id 区分大小写，则不转 lower。Reddit ID (t2_xyz) 通常是 base36，建议统一。
-- 这里我们只做 NULL 清洗。
UPDATE posts_raw SET author_id = NULL WHERE author_id = '';

-- 2. 回填 authors 表
-- 从 posts_raw 提取所有还没在 authors 表里的 author_id
INSERT INTO authors (author_id, first_seen_at_global)
SELECT DISTINCT p.author_id, MIN(p.created_at)
FROM posts_raw p
LEFT JOIN authors a ON p.author_id = a.author_id
WHERE p.author_id IS NOT NULL 
  AND a.author_id IS NULL
GROUP BY p.author_id;

-- 3. 建立外键
-- 先确认没有孤儿（刚才回填了，应该没有）
ALTER TABLE posts_raw 
ADD CONSTRAINT fk_posts_raw_author 
FOREIGN KEY (author_id) REFERENCES authors(author_id);

-- 4. 升级 analyses 表
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS sentiment_score numeric(4,3);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS recommendation varchar(50);

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_analyses_sentiment ON analyses(sentiment_score);
CREATE INDEX IF NOT EXISTS idx_analyses_recommendation ON analyses(recommendation);

-- 5. 修改唯一约束 (支持多版本)
-- 先删旧约束
ALTER TABLE analyses DROP CONSTRAINT IF EXISTS uq_analyses_task_id;
-- 加新约束 (如果已存在则忽略，或者用 IF NOT EXISTS 逻辑)
-- 注意：Postgres 不支持 ADD CONSTRAINT IF NOT EXISTS，所以只能硬做
-- 如果 uq_analyses_task_version 不存在：
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_analyses_task_version') THEN
        ALTER TABLE analyses ADD CONSTRAINT uq_analyses_task_version UNIQUE (task_id, analysis_version);
    END IF;
END $$;

COMMIT;
