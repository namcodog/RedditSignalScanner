# Reddit Signal Scanner - 数据抓取系统 SOP

**版本**: 1.0  
**生效日期**: 2025-12-01  
**维护人**: 架构组 (Key)  
**适用对象**: 运维工程师、后端开发

---

## 1. 系统全景图 (System Overview)

本系统采用 **“分级调度 + 增量水位线 + 冷热双写”** 的架构，确保数据抓取的高效性与完整性。

### 1.1 数据流向 (The Pipeline)
```mermaid
[Reddit API] 
    --> (Rate Limiter / RedditAPIClient) 
    --> [IncrementalCrawler (Service)]
        --> 1. 垃圾过滤 (_is_spam_post / Blacklist)
        --> 2. 水位线检查 (Watermark Check)
        --> 3. 双写机制 (Dual Write)
            --> [Postgres: posts_raw] (冷存储/SCD2历史)
            --> [Postgres: posts_hot] (热缓存/TTL 180天)
    --> [Celery Worker] (异步任务)
        --> 触发: [Vectorization] (post_embeddings)
        --> 触发: [Labeling] (content_labels)
```

### 1.2 核心组件
*   **调度心脏**: `Celery Beat` (负责定时触发心跳)。
*   **执行大脑**: `app.services.tiered_scheduler` (决定谁是 Tier 1/2/3，谁该多抓，谁该少抓)。
*   **执行手脚**: `app.services.incremental_crawler` (执行具体的 API 请求和入库)。

---

## 2. 环境准备 (Prerequisites)

在启动抓取前，必须确保以下配置就绪。

### 2.1 核心配置文件 (`backend/.env`)
| 变量名 | 作用 | 示例值 |
| :--- | :--- | :--- |
| `REDDIT_CLIENT_ID` | Reddit API 凭证 | `(Secret)` |
| `REDDIT_CLIENT_SECRET` | Reddit API 密钥 | `(Secret)` |
| `DATABASE_URL` | 生产数据库连接 | `postgresql+asyncpg://...` |
| `CELERY_BROKER_URL` | 任务队列 Broker | `redis://localhost:6379/1` |
| `CELERY_RESULT_BACKEND` | 任务结果存储 | `redis://localhost:6379/2` |

### 2.2 数据库状态
必须确保 Schema 已同步且种子数据已加载：
```bash
# 1. 检查数据库连接
make check-health

# 2. 确认种子社区池不为空 (至少要有 1 个 is_active=true 的社区)
# SQL: SELECT count(*) FROM community_pool WHERE is_active = true;
```

---

## 3. 启动与运行 (Operation Guide)

本系统**不推荐**手动运行 Python 脚本，而是完全依赖 **Celery** 进程守护。

### 3.1 标准启动流程 (Production Start)
在服务器上，你需要启动两个进程：`Beat` (发令员) 和 `Worker` (干活的)。

**方式 A: 使用 Docker (推荐)**
```bash
docker-compose up -d celery_worker celery_beat
```

**方式 B: 本地/裸机启动**
```bash
cd backend

# 1. 启动 Worker (处理抓取任务)
# --pool=solo 在 MacOS/Windows 上更稳定，Linux 可用默认 prefork
celery -A app.core.celery_app worker --loglevel=INFO --pool=solo &

# 2. 启动 Beat (定时调度)
celery -A app.core.celery_app beat --loglevel=INFO &
```

### 3.2 验证启动状态
查看日志，确认出现以下字样：
*   `beat`: `Scheduler: Sending due task tasks.crawler.crawl_seed_communities_incremental ...`
*   `worker`: `Task tasks.crawler.crawl_community[...] succeeded`

---

## 4. 日常运维任务 (Maintenance Tasks)

### 4.1 添加新社区 (Onboard New Community)
不需要重启服务，直接写库即可。调度器会自动发现新社区。

**SQL 操作**:
```sql
-- 添加一个新社区 r/NewTrend，默认激活
INSERT INTO community_pool (name, url, is_active, created_at, updated_at)
VALUES ('r/NewTrend', 'https://reddit.com/r/NewTrend', true, NOW(), NOW())
ON CONFLICT (name) DO UPDATE SET is_active = true;
```
*注：名称必须符合 `^r/[a-z0-9_]+$` 小写规范，否则数据库会报错拒绝。*

### 4.2 强制抓取某个社区 (Manual Trigger)
如果你不想等调度器，想立刻马上抓一次：

**命令行操作**:
```bash
cd backend
# 使用 Celery call 触发
celery -A app.core.celery_app call tasks.crawler.crawl_community --args "['r/shopify']"
```

### 4.3 封禁社区 (Blacklist)
发现某个社区质量太差，想停止抓取：

**SQL 操作**:
```sql
UPDATE community_pool SET is_blacklisted = true, is_active = false WHERE name = 'r/badcommunity';
```

---

## 5. 监控与报警 (Monitoring)

### 5.1 核心监控表 (`quality_metrics`)
系统每天会自动生成一行日报。
```sql
SELECT * FROM quality_metrics ORDER BY date DESC LIMIT 5;
```
*   **`collection_success_rate`**: 应 > 0.9。如果过低，检查 API Key 是否失效或网络。
*   **`deduplication_rate`**: 反映增量抓取效率。

### 5.2 实时日志检查
搜索以下关键词监控健康度：
*   **`[SPAM BLOCKED]`**: 拦截系统正在工作。
*   **`[RATE_LIMIT]`**: 触发了 Reddit 429 限流（系统会自动退避，无需人工干预，但需关注频率）。
*   **`IntegrityError`**: 数据库约束冲突（通常代码会自动处理并记录 ERROR）。

---

## 6. 故障排查 (Troubleshooting)

### Q1: 为什么新加的社区一直没数据？
1.  检查 `community_pool.is_active` 是否为 `true`。
2.  检查 `community_cache` 是否有该社区记录。如果没有，可能是 `TieredScheduler` 还没轮到它（默认每 30 分钟一轮）。
3.  检查日志是否有 `403 Forbidden` 或 `404 Not Found`（社区可能是私密的或不存在）。

### Q2: 为什么搜索搜不到刚抓的帖子？
1.  **Embedding 延迟**: 抓取和向量化是异步的。检查 `celery` 队列是否有积压。
2.  **垃圾拦截**: 检查日志，是否因为标题包含 `placeholder` 或正文包含 `AmazonFC` 被 `_is_spam_post` 拦截了。

### Q3: 磁盘空间报警了怎么办？
1.  检查 `posts_raw` 表膨胀情况。
2.  执行 `VACUUM FULL posts_raw` (注意：会锁表，需停机维护)。
3.  考虑启动 **Phase 5 (分区表)** 计划。

---

**文档结束**
