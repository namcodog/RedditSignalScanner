# Reddit Signal Scanner - 数据抓取系统操作手册 (SOP)

**版本**: 3.3.1 (现状可执行版 / Cache-First)  
**生效日期**: 2025-12-18  
**维护人**: 架构组 (David)

---

## 0. 核心架构：Cache-First (缓存优先)
**PRD-03 铁律**：分析引擎永远只读“缓存”和“冷库”，爬虫是唯一的写入者。
*   **Meta Cache (`community_cache` 表)**：记录水温、流速、最后一次活跃时间。
*   **Data Store (`posts_raw` 表)**：SCD (Slowly Changing Dimension) 历史快照。
*   **Hot Cache (Redis)**：高频访问的实时计算区（由 `cache_manager` 维护）。

**爬虫的唯一职责**：维持 `community_cache` 的新鲜度，并把新数据搬进 `posts_raw`。

### 两条轨道（System A / System B）
这套系统有两种“正常工作模式”，不是互相替代，而是各管一段：

| 轨道 | 形态 | 适用场景 | 输出形态 | 一句话注意事项 |
| --- | --- | --- | --- | --- |
| **System A（在线/稳态）** | `Celery Beat + Worker` 常驻服务 | 7x24 日常巡航、增量抓取、新增社区后自动接手 | 直接写库 + 更新 `community_cache` 水位线 | **靠水位线控重复**，任务允许重试所以入库要幂等 |
| **System B（离线/回填）** | 脚本抓取/脚本入库 | 冷启动、补历史数据（90 天/12 个月） | 先落本地 JSONL，再批量入库（或重型脚本直接写库） | **回填后要推进水位线**，否则 A 会“以为没补过”继续抓旧数据 |

---

## 1. Step 1: 制定计划 (Plan)
**目标**：基于“社区热度”和“饥渴度”生成任务，而不是机械轮询。

### 输入源
1.  **`community_cache` (主驱动)**：
    *   `last_crawled_at` (上次什么时候抓的)
    *   `crawl_frequency_hours` (抓取频率，单位小时；由分层策略动态调整)
    *   `quality_tier` / `avg_valid_posts` / `empty_hit` / `failure_hit`（用于分层与降级）
2.  **`community_blacklist.yaml`**：熔断名单。
3.  **`vertical_overrides.yaml`**：赛道强制干预。

### 计划生成逻辑
1.  **Staleness Check (过期检查)**：
    `NOW() >= last_crawled_at + crawl_frequency_hours` 的社区进入候选池（实现口径）。
2.  **Priority Sorting (优先级排序)**：
    优先级可选：基于历史 `pain_density` 做自适应排序（失败则回退原始顺序）。
3.  **Plan Output (工单)**：
    生成 `run_id`（UUID，单次批次的“流水号”），用于把本轮写入的数据串起来。
    
    **现状落地口径**：
    - 父/子两层（推荐口径）：
      - `crawl_run_id`（父级）：一次定时触发的“整轮抓取”。
      - `community_run_id`（子级）：本轮里某个社区的一次抓取。
    - 数据落地位置（现状）：
      - 主表字段：`posts_raw.crawl_run_id / posts_raw.community_run_id`，`comments.crawl_run_id / comments.community_run_id`
      - 追踪表：`crawler_runs`（父级汇总），`crawler_run_targets`（子级逐社区）
    - 兼容口径：`posts_raw.metadata->>'run_id'` 仍保留，方便老查询/排查。

---

## 2. Step 2: 执行抓取 (Run)
**目标**：高效执行，严格限流。

### 运行机制
*   **调度入口（现状黄金路径）**：
    *   `Celery Beat` 定时触发“心跳任务”，由 `Celery Worker` 消费队列并执行抓取。
    *   手工触发可走脚本（见第 6 节）。
*   **Client**: `RedditAPIClient` (aiohttp)。
*   **Concurrency**:
    *   HTTP 并发：由 `settings.reddit_max_concurrency` 控制（默认偏保守，避免超限）。
    *   DB 并发：由 `CRAWLER_MAX_CONCURRENCY` / 配置控制（默认低并发，避免 DB “并发操作不允许”）。
*   **Rate Limit**:
    *   解析 `X-Ratelimit-*` 响应头做动态监控。
    *   429：指数退避重试（优先用 `Retry-After`；否则按 base * 2^n，最大 60 秒）。
    *   可选：启用 Redis 全局限流（跨 worker 协同）。

### 错误分级处理
| 错误码 | 行为 | 缓存动作 |
| :--- | :--- | :--- |
| **429** | 暂停 + 重试 | 不更新缓存 |
| **401** | 刷新 token 后重试一次 | 不更新缓存 |
| **403/404** | 按“空结果”处理（私有/不存在） | 记录 empty_hit（不强制停用） |
| **5xx/Timeout** | 短重试 (3次) | 记录 `failure_hit += 1` |
| **Empty** | 记录 Warning | 记录 `empty_hit += 1`（当前不强制改频率，分层策略会接手） |

---

## 3. Step 3: 落库与幂等 (Write & Dedupe)
**目标**：数据入库，去重防污染。

### A. 写入策略
1.  **Posts (`posts_raw`)**：
    *   **去重键（实现口径）**：`(source, source_post_id, version)`（同一帖多版本）。
    *   **Upsert (SCD2)**：内容/关键字段变更 → 关闭旧 current → 插入新版本（`version += 1`）。
2.  **Comments (`comments`)**：
    *   **去重键**：`reddit_comment_id`。
    *   **Upsert**：覆盖更新（评论不需要保留历史版本，只看最新）。

### B. 必写追踪字段
每条写入记录必须包含：
*   `crawl_run_id` / `community_run_id`: 本轮抓取追踪号（若数据库有列，System A 会自动写；没有列也不影响入库）。
*   `run_id`（兼容字段）: `posts_raw.metadata->>'run_id'`（用于对账/排查，逐步可被列字段替代）。
*   `source_track`: 来源标记 (e.g., `incremental` / `incremental_preview`).
*   `fetched_at`: 抓取时间戳。
*   `first_seen_at`: 首次入库时间（新帖才有）。

---

## 4. Step 4: 更新缓存与元数据 (Update Cache)
**目标**：告诉系统“我干完活了，水是热的”。**此步不做，系统就是瞎子。**

### `community_cache` 必须更新的字段：
1.  **`last_crawled_at`** = `NOW()`。
2.  **水位线（增量抓取）**：
    *   `last_seen_post_id` / `last_seen_created_at`（用于下次过滤）。
3.  **计数与健康度**：
    *   `total_posts_fetched` / `dedup_rate`（抓取产出与重复率）
    *   `empty_hit` / `failure_hit` / `success_hit`（用于降级/分层）
4.  **分层频率（实现口径）**：
    *   `quality_tier` / `crawl_frequency_hours` 由分层调度器刷新与下发。

---

## 5. Step 5: 交付下游 (Hand-off)
**目标**：半成品不准上桌。

### 交付门禁
现状实现：`v_post_semantic_tasks` 主要筛选 **`posts_raw.is_current = TRUE`** 的“当前版本帖子”，并补充社区 role/vertical 字段；不做“已分析过滤/长度过滤”。

### 语义任务视图
*   **输入**：`v_post_semantic_tasks` (Post ID, Title, Truncated Body, Context)。
*   **输出**：Agent 读取视图 → 分析 → 写入 `post_semantic_labels`。

---

## 6. 运行与排查 (Runbook)

### 常用命令
**1. System A：启动智能增量（在线/稳态）**
```bash
# 推荐：一键启动 Redis + Backend + Celery Beat/Worker（黄金路径）
make dev-golden-path

# 或仅启动抓取调度（Beat + Worker）
make dev-celery-beat
```

**2. System A：手工触发一次增量抓取（不等 Beat）**
```bash
# 需要 Celery Worker 已启动（dev-golden-path / dev-celery-beat）
PYTHONPATH=backend python backend/scripts/trigger_incremental_crawl.py --force-refresh
```

**3. System B：历史回填（离线/回填）**
```bash
# 先抓到本地 JSONL（不入库）
python backend/scripts/crawl_incremental.py \
  --subreddit ecommerce \
  --max-pages 50 \
  --lookback-days 90 \
  --output backend/data/reddit_corpus/ecommerce_90d.jsonl \
  --stream-write

# 再把 JSONL 批量入库（幂等导入）
PYTHONPATH=backend python backend/scripts/ingest_jsonl.py \
  --file backend/data/reddit_corpus/ecommerce_90d.jsonl \
  --community r/ecommerce \
  --update-watermark
```

### 关键检查查询
**1. 检查谁在偷懒 (未更新缓存)**
```sql
SELECT community_name, last_crawled_at, crawl_frequency_hours
FROM community_cache 
WHERE last_crawled_at < NOW() - INTERVAL '2 days' 
ORDER BY crawl_priority DESC;
```

**2. 检查抓取产出（推荐：按 `crawl_run_id` 字段）**
```sql
SELECT crawl_run_id, COUNT(*) AS posts, MIN(fetched_at) AS min_fetched_at, MAX(fetched_at) AS max_fetched_at
FROM posts_raw
WHERE crawl_run_id IS NOT NULL
GROUP BY crawl_run_id
ORDER BY MAX(fetched_at) DESC
LIMIT 10;
```

**3. 检查抓取产出（comments，按 `crawl_run_id`）**
```sql
SELECT crawl_run_id, COUNT(*) AS comments, MIN(fetched_at) AS min_fetched_at, MAX(fetched_at) AS max_fetched_at
FROM comments
WHERE crawl_run_id IS NOT NULL
GROUP BY crawl_run_id
ORDER BY MAX(fetched_at) DESC
LIMIT 10;
```

**4. 检查抓取轨迹（父/子 run 追踪表）**
```sql
SELECT id AS crawl_run_id, status, started_at, completed_at
FROM crawler_runs
ORDER BY started_at DESC
LIMIT 10;
```

```sql
SELECT id AS community_run_id, crawl_run_id, subreddit, status, started_at, completed_at
FROM crawler_run_targets
ORDER BY started_at DESC
LIMIT 20;
```

**5. 兼容查询（按 `posts_raw.metadata->>'run_id'`）**
```sql
SELECT (metadata->>'run_id') AS run_id, COUNT(*) AS posts, MIN(fetched_at) AS min_fetched_at, MAX(fetched_at) AS max_fetched_at
FROM posts_raw
WHERE metadata ? 'run_id'
GROUP BY (metadata->>'run_id')
ORDER BY MAX(fetched_at) DESC
LIMIT 10;
```

**6. 检查缓存健康度**
```sql
SELECT 
    AVG(hit_count) as avg_hits, 
    SUM(empty_hit) as total_empty, 
    AVG(crawl_priority) as avg_prio 
FROM community_cache;
```

**7. 新增社区失败（duplicate key）时：修复“发号器”**
```bash
# 这是数据库内部记账问题，不改业务数据；修完就能继续新增社区
psql "$DATABASE_URL" -f repair_community_pool_id_sequence.sql
```

---

**总结**：
Cache-First 意味着：**抓取是为了刷新 `community_cache` 的状态，而不仅仅是堆积 `posts_raw` 的行数。**
没有更新 `community_cache` 的抓取，等于没有抓取。
