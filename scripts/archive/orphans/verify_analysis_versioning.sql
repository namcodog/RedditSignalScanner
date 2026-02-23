-- 验证分析表多版本支持
-- 运行环境：reddit_signal_scanner_test

BEGIN;

-- 1. 创建一个假任务
WITH new_task AS (
    INSERT INTO tasks (product_description, status, user_id)
    VALUES ('Analysis Test', 'completed', (SELECT id FROM users LIMIT 1))
    RETURNING id
)
-- 2. 插入版本 1.0
, insert_v1 AS (
    INSERT INTO analyses (id, task_id, analysis_version, insights, sources, sentiment_score, recommendation)
    SELECT 
        gen_random_uuid(), id, '1.0', '{}', '{}', 0.8, 'BUY'
    FROM new_task
)
-- 3. 插入版本 2.0 (同一个 task_id)
INSERT INTO analyses (id, task_id, analysis_version, insights, sources, sentiment_score, recommendation)
SELECT 
    gen_random_uuid(), id, '2.0', '{}', '{}', 0.5, 'HOLD'
FROM new_task;

ROLLBACK; -- 验证无误后回滚，不留垃圾数据
