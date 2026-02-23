# Phase 44 - Crawl Plan 收口第一波（idempotency_key + backfill_floor + last_attempt_at）

## 目标
- 把抓取入口开始收口：巡航/补数/离线入库统一走 “Crawl Plan 合同 + 统一执行器” 的口径。
- 避免 A/B 互相踩：补数要能推进回填底线；失败/中断只记录尝试时间，不误推进成功游标。
- 脚本降级：脚本只负责“下单/入队”，不再直接写库。
- 队列分流：巡航永远不被大回填挤死（patrol/backfill/probe 分队列）。

## 发现了什么问题/根因？
- `crawler_run_targets` 之前的唯一约束是 `(crawl_run_id, subreddit)`，导致“按时间窗切片回填”天然跑不起来：同一社区的多片计划会被卡死，追踪也会丢。
- 缺少“计划身份证”（幂等键）：同一计划重复 enqueue 时，无法做到可控去重与可审计重跑。
- `community_cache` 缺少回填底线与尝试时间：补数跑完 A 不知道；失败/中断又可能误影响调度判断。
- `semantic_rules` 的列名口径不统一（代码读 `pattern`，DB 实际是 `term`），导致语义回流/探针扩展“表面跑了，实际命中 0”。

## 是否已精确定位？
- 是，集中在 `community_cache` / `crawler_run_targets` 的字段与约束缺口，以及语义关键词 SQL 读取列名错误、计划缺少幂等键与分队列策略缺失。

## 精确修复方法？
- **DB 迁移（第一波收口迁移）**
  - `community_cache` 新增：`backfill_floor`（回填底线）、`last_attempt_at`（尝试时间）。
  - `crawler_run_targets` 新增：`plan_kind`、`idempotency_key`、`idempotency_key_human`。
  - 删除旧 UNIQUE：`uq_crawler_run_targets_run_subreddit`。
  - 新增 partial UNIQUE index：`(crawl_run_id, idempotency_key)`（仅当 `idempotency_key IS NOT NULL`）。
- **Plan 合同 + 统一执行器**
  - 新增 `CrawlPlanContract`（按 `plan_kind` 做校验）+ `compute_idempotency_key()`。
  - 新增 `execute_crawl_plan()`：把巡航/回填的执行逻辑收敛到同一处。
  - 巡航任务与回填任务改为调用统一执行器（减少“同一件事三套跑法”）。
- **水位线别名层（避免散写 last_seen_*）**
  - `community_cache_service` 新增：
    - `mark_crawl_attempt()` → 失败/中断只写 `last_attempt_at`
    - `update_incremental_waterline_if_forward()` → 增量水位线只前进
    - `update_backfill_floor_if_lower()` → 回填底线只往更老推进
- **脚本降级（只 enqueue）**
  - `backend/scripts/crawl_incremental.py` / `crawl_comprehensive.py` / `ingest_jsonl.py` 改为只生成切片计划并派发 Celery 任务，不再直写库。
- **语义回流列名对齐**
  - `CommunityDiscoveryService._fetch_pain_keywords_from_db()` 统一读取 `semantic_rules.term`（并修正 SQL：`GROUP BY term` + `ORDER BY MAX(weight)`）。
- **队列分流**
  - `celery_app` 增加 `patrol_queue/backfill_queue/probe_queue`，并将心跳/低质量补抓路由到 `patrol_queue`，回填/离线入库路由到 `backfill_queue`。

## 下一步
- 把真正的“唯一执行入口”补齐成 Celery 任务：`tasks.crawler.execute_plan(community_run_id)`（从 `crawler_run_targets.config` 读取 plan 合同，再统一 dispatch）。
- 探针闭环第二波：`evidence_posts` + `discovered_communities` + evaluator 入池 + 自动生成 backfill 30d plan。
- 如果要更强的“水位线不回退”保障：把增量 `_update_watermark()` 也改成只前进写 `last_seen_*`（避免乱序完成导致游标回退）。

## 这次修复的效果是什么？达到了什么结果？
- 同一 `crawl_run_id` 下，同一社区可以安全存在多张回填切片计划，不会被旧唯一约束卡死。
- 回填能推进 `backfill_floor`，失败只记 `last_attempt_at`，避免 A/B 因口径不一致产生重复抓取与资源浪费。
- 语义关键词读取恢复，避免探针扩展“命中 0”。
- 巡航/回填/探针可分队列运行，巡航有保底，不容易被大回填挤死。

## 变更文件（核心）
- `backend/alembic/versions/20251218_000002_add_plan_identity_and_waterlines.py`
- `backend/app/services/crawl/plan_contract.py`
- `backend/app/services/crawl/execute_plan.py`
- `backend/app/services/community_cache_service.py`
- `backend/app/tasks/crawler_task.py`
- `backend/app/tasks/backfill_task.py`
- `backend/app/tasks/ingest_task.py`
- `backend/scripts/crawl_incremental.py`
- `backend/scripts/crawl_comprehensive.py`
- `backend/scripts/ingest_jsonl.py`
- `backend/app/services/community_discovery.py`
- `backend/app/core/celery_app.py`
- `backend/tests/migrations/test_community_cache_waterlines.py`
- `backend/tests/migrations/test_crawler_run_targets_plan_identity.py`
- `backend/tests/services/test_semantic_rules_contract.py`
- `backend/tests/tasks/test_celery_beat_schedule.py`

## 测试证据
- `pytest -q backend/tests/migrations/test_community_cache_waterlines.py backend/tests/migrations/test_crawler_run_targets_plan_identity.py backend/tests/services/test_semantic_rules_contract.py`
- `pytest -q backend/tests/tasks/test_tasks_smoke.py backend/tests/tasks/test_celery_beat_schedule.py`

