# Phase 248 - Round 1 深层修复落地（状态机 / 评论入库 / 调度兜底）

执行时间: 2026-03-13

## 1. 发现了什么

- Round 1 真正要修的不是“except 太多”这种表面问题，而是 3 条会把链路弄歪的深层问题：
  - `crawl_execute_task.py`：关键状态写库失败会被吞掉，外面看到成功，库里未必真成功。
  - `comments_ingest.py`：评论入库既有 SQL 分支爆炸，也有 `post_id` 关联失败时整批静默丢弃的问题。
  - `crawler_task.py`：调度层把一部分真实异常伪装成“正常没抢到锁 / 正常回退”，日志不够。
- 这三块本质上都是“模块职责不清”：
  - 任务执行层本来应该负责**状态机一致性**；
  - 评论入库层本来应该负责**按 schema 明确写入或明确告警**；
  - 调度层本来应该负责**兜底，但不能吞错不留痕**。
- 参考了异步 SQLAlchemy 的通用最佳实践后，确认这轮最稳的方向是：
  - 统一事务边界；
  - 失败就 rollback；
  - 关键失败不能伪装成 success；
  - 吞掉异常时至少要有明确日志。

## 2. 是否需要修复

- 需要，已经落地。
- 这轮不是做局部补丁，而是把 3 个模块的边界重新收清楚：
  - `comments_ingest.py`：SQL 生成统一收口，FK 失败显式告警。
  - `crawl_execute_task.py`：状态流转统一走 helper，关键失败 fail-closed。
  - `crawler_task.py`：调度保留兜底，但所有吞错点补日志。

## 3. 精确修复方法

### 3.1 `backend/app/services/crawl/comments_ingest.py`

- 删除 12 个手写 `COMMENT_UPSERT_SQL_*` 常量，改成参数化 SQL 生成器：
  - `_build_comment_upsert_sql(...)`
  - `_build_comment_upsert_params(...)`
- 模块内新增统一 logger。
- `post_id` 解析失败时不再静默 `return 0`，现在会打 WARNING：
  - 查帖子失败：记录 lookup failed
  - 查不到帖子：记录 skipped batch because post_id resolution failed
- 作者 upsert 继续保持 best-effort，但也统一走模块 logger。

### 3.2 `backend/app/tasks/crawl_execute_task.py`

- 新增统一状态写入 helper：
  - `_rollback_session_quietly`
  - `_commit_session`
  - `_apply_session_change`
  - `_set_target_failed`
  - `_set_target_partial`
  - `_set_target_completed`
  - `_load_community_blacklist_status`
- 黑名单检查失败改成 fail-closed：
  - 以前：异常后继续执行
  - 现在：直接把 target 标成 `failed/blacklist_check_failed`
- 最终完成态写库失败不再假装成功：
  - 以前：`complete_crawler_run_target()` 失败但函数还能返回 success
  - 现在：明确返回 `failed/complete_persist_failed`
- partial / timeout / budget exhausted 这些分支的补偿目标、回滚、提交，也统一进 helper，减少复制逻辑。
- 顺手把补偿队列的测试口径补齐：
  - `backfill_posts` 补偿走 `backfill_posts_queue_v2`
  - `patrol` / `budget_exhausted` 仍走 `compensation_queue`

### 3.3 `backend/app/tasks/crawler_task.py`

- 新增统一吞错日志 helper：
  - `_log_swallowed_exception`
  - `_rollback_with_warning`
  - `_commit_with_warning`
- advisory lock 获取/释放失败现在会有 warning，不再伪装成普通竞争。
- 几个 planner / dispatch / comment_sync 分支里原先的静默 `pass` 改成：
  - 记录 warning
  - 必要时 rollback
  - 尽量保留主流程兜底
- 目标不是让调度层“完全不容错”，而是让它“容错但可观测”。

### 3.4 测试层一起收口

- `test_comments_ingest_service.py`
  - 新增 SQL builder 缓存与 flag 驱动测试
  - 新增 `post_id` 失败显式日志测试
  - `idempotent` 用例改成使用真实存在的 `posts_raw` 父帖子，避免手搓假数据不符合库内真实规则
- `test_execute_target_task.py`
  - 新增黑名单 fail-closed 测试
  - 新增完成态落库失败返回 failed 测试
  - 补齐补偿队列口径与 `community_cache` 测试隔离
- `test_crawler_fallback.py`
  - 新增 planner lock 失败日志测试
  - 把 fallback 测试替身补齐到当前计划构建链路

## 4. 验证结果

- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/services/crawl/test_comments_ingest_service.py -q`
  - `4 passed`
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/tasks/test_execute_target_task.py -q`
  - `18 passed`
- `cd backend && SKIP_DB_RESET=1 python -m pytest tests/tasks/test_crawler_fallback.py -q`
  - `2 passed`
- `SKIP_DB_RESET=1 make test-quality-gate`
  - `24 passed`

说明：
- `pytest.ini` 里还存在老警告：`Unknown config option: asyncio_default_fixture_loop_scope`
- 这是仓库现有噪音，不是本轮引入的问题。

## 5. 这次执行的价值

- 这轮把 Round 1 从“发现问题”推进到了“链路行为被测试锁死”的状态。
- 更重要的是，模块之间的协作口径被收清楚了：
  - 评论入库层只负责把数据按 schema 正确落下，落不下就明确告警；
  - 任务执行层只负责把状态机结果说真话，不能再假成功；
  - 调度层只负责兜底和下单，但任何异常都要留痕。
- 这更接近我们要的工程目标：
  - 各模块职责清楚
  - 通过统一接口协同
  - 彼此少牵连
  - 整条链路顺畅可控
