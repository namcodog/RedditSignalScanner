# Reddit Signal Scanner - 数据抓取系统操作手册 (SOP)

**版本**: 3.0 (Post-Refactoring Era)
**生效日期**: 2025-12-14
**维护人**: 架构组 (David)
**适用场景**: 日常运维、冷启动回填（帖子+评论）、数据清洗、战略选品

---

## 1. 系统架构全景 (Architecture)

本系统采用 **"双轨制 (Dual Track)"** 架构，兼顾实时性与吞吐量。核心依赖于自定义的 `RedditAPIClient` (基于 aiohttp)，而非 PRAW，以实现更精细的速率限制控制。

### 1.1 双轨机制
| 轨道 | 组件名称 | 适用场景 | 核心特点 |
| :--- | :--- | :--- | :--- |
| **System A (在线/稳态)** | **Celery Beat + Worker** | 7x24小时日常巡航 | **自动化**。R-F-E 动态调度，增量抓取 (`/new`)，双写冷热库。 |
| **System B (离线/回填)** | **crawl_comprehensive.py** | 帖子+评论回填、冷启动 | **统一入口**。支持三种模式：只帖子/只评论/帖子+评论。 |

### 1.2 核心防御 (Defense System)
1.  **代码过滤器 (`_is_spam_post`)**: 自动拦截垃圾贴（黑名单作者、加密货币广告）。
2.  **数据库防火墙**: 严格的外键约束（如作者必须存在）。
    *   *机制*: 爬虫服务内置了 **Atomic Author Upsert**，在插入帖子前自动创建作者，彻底解决了外键冲突问题。
3.  **速率限制 (Rate Limit)**:
    *   **本地**: 滑动窗口限流。
    *   **全局**: 支持 Redis 分布式限流（可选）。
    *   **避让**: 遇到 429 错误自动指数退避。

---

## 2. 数据流转与架构断点 (Data Pipeline & Gaps)

随着数据库架构升级到 V1 (Rulebook)，抓取系统的上下游关系如下：

### 2.1 数据流向
1.  **输入**: Reddit API (`/r/xxx/new` or `/top`)。
2.  **清洗**: `IncrementalCrawler` 进行基础去重和 Spam 过滤。
3.  **存储**:
    *   **冷库**: `posts_raw` (SCD2 版本控制，永久存储)。
    *   **热库**: `posts_hot` (7天缓存，用于快速去重)。
    *   **水位线**: `community_cache` (记录 `last_seen_created_at`)。

### 2.2 ⚠️ 关键断点 (Critical Gaps)
目前抓取系统与分析系统**尚未完全打通**：
*   **断点 1 (评分)**: 抓取后仅触发旧版 `tag_posts_batch`，**未触发** 新版 `score_posts_v2_optimized`。这意味着新进来的帖子在 `post_scores` 表中是缺失的。
*   **断点 2 (评论)**: 评论抓取 (`comments.backfill_full`) 目前是全量回填，**未利用** `value_score` 进行智能筛选（即垃圾贴也在抓评论，浪费额度）。

---

## 3. 轨道一：日常自动化抓取 (System A)

这是系统的“心跳”，由 `Celery Beat` 驱动。

### 3.1 启动服务
```bash
# 方式 A: Docker (推荐)
docker-compose up -d celery_worker celery_beat

# 方式 B: 本地运行 (需确保 PYTHONPATH 正确)
export PYTHONPATH=$(pwd)/backend
cd backend && celery -A app.core.celery_app beat --loglevel=INFO
cd backend && celery -A app.core.celery_app worker --loglevel=INFO --pool=solo
```

---

## 4. 轨道二：历史数据回填 (System B) - 统一入口

**注意：此脚本现已支持帖子+评论的统一回填。**

`crawl_comprehensive.py` 是系统的离线回填核心工具，支持三种模式：

| 模式 | 参数 | 说明 |
| :--- | :--- | :--- |
| **只抓帖子** | (默认) | 使用 Top/New/Hot 三种策略抓取帖子 |
| **只抓评论** | `--comments-only` | 跳过帖子，只补齐评论数据 |
| **帖子+评论** | `--with-comments` | 抓完帖子后自动抓取评论 |

### 4.1 核心脚本
*   **路径**: `backend/scripts/crawl_comprehensive.py`
*   **能力**: 自动翻页、自动去重、断点续传、软限流。

### 4.2 常用命令速查 (Cheat Sheet)

#### 场景 A：全量回填帖子 (只抓帖子)
适用于新社区加入或系统重置后的冷启动。
```bash
PYTHONPATH=backend python3 backend/scripts/crawl_comprehensive.py \
    --scope all \
    --time-filter year \
    --max-per-strategy 1000 \
    > logs/posts_backfill.log 2>&1 &
```

#### 场景 B：全量回填评论 (只抓评论)
适用于帖子已回填完成后，补齐评论数据。
```bash
PYTHONPATH=backend python3 backend/scripts/crawl_comprehensive.py \
    --scope all \
    --comments-only \
    --skip-labeling \
    > logs/comments_backfill.log 2>&1 &
```

#### 场景 C：帖子+评论一起抓 (完整回填)
适用于新社区的完整数据初始化。
```bash
PYTHONPATH=backend python3 backend/scripts/crawl_comprehensive.py \
    --communities r/shopify r/entrepreneur \
    --time-filter year \
    --with-comments \
    --skip-labeling \
    > logs/full_backfill.log 2>&1 &
```

---

## 5. 抓取-分析对齐 Checklist (v3.0)

- **Step 1 统一入口**：社区名单只来自 `community_pool` + `community_blacklist.yaml` + `community_roles.yaml` + `vertical_overrides.yaml` + `seed_communities_mapping.yml` 汇总的“抓取计划”，禁止硬编码。
- **Step 2 简化职责**：
  - 增量轨：只抓新帖写 `posts_raw`（可选少量预览评论），不调用 LLM、不打分。
  - 回填轨：帖子回填按“社区+时间窗”写 `posts_raw`；评论回填只对 `post_scores` 中高价值帖子抓全量评论树写 `comments`。
- **Step 3 补齐原始字段**：`posts_raw`/`comments` 统一写 `source_track`（incremental/backfill_posts/backfill_comments）、`first_seen_at`、`fetched_at`，可选 `lang`；`business_pool` 初始为 `lab`/NULL，`value_score` 为空，抓取层不判 core/noise。
- **Step 4 语义出口**：建视图 `v_post_semantic_tasks`（post_id、subreddit、title、截断 selftext、score_band、comment_band、community_role、vertical），预留 `v_comment_semantic_tasks` 供后续核心帖评论语义用。
- **Step 5 团队共识**：
  1) 抓取脚本不直接调用 LLM，价值判断留给分析层（post_scores/comment_scores + Rulebook/Agent）。
  2) 抓取成功标准：
     - Active 社区的新帖子能稳定、完整写入 `posts_raw`；
     - 被列入“评论回填任务”的帖子，其评论树能完整、稳定写入 `comments`；
     - `posts_raw`/`comments` 字段齐全，可随时导出给 LLM/Agent。
  3) 抓取 = “搬石头并标清产地时间”，上层 = “鉴定并打分出报表”。

---

## 6. 优化路线图 (Optimization Roadmap)

### 6.0 执行层工具栈（v3.0）
* **Reddit 主数据**：PRAW / asyncpraw 作为唯一官方 API 客户端（posts / comments / authors / subreddit 元数据），绑定 IncrementalCrawler、crawl_comprehensive。
* **通用 HTTP**：aiohttp 作为唯一通用抓取客户端，用于帖子外链（产品页、测评页、品牌官网等）。
* **不使用 Apify / 第三方爬虫平台**：为保持配置一致性与可控性，System C（Apify）已移除。

为了适配 V1 数据库架构，即将执行以下升级手术：

### 6.1 手术一：打通即时评分 (Real-time Scoring)
*   **目标**: 帖子入库即有分。
*   **方案**: 修改 `IncrementalCrawler` 的回调，从触发 `tag_posts_batch` (Legacy) 改为触发 `tasks.analysis.score_new_posts_v1` (New)。

### 6.2 手术二：智能评论抓取 (Smart Comments)
*   **目标**: 好钢用在刀刃上。
*   **方案**: 评论抓取任务先查询 `post_scores.value_score`。
    *   **Score >= 6**: 立即抓取，Depth=8。
    *   **Score < 4**: 跳过抓取。

---

## 7. 故障排查 (Troubleshooting)

### Q1: 报 `AttributeError: inserted` 或数据库无数据？
*   **原因**: 曾出现 `upsert` 逻辑在并发冲突时静默失败。
*   **解决**: 现已修复 `IncrementalCrawler`，使用 `fetched_at` 强制刷新机制，并移除了不稳定的 `RETURNING xmax` 语法。

### Q2: 批量脚本跑了一半报错？
*   **原因**: 长事务导致 Session 污染。
*   **解决**: `crawl_comprehensive.py` 现已实现 **Per-Community Session**（每社区独立会话），单点失败不会影响后续任务。

### Q3: 评论回填脚本挂了怎么办？
*   **原因**: 数据库连接超时断开 (`InterfaceError: underlying connection is closed`)。
*   **解决**: 直接重新运行相同命令，脚本会自动断点续传，跳过已完成的帖子。

---
**文档结束**
