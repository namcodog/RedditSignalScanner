# Phase 73 - 迁移执行（测试库 -> 生产）

时间：2025-12-23

## 目标
- 按既定流程先在测试库跑迁移，再同步到生产库

## 执行结果
- 测试库：已升级到 `20251222_000004 (head)`
- 生产库：已升级到 `20251222_000004 (head)`

## 执行方式（不泄露明文）
- 测试库：从 Makefile 的 `TEST_DB_URL` 读取连接，直接 `alembic upgrade head` + `alembic current`
- 生产库：使用 `backend/.env` 的 `DATABASE_URL` 执行 `alembic upgrade head` + `alembic current`

## 迁移清单
- 20251222_000001 Update score latest views
- 20251222_000002 Add score tables
- 20251222_000003 Refresh score latest views
- 20251222_000004 Enable auto_tier_enabled by default

## 校验
- `alembic current` 显示 head

## 影响/注意
- 生产库这次从旧版本补跑到最新，属于结构/视图/默认值升级，无删表动作
