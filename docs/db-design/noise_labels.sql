-- 草案：噪声标签表（示例，不可直接执行）
CREATE TABLE IF NOT EXISTS noise_labels (
    id serial PRIMARY KEY,
    content_type text NOT NULL CHECK (content_type IN ('post','comment')),
    content_id bigint NOT NULL,
    noise_type text NOT NULL CHECK (noise_type IN (
        'employee_rant','resale','bot','automod','template','spam_manual','offtopic','low_quality'
    )),
    reason text,
    created_at timestamptz DEFAULT now()
);

-- 索引：按噪声类型和目标快速查询
CREATE INDEX IF NOT EXISTS idx_noise_labels_target ON noise_labels(noise_type, content_type, content_id);
