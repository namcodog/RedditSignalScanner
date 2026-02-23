# Reddit Signal Scanner - 数据抓取系统操作手册 (SOP)

**版本**: 3.4 (P0 级修复 / 可连续运营版)  
**生效日期**: 2025-12-15  
**维护人**: 架构组 (David)

---

## 0. 核心架构：Cache-First (缓存优先)
**PRD-03 铁律**：分析引擎永远只读“缓存”和“冷库”，爬虫是唯一的写入者。
*   **Meta Cache (`community_cache` 表)**：记录水温、流速、最后一次活跃时间。
*   **Data Store (`posts_raw` 表)**：SCD (Slowly Changing Dimension) 历史快照。
*   **Hot Cache (Redis)**：**注意** 抓取层**不直接写** Redis 业务数据（如 Hot Lists）。抓取层只负责更新 PostgreSQL，Redis 的热加载由 `cache_manager` 或分析服务在读取时触发 (Read-Through)。

---

## 1. Step 1: 制定计划 (Plan)
**目标**：基于“社区热度”和“饥渴度”生成任务。

### A. 输入源 (Input)
1.  **`community_cache`** (数据库):
    *   `last_crawled_at`: 上次成功抓取时间。
    *   `ttl_seconds`: 动态计算的过期阈值。
    *   `crawl_priority` (1-100): 调度权重。
2.  **Overrides**: `community_blacklist.yaml` > `vertical_overrides.yaml` > `community_pool`.

### B. 任务生成 (Planning)
1.  **筛选**: `NOW() - last_crawled_at > ttl_seconds`。
2.  **排序**: Order by `crawl_priority DESC`, `hit_count DESC`。
3.  **工单**: 生成全局唯一的 **`run_id` (UUID)**，并在 `crawler_runs` 表创建记录 (status='running')。

---

## 2. Step 2: 执行抓取 (Run)
**目标**：高效执行，严格限流。

### A. 字段职责分明 (P0 修正)
严禁将 `run_id` 混入 `source_track`，导致无法索引。
*   **`crawl_run_id` (UUID)**: 必须字段。对应 `crawler_runs.id`。标识“这是哪一次卡车运回来的货”。
*   **`source_track` (Enum)**: 标识“货源渠道”。
    *   `incremental_v3`: 标准增量 (默认)。
    *   `backfill_posts`: 历史回填。
    *   `backfill_comments`: 评论补全。

### B. 运行策略
*   **Client**: `RedditAPIClient` (aiohttp)。
*   **Rate Limit**: 429 触发指数退避 (2s -> 4s -> 8s -> Skip)。
*   **断点续跑**:
    *   **增量**: 不存在断点，每次只抓 `new` 前 100。
    *   **回填**: 按时间窗分片。

---

## 3. Step 3: 落库与幂等 (Write & Dedupe)
**目标**：SCD Type 2 严格版本控制。

### A. Posts (`posts_raw`)
必须具备以下字段，否则无法回溯历史：
*   **唯一键**: `source_post_id` + `source` (default: 'reddit')。
*   **版本控制**:
    *   `text_norm_hash`: 内容指纹 (用于检测变更)。
    *   `is_current`: `true` (最新版) / `false` (历史版)。
    *   `valid_from`: 本版本生效时间。
    *   `valid_to`: 下个版本生成时间 (默认 `9999-12-31`)。
    *   **`crawl_run_id`**: **关键追踪字段** (关联 `crawler_runs` 表)。

### B. Comments (`comments`)
*   **策略**: Upsert (覆盖更新)。评论量大且修改少，暂不启用 SCD2。
*   **追踪**: 必须写入 `crawl_run_id`。

---

## 4. Step 4: 更新缓存与元数据 (Update Cache)
**目标**：**Cache-First 的核心环节**。不更新缓存 = 白抓。

### A. `community_cache` 更新规则
仅当本次抓取**成功**（无 Fatal Error）时更新：
1.  **`last_crawled_at`** = `NOW()`。
2.  **`posts_cached`** = `SELECT count(*) FROM posts_raw WHERE is_current=true`.
3.  **`hit_count`**: 保持累加（由分析端贡献，抓取端仅读取）。
4.  **`ttl_seconds` (动态)**:
    *   新增帖 > 5 → TTL * 0.8 (加速)。
    *   新增帖 = 0 → TTL * 1.2 (降速)，上限 24h。

### B. Redis 职责
*   **Crawler**: **不写 Redis**。只负责让 PG 里的数据是最新的。
*   **Analyzer/API**: 负责读取 PG -> 写入 Redis (Cache Aside / Read Through)。

---

## 5. Step 5: 交付下游 (Hand-off)
**目标**：明确“可消费”的定义。

*   **v_post_semantic_tasks**: 仅包含 `is_current=true` 且 `selftext` 非空的新帖。
*   **v_comment_semantic_tasks**: (预留) 用于评论深度分析。

---

## 6. 运行与排查 (Runbook)

### 常用命令 (使用真实脚本)
**1. 启动标准增量 (Standard Incremental)**
```bash
# 默认跑所有 Active 社区 (scope=all)，时间窗=all (实为最近)
python backend/scripts/crawl_comprehensive.py --scope all
```

**2. 强制回填 (Force Backfill)**
```bash
# 回填指定社区过去一年的数据，忽略水位线
python backend/scripts/crawl_comprehensive.py --communities r/coffee r/espresso --time-filter year --ignore-watermark
```

**3. 评论补全 (Comments Backfill)**
```bash
# 跳过帖子抓取，只针对高价值帖子补全评论
python backend/scripts/crawl_comprehensive.py --scope all --comments-only
```

### 监控指标 (`crawl_metrics` / `crawler_runs`)
排查时必看：
*   **Run 状态**: `SELECT * FROM crawler_runs ORDER BY started_at DESC LIMIT 5;`
*   **Run 产出**: `SELECT crawl_run_id, COUNT(*) FROM posts_raw GROUP BY crawl_run_id;`
*   **Error Breakdown**: 检查 `crawler_runs.metrics` 中的错误详情。

---

**总结**：
v3.4 彻底厘清了**“谁负责什么”**：
*   **SCD2** 负责历史。
*   **crawl_run_id** (DB) 负责追踪。
*   **community_cache** 负责调度。
*   **PG** 负责存储，**Redis** 归下游管。
这才是能连续运营 7x24h 的系统。