# Phase 45 - 唯一执行入口落地：execute_target(target_id=crawler_run_targets.id)

## 目标
- 把“执行入口”收口成一个：`tasks.crawler.execute_target(target_id)`。
- `target_id` 口径钉死：就是 `crawler_run_targets.id`（避免 community_run_id/切片映射歧义）。
- 回填脚本（System B）改成真正的 Planner：只写 `crawler_run_targets.config`（计划合同）+ enqueue 执行，不再自己执行抓取。

## 这次做了什么
- 新增唯一执行入口：
  - `tasks.crawler.execute_target(target_id)` 会从 `crawler_run_targets.config` 读 Crawl Plan 合同并执行。
  - 已完成的 target（status=completed）会直接跳过，避免重复抓取/重复写库。
- 回填脚本改造为“先落计划、后执行”：
  - `backend/scripts/crawl_incremental.py`、`backend/scripts/crawl_comprehensive.py`
    - 先写 `crawler_run_targets`（status=queued，config=Plan）
    - 再 enqueue `tasks.crawler.execute_target` 到 `backfill_queue`
- 修复一个隐藏坑：Plan config 里有 datetime 时，`json.dumps()` 会炸
  - 统一改成 `plan.model_dump(mode="json")` 写入 `crawler_run_targets.config`（确保可 JSON 序列化）
- Celery 路由补齐：
  - `tasks.crawler.execute_target` 默认路由到 `crawler_queue`（实际由 planner 按 plan_kind 选择 queue 更稳）

## 变更文件（核心）
- `backend/app/tasks/crawl_execute_task.py`
- `backend/app/tasks/__init__.py`
- `backend/app/core/celery_app.py`
- `backend/scripts/crawl_incremental.py`
- `backend/scripts/crawl_comprehensive.py`
- `backend/app/tasks/crawler_task.py`
- `backend/app/tasks/backfill_task.py`
- `backend/app/tasks/ingest_task.py`
- `backend/tests/tasks/test_execute_target_task.py`

## 测试证据
- `pytest -q backend/tests/tasks/test_execute_target_task.py backend/tests/tasks/test_celery_beat_schedule.py backend/tests/migrations/test_community_cache_waterlines.py backend/tests/migrations/test_crawler_run_targets_plan_identity.py backend/tests/services/test_semantic_rules_contract.py`

## 下一步
- 探针仍按拍板口径：`plan_kind=probe` + `meta.source in {search, hot}`，后续把 probe 也接入 `execute_target`（证据帖 + discovered_communities）。
- 自动 backfill 30 天的“额度上限”要写死（posts_limit<=300 + comments 只对 Top20 浅回填），避免大社区把队列吃光。

