# Reddit Signal Scanner - 数据抓取系统架构文档

**版本**: v0.1.0  
**生成时间**: 2025-10-22  
**文档类型**: 数据抓取系统架构与调度机制

---

## 目录

- [1. 系统概览](#1-系统概览)
- [2. Celery定时任务](#2-celery定时任务)
- [3. 抓取模式](#3-抓取模式)
- [4. 核心服务模块](#4-核心服务模块)
- [5. 数据流转](#5-数据流转)
- [6. 分层调度策略](#6-分层调度策略)
- [7. 监控与维护](#7-监控与维护)

---

## 1. 系统概览

### 1.1 抓取系统架构

```
┌─────────────────────────────────────────────────────────────┐
│ Celery Beat 定时调度器                                       │
├─────────────────────────────────────────────────────────────┤
│ - warmup-crawl-seed-communities (每2小时)                    │
│ - auto-crawl-incremental (每30分钟)                          │
│ - crawl-low-quality-communities (每4小时)                    │
│ - monitor-warmup-metrics (每15分钟)                          │
│ - cleanup-expired-posts (每6小时)                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Celery Worker (crawler_queue)                               │
├─────────────────────────────────────────────────────────────┤
│ - crawl_seed_communities (旧版批量抓取)                      │
│ - crawl_seed_communities_incremental (增量抓取)              │
│ - crawl_low_quality_communities (低质量社区补抓)             │
│ - crawl_community (单社区抓取)                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 核心服务层                                                   │
├─────────────────────────────────────────────────────────────┤
│ - IncrementalCrawler (增量抓取器)                            │
│ - RedditAPIClient (Reddit API客户端)                         │
│ - CacheManager (Redis缓存管理)                               │
│ - TieredScheduler (分层调度器)                               │
│ - CommunityPoolLoader (社区池加载器)                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 数据存储层                                                   │
├─────────────────────────────────────────────────────────────┤
│ - PostRaw (冷库，持久化存储，30天+)                          │
│ - PostHot (热缓存，24小时TTL)                                │
│ - CommunityCache (社区元数据与水位线)                        │
│ - CrawlMetrics (抓取指标)                                    │
│ - Redis (帖子缓存，24小时TTL)                                │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 抓取任务文件

```
backend/app/tasks/
├── crawler_task.py              # 主抓取任务（旧版+增量）
├── warmup_crawler.py            # Warmup期抓取任务
├── monitoring_task.py           # 监控任务
├── maintenance_task.py          # 维护任务（清理过期数据）
└── metrics_task.py              # 指标生成任务
```

### 1.3 核心服务文件

```
backend/app/services/
├── incremental_crawler.py       # 增量抓取器（冷热双写+水位线）
├── reddit_client.py             # Reddit API客户端
├── cache_manager.py             # Redis缓存管理器
├── tiered_scheduler.py          # 分层调度器（Tier 1/2/3）
├── community_pool_loader.py     # 社区池加载器
└── community_cache_service.py   # 社区缓存服务
```

---

## 2. Celery定时任务

### 2.1 定时任务配置

**文件**: `backend/app/core/celery_app.py`

```python
celery_app.conf.beat_schedule = {
    # 1. Warmup批量抓取：每2小时执行一次
    "warmup-crawl-seed-communities": {
        "task": "tasks.crawler.crawl_seed_communities",
        "schedule": crontab(minute="0", hour="*/2"),
        "options": {"queue": "crawler_queue"},
    },
    
    # 2. 兼容旧版批量抓取：每30分钟执行一次
    "crawl-seed-communities": {
        "task": "tasks.crawler.crawl_seed_communities",
        "schedule": crontab(minute="0,30"),
        "options": {"queue": "crawler_queue"},
    },
    
    # 3. 增量抓取：每30分钟执行一次（冷热双写+水位线）
    "auto-crawl-incremental": {
        "task": "tasks.crawler.crawl_seed_communities_incremental",
        "schedule": crontab(minute="0,30"),
        "options": {"queue": "crawler_queue", "expires": 1800},
    },
    
    # 4. 精准补抓低质量社区：每4小时执行一次
    "crawl-low-quality-communities": {
        "task": "tasks.crawler.crawl_low_quality_communities",
        "schedule": crontab(minute="0", hour="*/4"),
        "options": {"queue": "crawler_queue", "expires": 3600},
    },
    
    # 5. Warmup期监控：每15分钟执行一次
    "monitor-warmup-metrics": {
        "task": "tasks.monitoring.monitor_warmup_metrics",
        "schedule": crontab(minute="*/15"),
    },
    
    # 6. 每日指标生成：每天0点执行
    "generate-daily-metrics": {
        "task": "tasks.metrics.generate_daily",
        "schedule": crontab(hour="0", minute="0"),
        "options": {"queue": "monitoring_queue"},
    },
    
    # 7. API调用监控：每分钟执行一次
    "monitor-api-calls": {
        "task": "tasks.monitoring.monitor_api_calls",
        "schedule": crontab(minute="*"),
    },
    
    # 8. 缓存健康监控：每5分钟执行一次
    "monitor-cache-health": {
        "task": "tasks.monitoring.monitor_cache_health",
        "schedule": crontab(minute="*/5"),
    },
}
```

### 2.2 任务队列配置

```python
DEFAULT_QUEUE_NAMES = (
    "analysis_queue,"      # 分析任务队列
    "maintenance_queue,"   # 维护任务队列
    "cleanup_queue,"       # 清理任务队列
    "crawler_queue,"       # 抓取任务队列
    "monitoring_queue"     # 监控任务队列
)
```

### 2.3 任务路由规则

```python
task_routes = {
    "tasks.crawler.crawl_community": {"queue": "crawler_queue"},
    "tasks.crawler.crawl_seed_communities": {"queue": "crawler_queue"},
    "tasks.crawler.crawl_low_quality_communities": {"queue": "crawler_queue"},
    "tasks.monitoring.monitor_api_calls": {"queue": "monitoring_queue"},
    "tasks.monitoring.monitor_cache_health": {"queue": "monitoring_queue"},
    "tasks.monitoring.monitor_crawler_health": {"queue": "monitoring_queue"},
    "tasks.metrics.generate_daily": {"queue": "monitoring_queue"},
}
```

---

## 3. 抓取模式

### 3.1 旧版批量抓取（只写Redis缓存）

**任务**: `crawl_seed_communities`  
**调度**: 每30分钟 + 每2小时（Warmup）  
**文件**: `backend/app/tasks/crawler_task.py::_crawl_seeds_impl`

#### 执行流程

```
1. 加载社区池（CommunityPoolLoader）
   ↓
2. 筛选活跃社区（tier: high/medium/low）
   ↓
3. 并发抓取（信号量控制并发数=2）
   ├─ 调用 Reddit API (fetch_subreddit_posts)
   ├─ 写入 Redis 缓存 (CacheManager.set_cached_posts)
   └─ 更新 community_cache 表（posts_cached, last_crawled_at）
   ↓
4. 计算 Tier 分配（TieredScheduler）
   ↓
5. 写入 crawl_metrics 表
```

#### 关键参数

```python
DEFAULT_BATCH_SIZE = 12           # 每批抓取12个社区
DEFAULT_MAX_CONCURRENCY = 2       # 最大并发数2（避免数据库冲突）
DEFAULT_POST_LIMIT = 100          # 每个社区抓取100条帖子
DEFAULT_TIME_FILTER = "month"     # 时间范围：最近1个月
DEFAULT_SORT = "top"              # 排序策略：热门优先
```

#### 数据写入

- **Redis缓存**: 24小时TTL
- **community_cache表**: 更新 `posts_cached`, `last_crawled_at`
- **crawl_metrics表**: 记录抓取指标

---

### 3.2 增量抓取（冷热双写+水位线）

**任务**: `crawl_seed_communities_incremental`  
**调度**: 每30分钟  
**文件**: `backend/app/tasks/crawler_task.py::_crawl_seeds_incremental_impl`

#### 执行流程

```
1. 加载社区池（CommunityPoolLoader）
   ↓
2. 筛选活跃社区（tier: high/medium/low）
   ↓
3. 并发抓取（信号量控制并发数=2）
   ├─ 创建 IncrementalCrawler 实例
   ├─ 调用 crawl_community_incremental()
   │   ├─ 获取水位线（last_seen_created_at）
   │   ├─ 抓取新帖子（Reddit API）
   │   ├─ 过滤：只保留新于水位线的帖子
   │   ├─ 冷热双写
   │   │   ├─ 先写冷库（PostRaw）
   │   │   └─ 再写热缓存（PostHot）
   │   └─ 更新水位线（community_cache）
   └─ 记录抓取指标（crawl_metrics）
   ↓
4. 计算 Tier 分配（TieredScheduler）
   ↓
5. 汇总统计结果
```

#### 水位线机制

**水位线字段**: `community_cache.last_seen_created_at`

```python
async def _get_watermark(self, community_name: str) -> Optional[datetime]:
    """获取社区的水位线（最后抓取的帖子创建时间）"""
    result = await self.db.execute(
        select(CommunityCache.last_seen_created_at)
        .where(CommunityCache.community_name == community_name)
    )
    return result.scalar_one_or_none()
```

**过滤逻辑**:

```python
if watermark:
    posts = [p for p in posts if _unix_to_datetime(p.created_utc) > watermark]
```

#### 冷热双写策略

```python
async def _dual_write(
    self, community_name: str, posts: List[RedditPost]
) -> Tuple[int, int, int]:
    """
    冷热双写：先写冷库（PostRaw），再写热缓存（PostHot）
    
    Returns:
        (new_count, updated_count, duplicate_count)
    """
    # 1. 写冷库（PostRaw）
    new_count, updated_count, dup_count = await self._write_to_cold_storage(
        community_name, posts
    )
    
    # 2. 写热缓存（PostHot）
    await self._write_to_hot_cache(community_name, posts)
    
    return new_count, updated_count, dup_count
```

#### 去重策略

**去重键**: `(source, source_post_id, text_norm_hash)`

```python
# 使用 PostgreSQL UPSERT 实现去重
stmt = pg_insert(PostRaw).values(...)
stmt = stmt.on_conflict_do_update(
    index_elements=["source", "source_post_id", "text_norm_hash"],
    set_={
        "score": excluded.score,
        "num_comments": excluded.num_comments,
        "updated_at": datetime.now(timezone.utc),
        "version": PostRaw.version + 1,  # SCD2版本追踪
    },
)
```

---

### 3.3 低质量社区补抓

**任务**: `crawl_low_quality_communities`  
**调度**: 每4小时  
**文件**: `backend/app/tasks/crawler_task.py::_crawl_low_quality_communities_impl`

#### 查询条件

```python
cutoff_time = datetime.now(timezone.utc) - timedelta(hours=8)

result = await db.execute(
    select(CommunityCache.community_name)
    .where(
        and_(
            CommunityCache.last_crawled_at < cutoff_time,  # 超过8小时未抓取
            CommunityCache.avg_valid_posts < 50,           # 平均有效帖子数<50
            CommunityCache.is_active == True,              # 仅活跃社区
        )
    )
    .order_by(CommunityCache.last_crawled_at.asc())
    .limit(50)  # 每次最多补抓50个社区
)
```

#### 失败处理

```python
# 失败时回写 empty_hit += 1
await self.db.execute(
    pg_insert(CommunityCache)
    .values(community_name=community_name)
    .on_conflict_do_update(
        index_elements=["community_name"],
        set_={"empty_hit": CommunityCache.empty_hit + 1},
    )
)
```

---

## 4. 核心服务模块

### 4.1 IncrementalCrawler（增量抓取器）

**文件**: `backend/app/services/incremental_crawler.py`

#### 核心方法

```python
class IncrementalCrawler:
    async def crawl_community_incremental(
        self,
        community_name: str,
        limit: int = 100,
        time_filter: str = "month",
        sort: str = "top",
    ) -> dict[str, Any]:
        """增量抓取单个社区"""
        
    async def _get_watermark(self, community_name: str) -> Optional[datetime]:
        """获取水位线"""
        
    async def _dual_write(
        self, community_name: str, posts: List[RedditPost]
    ) -> Tuple[int, int, int]:
        """冷热双写"""
        
    async def _update_watermark(
        self,
        community_name: str,
        last_seen_post_id: str,
        last_seen_created_at: datetime,
        total_fetched: int,
        new_valid_posts: int,
        dedup_rate: float,
    ) -> None:
        """更新水位线"""
```

---

### 4.2 RedditAPIClient（Reddit API客户端）

**文件**: `backend/app/services/reddit_client.py`

#### 核心方法

```python
class RedditAPIClient:
    async def fetch_subreddit_posts(
        self,
        subreddit: str,
        limit: int = 100,
        time_filter: str = "month",
        sort: str = "top",
    ) -> List[RedditPost]:
        """抓取子版块帖子"""
```

#### 限流配置

```python
rate_limit = 60                    # 每分钟60次请求
rate_limit_window = 60             # 时间窗口60秒
request_timeout = 30               # 请求超时30秒
max_concurrency = 10               # 最大并发数10
```

---

### 4.3 TieredScheduler（分层调度器）

**文件**: `backend/app/services/tiered_scheduler.py`

#### Tier配置

```python
TIER_CONFIG = {
    "tier1": TierDefinition(
        name="高活跃（Tier 1）",
        threshold_min=Decimal("20"),      # avg_valid_posts >= 20
        threshold_max=None,
        frequency_hours=2,                # 每2小时抓取一次
        sort="new",                       # 最新优先
        time_filter="week",               # 最近1周
        limit=50,                         # 每次50条
    ),
    "tier2": TierDefinition(
        name="中活跃（Tier 2）",
        threshold_min=Decimal("10"),      # 10 <= avg_valid_posts < 20
        threshold_max=Decimal("20"),
        frequency_hours=6,                # 每6小时抓取一次
        sort="top",                       # 热门优先
        time_filter="week",               # 最近1周
        limit=80,                         # 每次80条
    ),
    "tier3": TierDefinition(
        name="低活跃（Tier 3）",
        threshold_min=Decimal("0"),       # 0 <= avg_valid_posts < 10
        threshold_max=Decimal("10"),
        frequency_hours=24,               # 每24小时抓取一次
        sort="top",                       # 热门优先
        time_filter="month",              # 最近1个月
        limit=100,                        # 每次100条
    ),
}
```

#### 核心方法

```python
class TieredScheduler:
    async def calculate_assignments(self) -> dict[str, list[str]]:
        """计算Tier分配"""
        
    async def apply_assignments(self, assignments: dict[str, list[str]]) -> None:
        """应用Tier分配到community_cache表"""
```

---

## 5. 数据流转

### 5.1 数据表关系

```
CommunityPool (社区池)
  ├─ name: string (r/webdev)
  ├─ tier: string (high/medium/low)
  ├─ categories: JSONB
  ├─ quality_score: float
  └─ is_active: boolean
  
  ↓ (抓取调度)
  
CommunityCache (社区元数据)
  ├─ community_name: string
  ├─ last_crawled_at: datetime
  ├─ last_seen_post_id: string (水位线)
  ├─ last_seen_created_at: datetime (水位线)
  ├─ posts_cached: int
  ├─ avg_valid_posts: int (用于Tier分配)
  ├─ quality_tier: string (tier1/tier2/tier3)
  ├─ crawl_frequency_hours: int
  ├─ empty_hit: int (空结果次数)
  ├─ success_hit: int (成功次数)
  └─ failure_hit: int (失败次数)
  
  ↓ (抓取数据)
  
PostRaw (冷库，持久化)
  ├─ source: string (reddit)
  ├─ source_post_id: string
  ├─ subreddit: string
  ├─ title: string
  ├─ content: text
  ├─ score: int
  ├─ num_comments: int
  ├─ created_at: datetime
  ├─ text_norm_hash: string (去重键)
  ├─ version: int (SCD2版本)
  └─ extra_data: JSONB
  
PostHot (热缓存，24小时TTL)
  ├─ source: string
  ├─ source_post_id: string
  ├─ subreddit: string
  ├─ title: string
  ├─ content: text
  ├─ score: int
  ├─ created_at: datetime
  ├─ expires_at: datetime (TTL)
  └─ extra_data: JSONB
  
CrawlMetrics (抓取指标)
  ├─ metric_date: date
  ├─ metric_hour: int
  ├─ cache_hit_rate: float
  ├─ valid_posts_24h: int
  ├─ total_communities: int
  ├─ successful_crawls: int
  ├─ empty_crawls: int
  ├─ failed_crawls: int
  ├─ avg_latency_seconds: float
  ├─ total_new_posts: int
  ├─ total_updated_posts: int
  ├─ total_duplicates: int
  └─ tier_assignments: JSONB
```

---

## 6. 分层调度策略

### 6.1 Tier分配流程

```
1. 计算滚动平均 avg_valid_posts
   ↓
2. 根据阈值分配Tier
   ├─ avg_valid_posts >= 20 → Tier 1
   ├─ 10 <= avg_valid_posts < 20 → Tier 2
   └─ 0 <= avg_valid_posts < 10 → Tier 3
   ↓
3. 更新 community_cache 表
   ├─ quality_tier
   └─ crawl_frequency_hours
```

### 6.2 抓取策略差异

| Tier | 频率 | 排序 | 时间范围 | 每次抓取数 | 适用场景 |
|------|------|------|----------|-----------|----------|
| Tier 1 | 2小时 | new | week | 50 | 高活跃社区，实时性优先 |
| Tier 2 | 6小时 | top | week | 80 | 中等活跃，平衡热门与新增 |
| Tier 3 | 24小时 | top | month | 100 | 低活跃，覆盖历史内容 |

---

## 7. 监控与维护

### 7.1 监控任务

**文件**: `backend/app/tasks/monitoring_task.py`

#### 监控指标

```python
# 1. API调用监控（每分钟）
@celery_app.task(name="tasks.monitoring.monitor_api_calls")
def monitor_api_calls() -> Dict[str, Any]:
    """监控Reddit API调用频率"""
    # 阈值：55次/分钟
    
# 2. 缓存健康监控（每5分钟）
@celery_app.task(name="tasks.monitoring.monitor_cache_health")
def monitor_cache_health() -> Dict[str, Any]:
    """监控缓存命中率"""
    # 阈值：70%
    
# 3. Warmup期监控（每15分钟）
@celery_app.task(name="tasks.monitoring.monitor_warmup_metrics")
def monitor_warmup_metrics() -> Dict[str, Any]:
    """监控Warmup期指标"""
```

### 7.2 维护任务

**文件**: `backend/app/tasks/maintenance_task.py`

```python
# 清理过期热缓存（每6小时）
@celery_app.task(name="tasks.maintenance.cleanup_expired_posts_hot")
def cleanup_expired_posts_hot() -> dict[str, Any]:
    """删除 expires_at < NOW() 的 PostHot 记录"""
```

---

## 总结

### 抓取系统特点

1. **双模式抓取**: 旧版（只写Redis）+ 增量（冷热双写）
2. **水位线机制**: 避免重复抓取，提升效率
3. **分层调度**: 根据社区活跃度动态调整抓取频率
4. **去重策略**: 基于 `(source, source_post_id, text_norm_hash)` 三元组
5. **SCD2版本追踪**: 记录帖子更新历史
6. **监控告警**: API限流、缓存健康、抓取失败

### 性能优化

- 并发控制：信号量限制并发数=2（避免数据库冲突）
- 批量处理：每批12个社区
- 缓存优先：先读Redis，再读数据库
- 水位线过滤：只抓取新帖子
- Tier分层：高活跃社区高频抓取，低活跃社区低频抓取

---

## 8. 配置参数

### 8.1 环境变量

```bash
# 抓取配置
CRAWLER_BATCH_SIZE=12                    # 每批抓取社区数
CRAWLER_MAX_CONCURRENCY=2                # 最大并发数
CRAWLER_POST_LIMIT=100                   # 每个社区抓取帖子数
CRAWLER_TIME_FILTER=month                # 时间范围（week/month/year/all）
CRAWLER_SORT=top                         # 排序策略（top/new/hot/rising）
HOT_CACHE_TTL_HOURS=24                   # 热缓存TTL（小时）

# Reddit API配置
REDDIT_CLIENT_ID=<your_client_id>
REDDIT_CLIENT_SECRET=<your_client_secret>
REDDIT_USER_AGENT=<your_user_agent>
REDDIT_RATE_LIMIT=60                     # 每分钟请求数
REDDIT_RATE_LIMIT_WINDOW_SECONDS=60      # 限流时间窗口
REDDIT_REQUEST_TIMEOUT_SECONDS=30        # 请求超时
REDDIT_MAX_CONCURRENCY=10                # API最大并发数

# Celery配置
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
CELERY_WORKER_COUNT=4                    # Worker并发数
CELERY_QUEUE_NAMES=analysis_queue,crawler_queue,monitoring_queue

# 监控配置
MONITOR_API_THRESHOLD=55                 # API调用阈值
MONITOR_CACHE_HIT_THRESHOLD=0.70         # 缓存命中率阈值
MONITOR_CRAWL_STALE_MINUTES=90           # 抓取过期时间（分钟）
```

### 8.2 数据库配置

```python
# 社区池文件
SEED_FILE = "backend/data/community_expansion_200.json"

# 数据库表
- community_pool: 社区池（200个社区）
- community_cache: 社区元数据与水位线
- posts_raw: 冷库（持久化存储）
- posts_hot: 热缓存（24小时TTL）
- crawl_metrics: 抓取指标
```

---

## 9. 常见问题

### 9.1 如何手动触发抓取？

```python
# 方法1：通过Celery任务
from app.tasks.crawler_task import crawl_seed_communities
result = crawl_seed_communities.delay(force_refresh=True)

# 方法2：通过CLI
celery -A app.core.celery_app call tasks.crawler.crawl_seed_communities

# 方法3：单社区抓取
from app.tasks.crawler_task import crawl_community
result = crawl_community.delay("r/Entrepreneur")
```

### 9.2 如何查看抓取指标？

```sql
-- 查看最近的抓取指标
SELECT * FROM crawl_metrics
ORDER BY metric_date DESC, metric_hour DESC
LIMIT 10;

-- 查看社区抓取状态
SELECT
    community_name,
    last_crawled_at,
    avg_valid_posts,
    quality_tier,
    crawl_frequency_hours,
    empty_hit,
    success_hit,
    failure_hit
FROM community_cache
ORDER BY avg_valid_posts DESC
LIMIT 20;
```

### 9.3 如何调整Tier分配？

```python
# 手动触发Tier重新计算
from app.services.tiered_scheduler import TieredScheduler
from app.db.session import SessionFactory

async with SessionFactory() as db:
    scheduler = TieredScheduler(db)
    assignments = await scheduler.calculate_assignments()
    await scheduler.apply_assignments(assignments)
```

### 9.4 如何清理过期数据？

```python
# 手动触发清理任务
from app.tasks.maintenance_task import cleanup_expired_posts_hot
result = cleanup_expired_posts_hot.delay()
```

---

## 10. 抓取流程图

### 10.1 增量抓取完整流程

```
┌─────────────────────────────────────────────────────────────┐
│ Celery Beat 定时触发                                         │
│ auto-crawl-incremental (每30分钟)                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ crawl_seed_communities_incremental()                        │
│ 1. 加载社区池（CommunityPoolLoader）                         │
│ 2. 筛选活跃社区（tier: high/medium/low）                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 并发抓取（信号量控制并发数=2）                               │
│ for each community:                                         │
│   IncrementalCrawler.crawl_community_incremental()          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤1：获取水位线                                            │
│ SELECT last_seen_created_at FROM community_cache            │
│ WHERE community_name = ?                                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤2：抓取新帖子                                            │
│ RedditAPIClient.fetch_subreddit_posts()                     │
│ - limit: 100                                                │
│ - time_filter: month                                        │
│ - sort: top                                                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤3：过滤新帖子                                            │
│ posts = [p for p in posts                                   │
│          if p.created_utc > watermark]                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤4：冷热双写                                              │
│ 4.1 写冷库（PostRaw）                                        │
│     - UPSERT 去重                                            │
│     - 去重键：(source, source_post_id, text_norm_hash)       │
│     - SCD2版本追踪（version += 1）                           │
│ 4.2 写热缓存（PostHot）                                      │
│     - TTL: 24小时                                            │
│     - expires_at = NOW() + 24h                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤5：更新水位线                                            │
│ UPDATE community_cache SET                                  │
│   last_seen_post_id = ?,                                    │
│   last_seen_created_at = ?,                                 │
│   last_crawled_at = NOW(),                                  │
│   success_hit = success_hit + 1,                            │
│   avg_valid_posts = (滚动平均)                               │
│ WHERE community_name = ?                                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤6：记录抓取指标                                          │
│ INSERT INTO crawl_metrics (...)                             │
│ VALUES (                                                    │
│   successful_crawls = 1,                                    │
│   total_new_posts = ?,                                      │
│   total_updated_posts = ?,                                  │
│   total_duplicates = ?,                                     │
│   avg_latency_seconds = ?                                   │
│ )                                                           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 步骤7：计算Tier分配                                          │
│ TieredScheduler.calculate_assignments()                     │
│ - 根据 avg_valid_posts 分配Tier                              │
│ - 更新 quality_tier, crawl_frequency_hours                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 返回结果                                                     │
│ {                                                           │
│   "community": "r/Entrepreneur",                            │
│   "new_posts": 15,                                          │
│   "updated_posts": 3,                                       │
│   "duplicates": 2,                                          │
│   "watermark_updated": true,                                │
│   "duration_seconds": 2.5                                   │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
```

---

**文档维护**: 本文档随抓取系统迭代更新，当前版本对应 Phase 3 完成状态。

