# Phase 70 - 评分视图口径统一（仅 is_latest）

时间：2025-12-22

## 目标
- 让 post_scores_latest_v / comment_scores_latest_v 只用 is_latest 选最新，避免 rule_version 混用
- 兼容旧视图列顺序，避免 CREATE OR REPLACE VIEW 报错

## 变更
- update_score_latest_views 迁移：按现有视图列顺序生成 SQL，仅移除 rule_version 过滤
- 兼容逻辑：若现存视图含 id 列则保留 id+is_latest 版本，否则走旧列顺序
 - 新增迁移：20251222_000002_add_score_tables（补齐 post_scores/comment_scores 表与索引）
 - 新增迁移：20251222_000003_refresh_score_latest_views（按现有视图列类型重建视图）
 - create_score_tables.sql：索引改为 IF NOT EXISTS，支持重复执行

## 验证
- python -m pytest backend/tests/models/test_score_latest_views.py
  - 结果：失败（post_scores / comment_scores 表不存在，UndefinedTableError）
 - python -m pytest backend/tests/models/test_score_latest_views.py
   - 结果：通过（2 passed）

## 执行
- 已在测试库执行 backend/migrations/create_score_tables.sql

## 风险/说明
- 测试库未建评分表会导致此用例无法验证；需先补齐 post_scores/comment_scores 表
