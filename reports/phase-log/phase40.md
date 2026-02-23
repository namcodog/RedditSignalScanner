# Phase 40 - run_id（父/子）无损落地 + SOP_v3 现状可执行版

## 目标
- **唯一原则**：不影响现有正常业务数据含义（以当前数据为准）。
- 把 “run_id” 从“日志里/metadata 里能看到”升级为**数据库可追溯、可审计、可回滚**：
  - `crawl_run_id`（父级）：一次定时触发的整轮抓取（覆盖多个社区）。
  - `community_run_id`（子级）：同一轮里某个社区的一次抓取。
- 把 `docs/sop/数据抓取系统SOP_v3.md` 调整成**按现状就能照着跑**的版本（不破坏结构）。

## 发现了什么问题/根因？
- 现状有 “run_id” 的概念，但**只在部分链路落地**（主要是 `posts_raw.metadata->>'run_id'`），`comments` 缺少稳定追踪字段。
- 另一条隐患：`_crawl_seeds_incremental_impl` 的 DB Session 生命周期不一致（先 `async with SessionFactory()` 结束后仍继续用 `db` 写 tier/metrics），属于**潜在的运行时错误点**。

## 是否已精确定位？
- 定位到主链路位置：
  - 调度入口：`backend/app/tasks/crawler_task.py`（增量心跳任务生成 `crawl_run_id`）。
  - 冷库写入：`backend/app/services/incremental_crawler.py`（`posts_raw` 写入 & metadata）。
  - 评论入库：`backend/app/services/comments_ingest.py`（comments upsert 与 run_id 兼容）。
  - 追踪表：`backend/app/services/crawler_runs_service.py`（best-effort run 记录）。

## 精确修复方法（无损/可灰度）
### 1) 数据库迁移（只加不改，不回填，不加 NOT NULL）
- 维护并加固 `crawler_runs + crawl_run_id`：
  - `backend/alembic/versions/20251215_000001_add_crawler_runs.py`
  - 改为 **不依赖 uuid-ossp**、只加 nullable 列、并用 **partial + CONCURRENTLY** 建索引（历史 NULL 行几乎不进索引，锁更小）。
- 新增子粒度 `crawler_run_targets + community_run_id`：
  - `backend/alembic/versions/20251218_000001_add_crawler_run_targets.py`
  - 新表 `crawler_run_targets` + 大表新增 `posts_raw.community_run_id` / `comments.community_run_id`（nullable），并用 partial + CONCURRENTLY 建索引。

### 2) 代码链路落地（best-effort，不阻塞主流程）
- 新增服务：`backend/app/services/crawler_run_targets_service.py`
  - best-effort 写入/完成/失败标记（表不存在就直接跳过）。
- 增量心跳任务落地父/子 run：
  - `backend/app/tasks/crawler_task.py`
  - 先 `ensure_crawler_run` 写父 run，再为每个社区生成稳定的 `community_run_id`（uuid5），写 `crawler_run_targets`，抓取结束后写 metrics。
  - 同时修正：tier/metrics 写入改用独立 Session，避免 “关闭的 session 继续使用” 风险。
- 冷库写入补齐 community_run_id：
  - `backend/app/services/incremental_crawler.py`
  - `posts_raw` 若存在列则写入 `crawl_run_id` + `community_run_id`，metadata 同步带上（便于老库排查）。
- 评论入库补齐 community_run_id：
  - `backend/app/services/comments_ingest.py`
  - schema 支持时，comments upsert 写入 `crawl_run_id` + `community_run_id`。

### 3) SOP 同步（不破坏结构）
- `docs/sop/数据抓取系统SOP_v3.md`
  - 更新成 “现状可执行版”：补充现状 run_id 落地口径 + 推荐命令（golden path / dev-celery-beat）+ 新增社区 duplicate key 时的序列修复脚本入口。

## 测试
- `pytest -q backend/tests/services/test_incremental_crawler_run_id.py backend/tests/services/test_comments_ingest_service.py backend/tests/services/test_crawler_run_targets_service.py`

## 这次修复的效果是什么？达到了什么结果？
- **不改现有业务数据口径**的前提下，把 run_id 做到“主表可索引、可追溯”，并新增了社区粒度的子 run 轨迹。
- SOP_v3 现在能按现状直接照着跑（不会再出现命令对不上代码的尴尬）。

## 下一步
- 在真实库执行 `alembic upgrade heads`（会跑 CONCURRENTLY 索引，建议观察日志与耗时）。
- 启动 `make dev-celery-beat` 或 `make dev-golden-path` 跑一轮，验证：
  - `posts_raw/comments` 新增行带 `crawl_run_id/community_run_id`
  - `crawler_runs/crawler_run_targets` 有对应记录
  - 需要回滚时可按 `crawl_run_id` 精确删除本轮写入

