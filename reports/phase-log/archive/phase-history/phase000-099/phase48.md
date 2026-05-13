# Phase 48 - P0 运营基础设施：partial 自动补偿 + 队列保底隔离 + 全局 token bucket

## 目标（Key 拍板）
在 A/B/探针都收口到 `execute_target(target_id)` 之后，系统稳定性取决于三件事：
1) **partial 怎么收尾**（自动补缺口，不靠人救火）
2) **队列资源怎么隔离**（backfill/probe 不抢巡航保底）
3) **全局配额怎么兜底**（一次大跑不把 API/DB 打爆）

## 这次做了什么
### 1) partial → 自动生成补偿 targets（不重跑老 target）
- `tasks.crawler.execute_target` 新增自动补偿逻辑：
  - 超时：标记 `partial(timeout)`，并 enqueue 一个补偿 target 到 `compensation_queue`
  - 全局配额触顶：标记 `partial(budget_exhausted)`，并 enqueue 补偿 target（带 countdown=wait_seconds）
  - 执行器返回 `status=partial`：同样落 `partial` 并生成补偿 target
- 补偿 target 具备稳定身份证：
  - `idempotency_key = hash(base_key | compensate | reason | cursor_after | missing_set_hash)`
  - `config.meta` 写入 `retry_of_target_id` / `compensation_reason` / `cursor_after` 等审计字段
- 补偿 target 永远走 `compensation_queue`（低优先级，不挤占巡航保底）。

### 2) 分页截断 → partial（cursor_remaining）
- `RedditAPIClient.fetch_subreddit_posts_by_timestamp` 返回 `(posts, cursor_after)`
- `backfill_posts_window` 如果触顶 `max_posts` 且 `cursor_after` 仍存在，则返回：
  - `status=partial`
  - `reason=cursor_remaining`
  - `cursor_after=t3_xxx`（供补偿 target 继续补）

### 3) 全局 token bucket（两桶配额）
- `RedditAPIClient` 增加 fail-fast 全局限流模式：
  - 当全局限流器返回需要等待时，直接抛 `RedditGlobalRateLimitExceeded(wait_seconds=...)`
- `execute_target` 构建两桶配额并启用 fail-fast：
  - `patrol_bucket`（默认 40%）
  - `bulk_bucket`（默认 60%：backfill + probe 共用）
  - token 不够直接走 `partial(budget_exhausted)` + 自动补偿（延迟到下个窗口再补）

### 4) 队列保底隔离（写进启动配置）
- Celery 默认队列列表加入 `compensation_queue`
- 新增标准启动脚本：
  - `backend/start_celery_worker_patrol.sh`：只监听 `patrol_queue`
  - `backend/start_celery_worker_bulk.sh`：监听 bulk 队列（不含 `patrol_queue`）
  - `backend/start_celery_beat.sh`：只跑调度
- Makefile 增加快捷命令：`make start-workers-isolated`

## 关键文件
- partial/补偿 targets：`backend/app/tasks/crawl_execute_task.py:1`
- 全局配额异常：`backend/app/services/reddit_client.py:19`
- backfill 分页截断 partial：`backend/app/services/incremental_crawler.py:502`
- backfill 执行器 cursor 透传：`backend/app/services/crawl/execute_plan.py:12`
- Celery 队列：`backend/app/core/celery_app.py:27`
- 启动脚本：`backend/start_celery_worker_patrol.sh:1`、`backend/start_celery_worker_bulk.sh:1`、`backend/start_celery_beat.sh:1`
- SOP 更新：`docs/sop/数据抓取系统SOP_v3_修正版_v3.2.md:109`

## 测试证据
- 已跑通过（示例）：
  - `pytest -q backend/tests/tasks/test_execute_target_task.py`
  - `pytest -q backend/tests/services/test_reddit_client_fail_fast_global_limiter.py`
  - `pytest -q backend/tests/services/test_backfill_posts_window_partial_truncation.py`

## 下一步
- 在 probe 闭环落地前，确认 `discovered_communities/evaluator` 的字段口径与入池策略（自动 backfill 30 天 + 配额上限）。
