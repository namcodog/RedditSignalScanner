-- 验证分析表多版本支持 V4
-- 运行环境：reddit_signal_scanner_test

BEGIN;

-- 0. 插入用户
INSERT INTO users (id, email, password_hash, membership_level)
VALUES ('00000000-0000-0000-0000-000000000001', 'tester@example.com', 'pbkdf2_sha256$123$456', 'free')
ON CONFLICT (email) DO NOTHING;

-- 1. 创建假任务 (status='pending' 以规避 completed_at 检查)
INSERT INTO tasks (id, user_id, product_description, status)
VALUES ('00000000-0000-0000-0000-000000000002', (SELECT id FROM users WHERE email='tester@example.com'), 'Analysis Test', 'pending');

-- 2. 插入版本 1.0
INSERT INTO analyses (id, task_id, analysis_version, insights, sources, sentiment_score, recommendation)
VALUES (gen_random_uuid(), '00000000-0000-0000-0000-000000000002', '1.0', '{}', '{}', 0.8, 'BUY');

-- 3. 插入版本 2.0 (同一个 task_id)
INSERT INTO analyses (id, task_id, analysis_version, insights, sources, sentiment_score, recommendation)
VALUES (gen_random_uuid(), '00000000-0000-0000-0000-000000000002', '2.0', '{}', '{}', 0.5, 'HOLD');

ROLLBACK;
