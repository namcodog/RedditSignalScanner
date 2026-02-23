# Phase 50 - P0 探针输入端（probe_search v1）：证据帖落库 + 候选社区幂等 upsert + 队列隔离

## 目标（Key 的口径）
把探针做成“纯输入层”：
- 只产 `evidence_posts` + `discovered_communities`
- 不碰 `community_cache` 水位线
- 不直接触发回填（回填仍然只由 evaluator 的 approved 触发）
- 幂等去重：同一 query 重跑不刷爆 DB

## 这次做了什么
### 1) 新增证据帖表 `evidence_posts`（可审计资产）
- 新表：`evidence_posts`
- 去重键写死：`(probe_source, source_query_hash, source_post_id)`

### 2) probe_search 执行器接入统一执行入口
- `execute_crawl_plan` 支持 `plan_kind=probe`（先实现 search；hot 暂不接）
- 执行时：
  - 调 Reddit search 拿 TopN 帖子
  - 写 `evidence_posts`
  - upsert `discovered_communities`（按 `name=r/<slug>` 唯一键）
  - 写死限额：`max_evidence_posts` / `max_discovered_communities`
  - 超限返回 `partial(caps_reached)`，用于运营可观测

### 3) 探针不自动补偿（防止越补越大）
- `execute_target`：当 `plan_kind=probe` 时，任何 `partial` 都不自动生成补偿 targets

### 4) 队列隔离：probe_queue 独立 worker
- 新增 `backend/start_celery_worker_probe.sh`（只监听 `probe_queue`，默认并发 1）
- Bulk worker 默认不再监听 `probe_queue`（避免探针挤占 backfill）
- `make start-workers-isolated` 现在会额外启动 probe worker

## 关键文件
- 证据帖表迁移：`backend/alembic/versions/20251218_000003_add_evidence_posts_table.py:1`
- 模型：`backend/app/models/evidence_post.py:1`
- 执行器：`backend/app/services/crawl/execute_plan.py:1`
- Planner（下单 + 入队）：`backend/app/tasks/probe_task.py:1`
- probe 不补偿：`backend/app/tasks/crawl_execute_task.py:300`
- 队列脚本：`backend/start_celery_worker_probe.sh:1`、`backend/start_celery_worker_bulk.sh:1`
- Makefile：`Makefile:150`
- SOP 更新：`docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md:270`

## 测试证据
- 建议验收命令（已补测试覆盖）：
  - `pytest -q backend/tests/services/test_probe_search_executor.py`
  - `pytest -q backend/tests/tasks/test_probe_planner_task.py`
  - `pytest -q backend/tests/tasks/test_execute_target_task.py`

## 下一步
- 在 probe_search 稳定后再上 probe_hot：
  - 继续复用同一套 evidence_posts + discovered_communities upsert
  - 入口必须“受控热源”+ 硬限额（避免一夜灌满无关社区）

