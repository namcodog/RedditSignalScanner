-- 验证大小写约束脚本
-- 运行环境：reddit_signal_scanner_test
BEGIN;

-- 1. 尝试插入大写名字 (预期报错)
INSERT INTO community_pool (name, tier, categories, description_keywords, semantic_quality_score)
VALUES ('r/TestUpperCase', 'S', '[]', '[]', 0.0);

ROLLBACK;
