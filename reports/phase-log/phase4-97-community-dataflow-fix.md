# Phase 4 · 97 社区数据流修复执行记录

**创建时间**：2025-11-17  
**关联文档**：`97社区数据流修复执行方案.md`  
**涉及范围**：`community_pool` / `community_cache` / `crawler.yml` / Celery 抓取链路  

---

## 1）发现了什么问题 / 根因？

- 现状：数据库已有 `posts_raw ≈ 7.6 万条、comments ≈ 85 万条、98 个社区`，但：
  - `community_pool` 行数 = 0（社区配置中心断层）
  - `community_cache` 行数 = 0（水位线、抓取频率全部缺失）
- 根因 1：临时抓取脚本（如 `crawl_posts_from_csv.py`）绕过了 `community_pool/community_cache`，直接写业务表，只解决了“把数据抓进来”，没有走系统化数据流。
- 根因 2：回填脚本 `backfill_community_pool_from_csv_97.py` 与当前数据文件 / 表结构不一致：
  - 仍假设从 `社区分级汇总报告_基于165社区.csv` 里直接读出 97 个社区，但现在这份 CSV 只有分级汇总，没有逐社区明细 → 实际读到 0 个社区。
  - SQL 仍按老 schema 使用 `posts_raw.post_id`，但模型已经改成 `source_post_id`。
  - `CommunityCache` 模型字段从 `crawl_quality_score` 重命名为 `quality_score`，脚本未同步更新。
- 根因 3：`crawler.yml` 仍处于“历史回填模式”：
  - `watermark_enabled = false`，水位线被整体关掉。
  - 各 tier 的 `time_filter` 仍为 `"all"`，且 T3 仍按 `["low"]` 匹配，没有对 `semantic` 单独建 tier 策略。

---

## 2）是否已精确定位？

- 已精确定位到三个具体断点：
  1. **社区来源**：97 个保留社区真实来源是三张明细表  
     - `高价值社区池_基于165社区.csv`（48 个）  
     - `次高价值社区池_基于165社区.csv`（15 个）  
     - `扩展语义社区池_基于165社区.csv`（34 个）  
     而不是原来的 165 汇总表。
  2. **统计 SQL 与模型不匹配**：帖子统计应该基于 `posts_raw.source_post_id` + `created_at`，而不是不存在的 `post_id`。
  3. **缓存模型字段名变更**：`community_cache` 里的质量字段现在叫 `quality_score`（底层列名仍为 `crawl_quality_score`），脚本必须用新字段名构造 ORM 对象。

---

## 3）精确修复方法（已经落地的改动）

### 3.1 回填脚本修复（97 社区 → pool/cache）

- 修改 `backend/scripts/backfill_community_pool_from_csv_97.py`：
  - 新增三张 CSV 路径常量：  
    - `CSV_HIGH_VALUE_PATH = "高价值社区池_基于165社区.csv"`  
    - `CSV_MEDIUM_VALUE_PATH = "次高价值社区池_基于165社区.csv"`  
    - `CSV_SEMANTIC_VALUE_PATH = "扩展语义社区池_基于165社区.csv"`
  - 重写 `read_communities_from_csv()`：
    - 逐文件用 `csv.reader` 读取，跳过“说明 / 抓取策略 / 表头”行。
    - 从每行中抓取以 `r/` 开头的字段作为社区名。
    - 按中文分级标签映射到内部 tier：`高价值社区 → high`、`次高价值社区 → medium`、`扩展语义社区 → semantic`。
    - 为每个社区挂上 `CRAWL_STRATEGY` 中的抓取频率、优先级和评论策略。
  - 修复统计 SQL：
    - `COUNT(DISTINCT post_id)` → `COUNT(DISTINCT source_post_id)`。
  - 修复 `CommunityCache` 构造：
    - `crawl_quality_score=Decimal('0.50')` → `quality_score=Decimal('0.50')`。
- 新增单元测试：`backend/tests/scripts/test_backfill_community_pool_from_csv_97.py`
  - 断言：
    - 总社区数 = 97，且社区名全部以 `r/` 开头且无重复。
    - tier 分布为：`high=48`、`medium=15`、`semantic=34`。
  - 已通过：`pytest backend/tests/scripts/test_backfill_community_pool_from_csv_97.py -q`。
- 实际执行回填脚本：
  - 命令：`python backend/scripts/backfill_community_pool_from_csv_97.py`
  - 关键输出（最终一次）：
    - `community_pool 总数: 97 / 活跃: 97`
    - `community_cache 总数: 84 / 有水位线: 84`
    - 按 tier：`high=48, medium=15, semantic=34`。
  - SQL 验证：
    - `SELECT COUNT(*) FROM community_pool;` → 97  
    - `SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE last_seen_created_at IS NOT NULL) AS with_watermark FROM community_cache;` → `84 / 84`。
  - 说明：  
    - 当前 `posts_raw` 中只有 84 个社区与 97 个保留社区有交集，其余 13 个社区仍是“尚未在 posts_raw 留痕的新社区”，因此脚本按设计跳过 cache 初始化，等系统首次抓取时再自然生成，这一点与文档预期的 98 有差异，已经在此记录。

### 3.2 评论回填链路的数据库锁与事务修复（新增，2025-11-18）

- 新发现的问题（本次事故）：
  - 运行 `backfill_comments_for_posts.py` 大规模回填评论时，出现：
    - 多次 `Timeout while processing post` 日志；
    - 多次 `Can't reconnect until invalid transaction is rolled back` 错误；
    - PostgreSQL 侧观测到：
      - ~90 个事务等待 `transactionid` 锁；
      - 多个连接处于 `idle in transaction` / `idle in transaction (aborted)` 状态；
      - 最终触发 `FATAL: sorry, too many clients already`。
  - 根因定位：
    - `backend/scripts/backfill_comments_for_posts.py` 中：
      - 每个帖子处理时使用 `asyncio.wait_for(...)` 做总超时保护，但触发 `TimeoutError` 后只打印日志，没有对当前 `AsyncSession` 进行 `rollback`；
      - 被 `wait_for` 取消的协程在数据库侧可能已经进入“事务 aborted”状态（持有 transactionid 锁），后续对同一连接的任何 SQL 都会报 “当前事务已中止”，直到手动 rollback；
    - 多个 Celery 任务/抓取任务在写 `comments` 表时：
      - 使用“长事务 + 循环内多次 `persist_comments` + 末尾统一 `session.commit()`”模式；
      - 当某一条帖子在循环中触发异常时，只记录 warning，不做 `session.rollback()`，导致整个事务处于 aborted 状态继续向后走；
      - 在高并发（多 Worker、多脚本并行）的情况下，极易堆积大量“等待某个 transactionid 锁”的事务，形成严重锁竞争甚至死锁前兆。

- 已落地的系统性修复：
  1. 超时场景强制 rollback（脚本）  
     - 文件：`backend/scripts/backfill_comments_for_posts.py`  
     - 改动：
       - 在 per-post 超时处理分支中，补充显式的 `await session.rollback()`：
         - 触发 `TimeoutError` 时，立即释放当前事务持有的锁并重置连接状态；
         - 避免后续 SQL 再次命中 “Can't reconnect until invalid transaction is rolled back”。
     - 影响范围：
       - 所有通过 `backfill_comments_for_posts.py` 执行的大规模评论回填任务；
       - 尤其是高价值/次高价值社区的历史补抓场景。

  2. Celery 评论回填任务的短事务化（每帖独立提交）  
     - 文件：`backend/app/tasks/comments_task.py`  
     - 改动：
       - `comments.backfill_full`：
         - 原逻辑：`for pid in source_post_ids: ...` 循环内多次 `persist_comments` + NLP 标注，最后统一 `await session.commit()`；
         - 新逻辑：
           - 每成功处理一个帖子后立刻 `await session.commit()`，缩短单次事务生命周期；
           - 在 `except Exception` 分支中显式 `await session.rollback()`，清理 aborted 状态；
       - `comments.backfill_recent_full_daily`：
         - 对每个帖子成功处理后立即 `commit`，出错时 `rollback` 并跳过该帖；
       - `comments.backfill_high_value_full`：
         - 为每个帖子添加“成功后 commit、异常时 rollback”的保护，避免高价值社区批量抓取时形成长事务。

  3. 在线抓取链路中的评论同步事务收缩  
     - 文件：`backend/app/tasks/crawler_task.py`  
     - 改动：
       - 在 `_crawl_single` 的“可选评论同步”阶段：
         - 之前：`async with SessionFactory() as db:` + 循环内多次 `persist_comments`，最后统一 `await db.commit()`；
         - 现在：
           - 每个帖子：
             - 成功抓取并写入评论后立即 `await db.commit()`；
             - 任何异常（包括数据库错误）都会触发一次 `await db.rollback()`，然后仅跳过当前帖子；
       - 这样可以最大限度避免“长事务 + 高并发”叠加，减少 `comments` 上的锁竞争。

- 自检与验证（本次修复）：
  - 新增测试：`backend/tests/scripts/test_backfill_comments_for_posts_timeout.py`  
    - 模拟 `asyncio.wait_for` 立即抛出 `TimeoutError`，并用 FakeSession 统计 `rollback` 调用次数；
    - 断言：在出现 `Timeout while processing post` 的路径下，至少执行一次 `session.rollback()`。
  - 手工验证建议（运维执行）：
    1. 启动一轮小规模回填（例如：单社区、page_size=50），观察：
       - 是否还出现 “Can't reconnect until invalid transaction is rolled back”；
       - `pg_stat_activity` 中是否存在长时间 `idle in transaction (aborted)` 连接；
       - `pg_locks` 中的 `transactionid` 锁数量是否稳定在较低水平。
    2. 再逐步放大批量规模（多社区、多 Worker），确认锁等待保持在可控范围内。

- 预期效果：
  - 任一帖子在抓取/写入过程中超时或失败时，最多影响当前帖子对应的事务，不会拖挂整批任务；
  - 不再出现几十个事务同时等待同一个 transactionid 锁的情况，数据库连接池不会再因为大量 aborted 事务被“占满”；
  - 评论表的并发写入从“长事务串行等待”降维为“短事务、快速释放锁”，整体吞吐更稳定。

> 补充（2025-11-19）：为避免社区池初始化方案混乱，已将早期的 `init_community_pool.py` 与 `import_clean_260_communities.py` 标记为历史实现并从脚本目录移除，后续所有社区池初始化统一通过 `backend/scripts/backfill_community_pool_from_csv_97.py`（`make backfill-97-communities` / `make pool-init`）完成，在此记录。

### 3.2 抓取配置修复（crawler.yml 水位线 + 分级策略）

- 修改 `backend/config/crawler.yml`：
  - 全局配置：
    - `watermark_enabled: false` → `watermark_enabled: true`（启用水位线，增量模式）。
  - Tier T1（高价值 48 社区）：
    - `time_filter: "all"` → `time_filter: "month"`（最近 30 天）。
    - 保持 `re_crawl_frequency: "2h"`、`post_limit: 1000`。
  - Tier T2（次高价值 15 社区）：
    - `time_filter: "all"` → `time_filter: "month"`。
    - 保持 `re_crawl_frequency: "4h"`、`post_limit: 1000`。
  - Tier T3（扩展语义 34 社区）：
    - `match_tiers: ["low"]` → `match_tiers: ["semantic"]`（专门匹配 semantic 社区）。
    - `re_crawl_frequency: "6h"` → `re_crawl_frequency: "8h"`。
    - `time_filter: "all"` → `time_filter: "month"`。
    - `post_limit: 1000` → `post_limit: 500`（控制语义长尾抓取量）。
  - 通过 `app.services.crawler_config.get_crawler_config(reload=True)` 验证：
    - `watermark_enabled = True`。
    - `T1: freq_h=2, time_filter=month, post_limit=1000`。
    - `T2: freq_h=4, time_filter=month, post_limit=1000`。
    - `T3: freq_h=8, time_filter=month, post_limit=500`。

### 3.3 运行链路与监控脚本

- Celery 侧处理：
  - 手工停掉历史 Celery 进程：`pkill -f "celery -A app.core.celery_app"`。
  - 使用 `nohup` 在后台重新拉起：
    - Worker：`cd backend && nohup ../venv/bin/celery -A app.core.celery_app worker --loglevel=info --concurrency=2 >/tmp/celery_worker.log 2>&1 &`
    - Beat：`cd backend && nohup ../venv/bin/celery -A app.core.celery_app beat --loglevel=info --schedule tmp/celerybeat-schedule.db >/tmp/celery_beat.log 2>&1 &`
  - 用 `ps aux | grep "celery -A app.core.celery_app"` 校验进程存在。
- 手动触发一次增量任务（方便首轮验证）：
  - 在 `backend/` 下执行：
    - `python - << 'PY' ... crawl_seed_communities_incremental.delay(force_refresh=False) ... PY`
  - 结果：任务已成功派发，但 Celery Worker 内部报出已有的 async/DB 事件循环兼容问题（详见下一节“遗留问题”）。
- 新增运行期监控脚本：`scripts/monitor_data_growth.sh`
  - 功能：统计最近 4 小时 `posts_raw` / `comments` 增量。
  - 默认在本地自动使用 `postgresql+asyncpg://postgres:postgres@localhost:5432/reddit_signal_scanner`，并会自动去掉 `+asyncpg`。
  - 当前执行结果（在本次修复后）：
    - `posts_raw total=76076, last_4h=0`
    - `comments total=853677, last_4h=0`

---

## 4）下一步做什么？

1. **修后观察（短期）**
   - 按照文档建议，在 Celery 修复 async/DB 事件循环问题后：
     - 持续运行 `scripts/monitor_data_growth.sh`（建议每 4 小时一次），观察 posts/comments 的新增量是否稳定。
     - 重点关注 high/medium tier 社区的抓取频率是否符合 `2h/4h/8h` 策略。
2. **Celery async 兼容性修复（独立子任务）**
   - 当前 `tasks.crawler.crawl_seed_communities_incremental` 在 Worker 内部仍有：
     - `RuntimeError: got Future ... attached to a different loop`。
   - 建议在后续 Phase 中单独开一个“Celery + async DB 兼容性”修复任务，对 `SessionFactory` 在 Celery 环境中的使用方式做统一调整（这一问题是通用基础设施问题，不仅限于 97 社区数据流）。
3. **数据质量持续校验**
   - 定期执行重复度检查（已按新 schema 落地）：
     - `SELECT source_post_id, COUNT(*) AS version_count ... HAVING COUNT(*) > 1`  
     - 目前最多 3 个版本，属于“帖子更新”的正常范围。
   - 根据实际抓取情况，持续观察 `community_cache.posts_cached / total_posts_fetched` 是否合理，适时调整 `post_limit` 和调度频率。

---

## 5）这次修复的效果 / 达到的结果

- **社区配置中心恢复**：
  - `community_pool`：
    - 行数 = 97，全部 `is_active = true`。
    - tier 分布符合高/次高/扩展语义的 48/15/34 策略。
- **抓取缓存 + 水位线恢复**：
  - `community_cache`：
    - 行数 = 84，其中 84 条都已设置 `last_seen_created_at`（水位线完整）。
    - `crawl_frequency_hours` 与 tier 策略对齐（high=2、小于 500 帖子的语义社区=8 等）。
  - 现在系统具备从“已有 7.6 万帖子 + 85 万评论”平滑切换到“严格按水位线增量抓取”的能力。
- **配置与监控闭环建立**：
  - `crawler.yml` 已切回增量模式（`watermark_enabled=true` / `time_filter="month"`），避免继续无水位线地重复回扫历史数据。
  - 新增 `scripts/monitor_data_growth.sh`，结合手动 SQL 能够随时验证修复后的数据增长是否健康。
- **与文档预期的差异点（已记录）**：
  - 文档预期 `community_cache` 行数 ~98，本次实际为 84：
    - 原因：当前库内只有 84 个社区在 97 个保留社区 + `posts_raw` 交集中有历史数据，其余 13 个是“池里已配置但尚未有历史帖”的社区。
    - 处理策略：这 13 个社区保持 pool 配置，待后续抓取任务跑通后，由系统自然创建 cache 记录。
  - Celery 增量抓取任务已经可以派发，但 Worker 内部仍有 async/DB 事件循环问题，需要在后续 Phase 单独解决。

> 结论：  
> 本次执行已经完成“97 社区从 CSV → community_pool → community_cache（水位线）→ crawler.yml 配置切回增量模式”的闭环修复，数据结构和配置层面的断点已打通，后续只需在 Celery 层补齐 async 兼容性，即可按方案文档跑完整的首轮抓取与持续监控。
