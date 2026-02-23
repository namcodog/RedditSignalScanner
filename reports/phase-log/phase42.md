# Phase 42 - current_schema.sql 同步到最新真实库架构

## 目标
- 把真实库（已升级到最新迁移 head）当前架构导出到 `current_schema.sql`，作为“架构唯一事实来源”。

## 背景
- 真实库已完成无损迁移上线（见 `reports/phase-log/phase41.md`）。
- 发现 `current_schema.sql` 仍未包含新落地对象（如 `crawler_runs/crawler_run_targets`、`community_run_id`、`comments_core_lab_v`），需要同步。

## 执行
- 命令：`make db-sync-schema`
  - 本质：`pg_dump -s -d reddit_signal_scanner -U postgres -h localhost > current_schema.sql`

## 结果校验（关键对象已出现在 schema dump）
- `public.crawler_runs` ✅
- `public.crawler_run_targets` ✅
- `posts_raw.community_run_id / crawl_run_id` ✅
- `comments.community_run_id / crawl_run_id` ✅
- `public.comments_core_lab_v` ✅

