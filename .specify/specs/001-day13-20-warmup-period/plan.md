# Implementation Plan: Day 13-20 预热期与社区池扩展

**Feature ID**: 001-day13-20-warmup-period  
**Plan Version**: 1.0  
**Created**: 2025-10-15  
**Tech Lead**: Lead  
**PRD Reference**: PRD-09

---

## Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Reddit Signal Scanner                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │ Celery Beat  │─────▶│ Celery Worker│                    │
│  │  (Scheduler) │      │  (Crawler)   │                    │
│  └──────────────┘      └───────┬──────┘                    │
│                                 │                            │
│                                 ▼                            │
│                        ┌─────────────────┐                  │
│                        │  Reddit API     │                  │
│                        │  (60 req/min)   │                  │
│                        └────────┬────────┘                  │
│                                 │                            │
│                    ┌────────────┴────────────┐              │
│                    ▼                         ▼              │
│           ┌─────────────┐          ┌──────────────┐        │
│           │   Redis     │          │ PostgreSQL   │        │
│           │  (Cache)    │          │ (Metadata)   │        │
│           └─────────────┘          └──────────────┘        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Community Discovery Service                 │  │
│  │  (TF-IDF + Reddit Search + Admin Approval)           │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Adaptive Crawler Service                    │  │
│  │  (Dynamic frequency based on cache hit rate)         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend Services**:
- Python 3.11+
- Celery 5.3+ (task queue)
- Redis 5.0+ (broker + cache)
- PostgreSQL 15+ (metadata)
- PRAW (Python Reddit API Wrapper)

**New Components**:
- `backend/app/services/community_pool_loader.py` - 加载种子社区
- `backend/app/services/community_discovery.py` - 发现新社区
- `backend/app/services/adaptive_crawler.py` - 自适应爬虫
- `backend/app/tasks/warmup_crawler.py` - 预热爬虫任务
- `backend/app/tasks/monitoring_task.py` - 监控任务
- `backend/app/api/routes/admin_community_pool.py` - Admin API

**Database Schema Extensions**:
```sql
-- 新增表
CREATE TABLE discovered_communities (
    id UUID PRIMARY KEY,
    community_name VARCHAR(100) NOT NULL,
    discovered_from_task_id UUID REFERENCES tasks(id),
    keywords TEXT[],
    discovery_count INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'pending', -- pending/approved/rejected
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    reviewed_by UUID REFERENCES users(id)
);

-- 扩展现有表
ALTER TABLE community_cache ADD COLUMN priority INTEGER DEFAULT 5;
ALTER TABLE community_cache ADD COLUMN crawl_frequency_hours INTEGER DEFAULT 2;
ALTER TABLE community_cache ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
```

---

## Implementation Details

### Phase 1: Database & Models (Day 13 上午)

**Files to Create/Modify**:
- `backend/alembic/versions/00X_add_community_pool_tables.py`
- `backend/app/models/discovered_community.py`
- `backend/app/schemas/community_pool.py`

**Implementation**:
1. Create Alembic migration for new tables
2. Add `DiscoveredCommunity` model
3. Add Pydantic schemas for API validation
4. Run migration: `alembic upgrade head`

**Acceptance**:
- [ ] Migration runs successfully
- [ ] Tables created in database
- [ ] Models pass mypy --strict
- [ ] Unit tests for models pass

---

### Phase 2: Community Pool Loader (Day 13 上午)

**Files to Create**:
- `backend/app/services/community_pool_loader.py`
- `backend/data/seed_communities.json`
- `backend/tests/services/test_community_pool_loader.py`

**Implementation**:
```python
# backend/app/services/community_pool_loader.py
class CommunityPoolLoader:
    async def load_seed_communities(self) -> list[str]:
        """从 JSON 文件加载种子社区列表"""
        
    async def initialize_community_cache(
        self, 
        communities: list[str]
    ) -> None:
        """初始化社区缓存元数据"""
```

**Seed Communities** (100 个):
```json
{
  "high_priority": [
    "r/artificial", "r/startups", "r/entrepreneur",
    "r/saas", "r/ProductManagement", ...
  ],
  "medium_priority": [...],
  "low_priority": [...]
}
```

**Acceptance**:
- [ ] Loader can read seed communities from JSON
- [ ] Can initialize community_cache records
- [ ] Unit tests pass (100% coverage)
- [ ] mypy --strict passes

---

### Phase 3: Warmup Crawler Task (Day 13 下午)

**Files to Create**:
- `backend/app/tasks/warmup_crawler.py`
- `backend/tests/tasks/test_warmup_crawler.py`

**Implementation**:
```python
@celery_app.task(name="tasks.warmup.crawl_seed_communities")
async def crawl_seed_communities() -> dict[str, Any]:
    """
    预热爬虫：爬取种子社区
    
    策略：
    - 100 个种子社区
    - 每个社区 100 个帖子 (top/week)
    - 遵守 60 次/分钟限制
    - 存入 Redis + 更新 PostgreSQL
    """
    rate_limiter = RateLimiter(max_calls=58, period=60)
    
    for community in seed_communities:
        await rate_limiter.acquire()
        posts = await reddit_client.fetch_subreddit_posts(
            community, limit=100, time_filter="week", sort="top"
        )
        await cache_manager.set_cached_posts(community, posts)
        await update_community_cache_metadata(community, len(posts))
```

**Rate Limiting**:
- Use `aiolimiter` library
- Max 58 calls/minute (safety margin)
- Exponential backoff on errors

**Acceptance**:
- [ ] Can crawl 100 communities in < 2 minutes
- [ ] Rate limit never exceeded
- [ ] Data stored in Redis + PostgreSQL
- [ ] Error handling with 3 retries
- [ ] Integration test passes

---

### Phase 4: Celery Beat Configuration (Day 13 下午)

**Files to Modify**:
- `backend/app/core/celery_app.py`
- `backend/app/core/config.py`

**Implementation**:
```python
# backend/app/core/celery_app.py
celery_app.conf.beat_schedule = {
    'warmup-crawl-seed-communities': {
        'task': 'tasks.warmup.crawl_seed_communities',
        'schedule': crontab(minute='0', hour='*/2'),  # 每 2 小时
    },
    'monitor-warmup-metrics': {
        'task': 'tasks.monitoring.monitor_warmup_metrics',
        'schedule': crontab(minute='*/15'),  # 每 15 分钟
    },
}
```

**Acceptance**:
- [ ] Celery Beat starts successfully
- [ ] Tasks execute on schedule
- [ ] Logs show task execution
- [ ] No errors in worker logs

---

### Phase 5: Community Discovery Service (Day 14-15)

**Files to Create**:
- `backend/app/services/community_discovery.py`
- `backend/tests/services/test_community_discovery.py`

**Implementation**:
```python
class CommunityDiscoveryService:
    async def discover_from_product_description(
        self, 
        task_id: UUID,
        product_description: str
    ) -> list[str]:
        """
        从产品描述中发现相关社区
        
        步骤：
        1. 提取关键词 (TF-IDF)
        2. Reddit Search API 搜索帖子
        3. 统计社区来源
        4. 记录到 discovered_communities 表
        """
        keywords = await self.extract_keywords(product_description)
        posts = await self.search_reddit_posts(keywords, limit=100)
        communities = self.extract_communities(posts)
        await self.record_discoveries(task_id, keywords, communities)
        return communities
```

**Acceptance**:
- [ ] Can extract keywords from text
- [ ] Can search Reddit posts
- [ ] Can record discoveries to database
- [ ] Unit tests pass
- [ ] Integration test with real Reddit API

---

### Phase 6: Admin Community Pool API (Day 15)

**Files to Create**:
- `backend/app/api/routes/admin_community_pool.py`
- `backend/tests/api/test_admin_community_pool.py`

**API Endpoints**:
```python
GET    /api/admin/communities/pool          # 查看社区池
GET    /api/admin/communities/discovered    # 查看待审核社区
POST   /api/admin/communities/approve       # 批准社区
POST   /api/admin/communities/reject        # 拒绝社区
DELETE /api/admin/communities/{name}        # 禁用社区
```

**Acceptance**:
- [ ] All endpoints return correct data
- [ ] Admin authentication required
- [ ] Non-admin users get 403
- [ ] API tests pass
- [ ] OpenAPI docs updated

---

### Phase 7: Adaptive Crawler Service (Day 16)

**Files to Create**:
- `backend/app/services/adaptive_crawler.py`
- `backend/tests/services/test_adaptive_crawler.py`

**Implementation**:
```python
class AdaptiveCrawler:
    async def adjust_crawl_frequency(self) -> None:
        """
        根据缓存命中率动态调整爬虫频率
        
        策略：
        - 缓存命中率 > 90%: 降低频率到每 4 小时
        - 缓存命中率 70-90%: 保持每 2 小时
        - 缓存命中率 < 70%: 提高到每 1 小时
        """
        cache_hit_rate = await self.get_cache_hit_rate()
        
        if cache_hit_rate > 0.9:
            await self.set_crawl_interval(hours=4)
        elif cache_hit_rate < 0.7:
            await self.set_crawl_interval(hours=1)
        else:
            await self.set_crawl_interval(hours=2)
```

**Acceptance**:
- [ ] Can calculate cache hit rate
- [ ] Can adjust Celery Beat schedule dynamically
- [ ] Logs frequency changes
- [ ] Unit tests pass

---

### Phase 8: Monitoring & Alerting (Day 16-17)

**Files to Create**:
- `backend/app/tasks/monitoring_task.py`
- `backend/app/services/alert_service.py`
- `backend/tests/tasks/test_monitoring_task.py`

**Metrics to Monitor**:
- API calls per minute
- Cache hit rate
- Average analysis time
- System resources (memory/CPU)
- User satisfaction

**Alerts**:
- API calls > 55/min → Pause new registrations
- Cache hit rate < 70% → Increase crawler frequency
- Memory > 1.8GB → Alert admin

**Acceptance**:
- [ ] Monitoring task runs every 15 minutes
- [ ] Metrics stored in database
- [ ] Alerts triggered correctly
- [ ] Integration test passes

---

### Phase 9: Beta Testing Infrastructure (Day 17-18)

**Files to Create**:
- `backend/scripts/create_beta_users.py`
- `backend/app/api/routes/beta_feedback.py`

**Beta User Management**:
```bash
python backend/scripts/create_beta_users.py \
  --emails "user1@test.com,user2@test.com" \
  --role "beta_tester"
```

**Feedback API**:
```python
POST /api/beta/feedback
{
  "task_id": "uuid",
  "satisfaction": 4,
  "missing_communities": ["r/example"],
  "comments": "Great tool!"
}
```

**Acceptance**:
- [ ] Can create beta users
- [ ] Beta users can submit feedback
- [ ] Feedback stored in database
- [ ] Admin can view feedback

---

### Phase 10: Warmup Report Generator (Day 19)

**Files to Create**:
- `backend/scripts/generate_warmup_report.py`
- `backend/tests/scripts/test_warmup_report.py`

**Report Contents**:
```json
{
  "warmup_period": "Day 13-19 (7 days)",
  "community_pool": {
    "seed_communities": 100,
    "discovered_communities": 150,
    "total": 250
  },
  "cache_metrics": {
    "total_posts_cached": 25000,
    "cache_hit_rate": 0.92,
    "avg_cache_age_hours": 6
  },
  "api_usage": {
    "total_calls": 15000,
    "avg_calls_per_minute": 35,
    "peak_calls_per_minute": 58
  },
  "user_testing": {
    "internal_users": 10,
    "beta_users": 45,
    "total_analyses": 180,
    "avg_satisfaction": 4.3
  },
  "system_performance": {
    "avg_analysis_time_seconds": 155,
    "p95_analysis_time_seconds": 180,
    "uptime_percentage": 99.8
  }
}
```

**Acceptance**:
- [ ] Report generates successfully
- [ ] All metrics accurate
- [ ] Saved to `reports/warmup-report.json`
- [ ] Human-readable summary printed

---

## Testing Strategy

### Unit Tests
- All services: 100% coverage
- All tasks: Mock Reddit API
- All models: Validation tests

### Integration Tests
- Reddit API integration (real API, rate-limited)
- Database operations (PostgreSQL + Redis)
- Celery task execution

### End-to-End Tests
- Complete warmup cycle (seed → crawl → cache)
- Community discovery flow (task → discover → approve → crawl)
- Adaptive crawler adjustment

### Performance Tests
- Crawl 100 communities in < 2 minutes
- Rate limit compliance (< 60 req/min)
- Cache write latency < 100ms

---

## Deployment Plan

### Day 13 Morning
1. Deploy database migrations
2. Deploy community pool loader
3. Load seed communities

### Day 13 Afternoon
4. Deploy warmup crawler
5. Start Celery Beat
6. Monitor first crawl cycle

### Day 14-15
7. Deploy community discovery
8. Deploy admin API
9. Internal testing begins

### Day 16-17
10. Deploy adaptive crawler
11. Deploy monitoring
12. Beta testing begins

### Day 18-19
13. Monitor and optimize
14. Generate warmup report
15. Prepare for Day 20 launch

---

## Risk Mitigation

### Risk 1: Reddit API Rate Limit Exceeded
**Mitigation**: 
- Use 58 req/min limit (safety margin)
- Implement circuit breaker
- Alert at 55 req/min

### Risk 2: Cache Hit Rate Below Target
**Mitigation**:
- Adaptive crawler increases frequency
- Manual community addition via Admin
- Extend warmup period if needed

### Risk 3: System Resource Exhaustion
**Mitigation**:
- Monitor memory/CPU every 15 minutes
- Limit concurrent crawlers to 2
- Auto-scale if needed

### Risk 4: Data Quality Issues
**Mitigation**:
- Validate all Reddit API responses
- Retry failed requests (3x)
- Log all errors for review

---

## Success Criteria

### Day 14 (Seed Communities)
- [ ] 100 communities cached
- [ ] Cache hit rate 100% (for seeds)
- [ ] 0 API rate limit violations

### Day 16 (Internal Testing)
- [ ] 150 communities in pool
- [ ] Cache hit rate > 80%
- [ ] 10 internal users tested

### Day 18 (Beta Testing)
- [ ] 250 communities in pool
- [ ] Cache hit rate > 85%
- [ ] 50 beta users tested
- [ ] User satisfaction > 4.0

### Day 19 (Final Validation)
- [ ] Cache hit rate > 90%
- [ ] Avg analysis time < 3 minutes
- [ ] System uptime > 99.5%
- [ ] Warmup report generated

---

**Next Step**: Generate task breakdown (`/speckit.tasks`)

