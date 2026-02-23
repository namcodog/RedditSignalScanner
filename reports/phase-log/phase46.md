# Phase 46 - System A 收口：心跳只下单（planner），执行统一走 execute_target（patrol_queue）

## 目标
- 把 System A（巡航）从“既下单又执行”拆成两段：
  - **心跳/调度（planner）**：只生成 `crawler_run_targets`（status=queued）
  - **真正抓取（executor）**：只走 `tasks.crawler.execute_target(target_id)`，并路由到 `patrol_queue`
- 让 A/B/探针共享同一套执行器、写库、cache 结账、水位线口径与 run 追踪，减少重复与分叉。

## 落地口径（Key 拍板）
- 心跳仍然负责“产生计划”，不拆散它的调度能力。
- `plan_kind=patrol`，只用增量水位线（`last_seen_*`），不碰 `backfill_floor`。
- 每条 target 必须带 `idempotency_key`，同一轮重复下单不重复插入。

## 这次做了什么
- `tick-tiered-crawl`（原 A 执行任务）改成 **planner-only**：
  - 仍然读取 community_pool/community_cache 的到期策略
  - 写入 `crawler_run_targets`：`status=queued` + `plan_kind=patrol` + `idempotency_key`
  - `config` 里存 Crawl Plan 合同，并写入 cursor 快照（`cursor_last_seen_*`）
  - 对每个新插入的 target，enqueue `tasks.crawler.execute_target(target_id)` 到 `patrol_queue`
- `crawl_low_quality_communities` 同样改成 planner-only（避免 A 还有直抓路径）。
- `CommunityPoolLoader` 读取社区池时统一跳过黑名单（`is_blacklisted=true`），避免 blocked 社区进入巡航下单。
- `ensure_crawler_run_target()` 增加返回值（bool）：告诉调用方“这次到底有没有插入新行”，用来避免重复 enqueue。

## 关键文件
- Planner（心跳）：`backend/app/tasks/crawler_task.py:569`
- 黑名单过滤：`backend/app/services/community_pool_loader.py:346`
- Executor（唯一执行入口）：`backend/app/tasks/crawl_execute_task.py:1`

## 测试证据
- 新增测试覆盖 A 的收口口径：`backend/tests/tasks/test_patrol_planner_task.py:1`
- 已跑通过（示例）：`pytest -q backend/tests/tasks/test_patrol_planner_task.py backend/tests/tasks/test_execute_target_task.py backend/tests/tasks/test_celery_beat_schedule.py`

## 下一步
- 探针（probe）按拍板口径先统一 `plan_kind=probe`，用 `config.meta.source=search/hot` 区分，并复用同一条 `execute_target` 主干。
- 把“巡航保底配额”写死（posts_limit 上限、comments 浅回填上限），防止个别大社区把 `patrol_queue` 吃满。

