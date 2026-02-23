-- 验证分析表多版本支持 V2
-- 运行环境：reddit_signal_scanner_test

BEGIN;

-- 0. 确保有一个用户
INSERT INTO users (id, username, email, password_hash)
VALUES ('00000000-0000-0000-0000-000000000001', 'tester', 'test@example.com', 'hash')
ON CONFLICT DO NOTHING;

-- 1. 创建一个假任务 (显式指定 ID)
INSERT INTO tasks (id, user_id, product_description, status)
VALUES ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'Analysis Test', 'completed');

-- 2. 插入版本 1.0
INSERT INTO analyses (id, task_id, analysis_version, insights, sources, sentiment_score, recommendation)
VALUES (gen_random_uuid(), '00000000-0000-0000-0000-000000000002', '1.0', '{}', '{}', 0.8, 'BUY');

-- 3. 插入版本 2.0 (同一个 task_id) - 如果约束还在，这里会报错
INSERT INTO analyses (id, task_id, analysis_version, insights, sources, sentiment_score, recommendation)
VALUES (gen_random_uuid(), '00000000-0000-0000-0000-000000000002', '2.0', '{}', '{}', 0.5, 'HOLD');

ROLLBACK;
