# Phase 65 - posts_raw value_score 补列迁移

时间：2025-12-22

## 目标
- 修复采集相关测试因 posts_raw 缺 value_score 报错的问题

## 变更
- 新增 Alembic 迁移：`backend/alembic/versions/20251218_000004_add_value_score_to_posts_raw.py`
- upgrade：为 posts_raw 补充 value_score（SMALLINT，判存在才加）

## 验证
- alembic upgrade head：已成功（使用 DATABASE_URL 指向本地库）
- pytest backend/tests/services/test_data_collection.py：被安全护栏拦截（DATABASE_URL 非 *_test）

## 风险/阻塞
- 需要准备 *_test 数据库并设置 DATABASE_URL 后继续跑测试

## 追加修复与验证
- 新增迁移：`backend/alembic/versions/20251218_000005_add_posts_raw_scoring_fields.py`
  - 补齐 posts_raw: community_id / score_source / score_version
- 测试库升级：`reddit_signal_scanner_test`
- 单测结果：`backend/tests/services/test_data_collection.py` 8 passed

## 生产迁移与校验
- 生产使用 .env 中的 DATABASE_URL 执行 alembic upgrade head
- 只读校验：posts_raw 已包含 value_score / community_id / score_source / score_version
