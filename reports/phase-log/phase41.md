# Phase 41 - 真实库无损迁移上线（run_id 父/子落地 + 序列修复生效）

## 背景与前提
- 用户已完成真实数据库备份（本阶段默认备份可用）。
- 迁移目标库：`localhost:5432 / reddit_signal_scanner`（非 `_test`）。
- 原则：**不影响现有正常业务数据含义**，只做“加表/加列/加索引/修序列/建视图”的无损变更。

## 1）发现了什么问题/根因？
- 首次执行 `alembic upgrade heads` 失败，报错：
  - `cannot drop columns from view`
- 根因：真实库里已存在 `post_scores_latest_v`，且列集合包含 `id`、`is_latest`。
  - 我们迁移脚本里 `CREATE OR REPLACE VIEW post_scores_latest_v` 的新定义缺少这两列，Postgres 不允许用 OR REPLACE “删列/改列集合”。
- 额外副作用：因为迁移中包含 `CREATE INDEX CONCURRENTLY`（autocommit），导致：
  - `crawler_runs`、`posts_raw/comments/crawl_metrics.crawl_run_id` 以及相关索引已经落库
  - 但 `alembic_version` 仍停留在旧 revision（版本表记录回滚了）
  - 形成“**schema 已变更，但版本号没跟上**”的记账不一致。

## 2）是否已精确定位？
- 已定位到具体迁移文件与 SQL：
  - `backend/alembic/versions/20251217_000005_add_score_read_views_and_business_comments_view.py`
  - 问题点：`post_scores_latest_v` 的列集合与真实库既有视图不兼容。

## 3）精确修复方法？
### A. 让视图迁移对真实库兼容（不 drop，不 cascade）
- 修复方式：保持 `post_scores_latest_v` 的列集合与真实库兼容（包含 `id`、`is_latest`，并保持顺序）。
- 对应修复文件：
  - `backend/alembic/versions/20251217_000005_add_score_read_views_and_business_comments_view.py`

### B. 修复 Alembic 记账（stamp）
- 由于首次失败已经让 `20251215_000001` 的核心 DDL 落库，但版本表未更新，采取：
  - `alembic stamp 20251215_000001`
- 这是纯“版本号记账修正”，不改业务数据。

## 4）下一步做什么？
- 迁移完成后恢复抓取调度：
  - `make dev-celery-beat` 或 `make dev-golden-path`
- 然后再执行新增社区（此时序列已对齐，不应再出现 duplicate key）。

## 5）这次修复的效果/结果是什么？
- 真实库已成功升级到 head：`20251218_000001 (head)`。
- run_id 父/子落库完成：
  - `crawler_runs` ✅
  - `crawler_run_targets` ✅
  - `posts_raw.crawl_run_id/community_run_id` ✅
  - `comments.crawl_run_id/community_run_id` ✅
  - `crawl_metrics.crawl_run_id` ✅
- 关键视图存在：
  - `comments_core_lab_v` ✅
- 序列修复已生效（验证口径）：
  - `community_pool max(id)=1411`
  - `sequence current_next=1425`
  - `current_next > max(id)` ✅（新增社区不会再撞主键）

## 执行记录（关键命令）
- `cd backend && alembic current`
- `cd backend && alembic upgrade heads`（首次失败于视图 OR REPLACE）
- 修复视图迁移后：
  - `cd backend && alembic stamp 20251215_000001`
  - `cd backend && alembic upgrade heads`（成功）

