# Phase 25 - 数据抓取 + 数据入库“体检报告”（只读、零破坏）

日期：2025-12-17  
代码基线：`main@fbc5a89`（以当前仓库代码 + 现有数据库数据为准）

> 本期原则：**不改任何现有业务数据**。  
> 体检只做两件事：1) 把“抓取→入库”的链路讲清楚；2) 用只读 SQL 看真实数据健康状况。

---

## 一句话结论

抓取与入库主链路是通的，但当前库里有两个明显“健康问题”：
1) **过期数据堆积**（`posts_hot` / `comments` 里大量过期行没有被清理）；  
2) **抓取新鲜度停在 12/08**（看起来定时任务/Worker 没持续跑，或跑了但没落库/没清理）。

另外发现少量边缘异常：`posts_raw` 有 2 条帖子没有任何 `is_current=true` 的版本，会导致后续评论入库被跳过。

---

## 统一反馈（大白话 5 问）

### 1）发现了什么问题/根因？
- “抓取”没问题，核心风险在两点：
  - **没人打扫**：`posts_hot` / `comments` 的过期数据堆在库里，越堆越慢。
  - **跑得不连续**：从数据时间戳看，最近一次大规模抓取/入库停在 12/08。
- 边缘问题：`posts_raw` 少数帖子没有 current 版本，导致评论入库入口会直接跳过（因为找不到满足 FK 的 post_id）。

### 2）是否已精确定位？
已精确定位到“代码入口 + 数据表”：
- 抓取入口：
  - Reddit API 客户端：`backend/app/services/reddit_client.py:RedditAPIClient`
  - 增量调度任务：`backend/app/tasks/crawler_task.py:_crawl_seeds_incremental_impl`
  - 单社区抓取（热缓存 + 预览评论）：`backend/app/tasks/crawler_task.py:_crawl_single`
- 入库入口：
  - 帖子冷库/热库：`backend/app/services/incremental_crawler.py:IncrementalCrawler`
  - 评论入库：`backend/app/services/comments_ingest.py:persist_comments`
  - 社区抓取状态/水位线：`community_cache`（由增量抓取与 cache service 更新）
- 定时清理入口（代码存在，但“是否在跑”需要现场确认）：
  - `backend/app/tasks/maintenance_task.py:cleanup_expired_posts_hot_impl`
  - `backend/app/tasks/maintenance_task.py:cleanup_expired_comments_impl`
  - Celery Beat 配置：`backend/app/core/celery_app.py`（已包含 posts_hot 清理；未看到 comments 清理的 beat 计划）

### 3）精确修复方法？
本期只体检，不动数据。给到“最小风险修复路线”：
- A. 先确认定时任务是否在跑（Celery beat + 对应队列 consumer 是否在线）。
- B. **把 comments 的过期清理纳入定时计划**（目前 beat 里没有），并先做 dry-run（只统计不删除）。
- C. 对 `posts_raw` “找不到 current” 的情况，在评论入库处加一个兜底：找不到 `is_current=true` 时，退回到“最新版本”。

### 4）下一步做什么？
建议按这个顺序推进（风险从低到高）：
1. 先做运行态确认：beat 是否跑、队列是否消费、最近一次抓取/清理是否有日志与 metrics。
2. 做一次只读盘点：按表维度确认“过期量/增长量/近 24h 入库量”。
3. 再决定是否执行清理（建议低峰期），以及是否需要加兜底逻辑（不影响现有正常数据）。

### 5）这次体检的效果是什么？
- 把“抓取→入库→清理→监控”的关键链路定位清楚了。
- 用只读 SQL 把现状量化出来，后续你可以按“风险清单”逐项收敛，不会靠猜。

---

## 抓取→入库：链路图（用人话）

### 1) 抓取（拿数据）
- `RedditAPIClient` 负责请求 Reddit、限流、429 重试、超时退化为空结果。
- 调度层（Celery 任务）决定“抓哪些社区、每次抓多少、用什么排序策略”。

### 2) 入库（把数据写进表）
- 增量抓取主线（推荐）：
  - 帖子写入 **冷库 `posts_raw`**（支持版本化、保留历史）
  - 同时写入 **热库 `posts_hot`**（覆盖刷新、用于看板/快报）
  - 写 **社区水位线 `community_cache.last_seen_created_at`**（下次只抓更新的）
- 评论入库：
  - 评论写入 `comments`（按 `reddit_comment_id` 幂等 upsert）
  - 但必须先能找到 `posts_raw` 对应的 `post_id`（FK），找不到就会跳过。

### 3) 清理（把过期的删掉，库才不会越跑越慢）
- `posts_hot`：代码里有清理任务，但需要确认是否真的在跑。
- `comments`：代码里也有清理任务，但 beat 计划里没看到，**大概率不会自动跑**。

---

## 只读 SQL 体检结果（本地库 reddit_signal_scanner）

> 说明：以下为只读查询结果，未做任何删改操作。

### 1) 表体量（规模）
- `posts_raw`: 186,952
- `posts_hot`: 183,103
- `comments`: 3,681,121
- `community_pool`: 228（active=172）
- `community_cache`: 193

### 2) 新鲜度（最近一次“真入库”的时间）
- `posts_raw.max(fetched_at)`：2025-12-08
- `posts_hot.max(cached_at)`：2025-12-08
- `comments.max(captured_at)`：2025-12-08

### 3) 过期堆积（该删但没删）
- `posts_hot`：过期 182,852 / 总 183,103（几乎全过期）
- `comments`：过期 1,726,651 / 总 3,681,121
- `comments.expires_at IS NULL`：13,037（老数据/兼容遗留的概率大）

### 4) 入库一致性边缘异常
- `posts_raw` 里有 2 个帖子：所有版本都不是 current（`is_current=true` 为 0）
  - 影响：评论入库时会因为“找不到 current 的 post_id”直接跳过（数据缺口）。

### 5) 索引健康
- 发现 1 个无效索引：`idx_posts_raw_duplicate_of`（`posts_raw` 上 `indisvalid=false`）
  - 影响：相关查询可能变慢；需要 DBA 级处理（REINDEX/重建）。

---

## 风险清单（按优先级）

### P0（必须立刻确认）
1. **过期数据堆积**：`posts_hot` / `comments` 过期量巨大，说明清理链路很可能没跑起来。  
   - 后果：库越来越慢、越来越大，最终拖垮分析/报表查询。

### P1（建议尽快修）
1. **comments 清理未纳入 beat**：代码有，但定时调度里没看到。  
2. **`posts_raw` 少量无 current**：会造成评论入库的“黑洞帖子”（后续评论永远跳过）。
3. **无效索引**：需要安排修复窗口处理。

### P2（优化项，不影响正确性但影响体验/成本）
1. 热库/评论同步存在“逐条 commit”的写法（稳但慢），高峰期容易拖慢整体吞吐。  
2. 抓取异常大量被“降级为空结果”，监控如果不到位会“看起来一切正常，其实没抓到东西”。

---

## 建议的下一步（不破坏现有业务数据）

1) 先确认运行态（最关键）
- Celery beat 是否在跑？
- `cleanup_queue` / `maintenance_queue` 是否有 worker 消费？
- 最近 24h 是否有 crawl/cleanup 的日志与 metrics？

2) 把 comments 清理纳入“可控开关”
- 先加 dry-run（只统计将删除多少，不删）。
- 再在低峰期执行一次真实清理。

3) 给评论入库加“兜底找 post_id”
- 找不到 current 时，回退到 `ORDER BY version DESC` 的最新版本（只为补齐 FK，不改变旧数据）。

4) 处理无效索引
- 单独安排维护窗口（REINDEX/重建），避免锁表影响业务。

---

## 对照 `docs/sop/数据抓取系统SOP_v3.md`（符合度 + 差异）

> 结论：**方向一致，但不是 100% 按 SOP 的“检查项清单”跑的**；并且 SOP 里提到的 `run_id` 在当前 `posts_raw` 实现里并没有落地成列（所以 SOP 的那条 run_id 查询在现库直接不可用）。

### 已符合（或我这次体检已覆盖）
- **Cache-First 的核心对象一致**：`community_cache` + `posts_raw` 是主干（我也额外看了 `posts_hot` / `comments` 的过期堆积问题）。
- **抓取/入库入口定位方式一致**：我在 `## 2）是否已精确定位？` 里把“调度任务 → 抓取 client → 入库服务 → 清理任务 → beat 配置”都标了入口文件。
- **必写追踪字段（除 `run_id` 外）在现库是齐的**（只读校验）：  
  - `posts_raw.source_track / fetched_at / first_seen_at` 缺失数均为 `0`（总行数 `186,952`）。

### 不完全符合 / 缺口（需要你确认是“补 SOP 还是补实现”）
- **SOP 要求 `run_id` 关联 `crawl_metrics`**：但当前 `posts_raw` 没有 `run_id` 列，`metadata` 里也没有 `run_id`（只读校验：`metadata_has_run_id=0`）。  
  - 直接影响：SOP Runbook 的 “按 run_id 看产出” 这条 SQL 在现库不可执行。
- **SOP Runbook 的关键检查查询我在原始 phase25 里没逐条跑出来**：这次补跑了其中与现库匹配的部分（见下方“只读校验”）。
- **SOP Step 5 的 Hand-off 门禁（`v_post_semantic_tasks`）**：本次体检没有覆盖到“视图产出是否正常/堆积是否异常”这一段。

### 只读校验（按 SOP Runbook 可执行的部分）
- **检查谁在偷懒（未更新缓存）**：`community_cache.last_crawled_at < NOW()-2 days` 的社区数 = `165`（总 `193`）。  
  - `community_cache` 时间范围：`min_last_crawled_at=2025-11-13`，`max_last_crawled_at=2025-12-17`（注意：max 可能包含“新建 stub”带来的更新时间，不代表真实抓取产出）。
- **检查缓存健康度**：`avg_hits=0`、`total_empty=7`、`avg_prio=50`（整体看像是大多还停在默认值，需结合“是否有用户查询/是否有调度更新优先级逻辑”确认）。
