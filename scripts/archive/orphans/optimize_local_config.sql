-- 本地环境性能优化与清理脚本
-- 目标：提升复杂查询性能，清理无用插件
-- 运行环境：生产库 (reddit_signal_scanner)

BEGIN;

-- 1. 调整 work_mem (针对当前会话验证，永久生效需 ALTER SYSTEM)
-- 注意：ALTER SYSTEM 不能在事务块中运行，所以这里我们只做 Session 级验证
-- 实际执行时，我会单独跑 ALTER SYSTEM
SET work_mem = '16MB';

-- 2. 尝试移除冗余插件
-- 如果有对象依赖它（比如 default uuid_generate_v4()），DROP 会报错并回滚，这是安全的
DROP EXTENSION IF EXISTS "uuid-ossp";

-- 3. 检查是否有表依赖 pgcrypto，如果没有也移除
-- DROP EXTENSION IF EXISTS "pgcrypto"; -- pgcrypto 有时用于密码哈希，风险较高，先保留

COMMIT;
