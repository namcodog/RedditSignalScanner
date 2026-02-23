# Phase 26 - SOP v3 对齐为“可执行现状版” + run_id 升级落地（零破坏）

日期：2025-12-17  
代码基线：以当前仓库代码为准（不改任何现有业务数据）

## 一句话结论

把 `docs/sop/数据抓取系统SOP_v3.md` 改成**跟现在代码/数据库口径一致、SQL 能直接跑**的版本；同时补上缺失的 `run_id`：**新写入的 `posts_raw` 会在 `metadata` 里带上 `run_id`**，方便对账与排查。

---

## 统一反馈（大白话 5 问）

### 1）发现了什么问题/根因？
- SOP v3 里有几处关键口径跟现实现不一致（比如用 `ttl_seconds` 算“到期”、按表字段 `run_id` 查产出）。
- 现实现里 `posts_raw` 没有 `run_id` 列，导致 SOP 的 “按 run_id 对账” 在现库跑不起来。

### 2）是否已精确定位？
- 已定位到三处“真相源头”：
  - 到期调度口径：`backend/app/services/community_pool_loader.py:get_due_communities`（用 `last_crawled_at + crawl_frequency_hours`）
  - 增量抓取入口：`backend/app/tasks/crawler_task.py:_crawl_seeds_incremental_impl`
  - 冷库写入点：`backend/app/services/incremental_crawler.py:_upsert_to_cold_storage`（写入 `posts_raw.metadata`）

### 3）精确修复方法？
- 文档层（不改结构）：把 SOP 里“会误导执行”的部分改成现状口径，并把 Runbook SQL 改成现库可执行（尤其是 run_id 那条）。
- 实现层（零破坏升级）：
  - 每次增量抓取批次生成一个 `run_id`（UUID），在日志与返回值里可见。
  - 新写入的 `posts_raw` 会把 `run_id` 写进 `metadata`（`metadata->>'run_id'`）。
  - 不改历史数据；不依赖数据库迁移；不会影响现有正常业务读写。

### 4）下一步做什么？
- 你恢复 `Celery beat + worker` 后，新的入库数据就会自动带 `run_id`，可以按 SOP Runbook 的 SQL 做对账。
- 如果后面你想更“硬核”（更快查、更强约束）：再考虑把 `run_id` 升级成专用列并加索引（需要单独评估锁表/维护窗口）。

### 5）这次修复的效果是什么？达到了什么结果？
- SOP v3 现在是“照着就能跑”的，不会再出现“文档写了但库里没这个字段”的尴尬。
- 新增的 run_id 能把一次批次写入的帖子串起来，排查“哪一轮出了问题”会非常快。

---

## 我做了哪些改动（文件级）
- SOP 对齐：`docs/sop/数据抓取系统SOP_v3.md`
- run_id 落地：
  - `backend/app/tasks/crawler_task.py`（生成 `run_id` 并传递给增量抓取器）
  - `backend/app/services/incremental_crawler.py`（写入 `posts_raw.metadata.run_id`；兼容 mocks 返回值）
- 测试先行：
  - `backend/tests/services/test_incremental_crawler_run_id.py`

## 我跑过的验证命令
- `cd backend && PYTEST_RUNNING=1 DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner_test pytest -q tests/services/test_incremental_crawler_run_id.py`

