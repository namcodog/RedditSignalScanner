# Task Breakdown: Day 13-20 预热期与社区池扩展

**Feature ID**: 001-day13-20-warmup-period  
**Tasks Version**: 1.0  
**Created**: 2025-10-15  
**Execution Mode**: Sequential with parallel markers

---

## Task Execution Rules

- **Sequential**: Tasks must be completed in order unless marked [P]
- **Parallel**: Tasks marked [P] can run in parallel with previous task
- **Checkpoint**: ✓ marks validation points - must verify before proceeding
- **Dependencies**: Listed explicitly for each task
- **Estimated Time**: Provided for planning purposes

---

## Phase 1: Database & Models (Day 13 上午, ~2 hours) ✅ 已完成

**完成日期**: 2025-10-15
**技术债清零**: ✅ 已完成（详见 `phase-1-2-3-tech-debt-clearance.md`）
**验证命令**: `make phase-1-2-3-verify`

### Task 1.1: Create Database Migration
**File**: `backend/alembic/versions/00X_add_community_pool_tables.py`  
**Dependencies**: None  
**Estimated Time**: 30 minutes

**Steps**:
1. Create new Alembic migration file
2. Add `discovered_communities` table
3. Add columns to `community_cache` table (priority, crawl_frequency_hours, is_active)
4. Add indexes for performance

**Validation**:
```bash
cd backend
alembic upgrade head
# Should complete without errors
psql -U postgres -d reddit_scanner -c "\d discovered_communities"
# Should show table structure
```

**Acceptance**:
- [ ] Migration file created
- [ ] Migration runs successfully
- [ ] Tables created in database
- [ ] Indexes created

---

### Task 1.2: Create DiscoveredCommunity Model
**File**: `backend/app/models/discovered_community.py`  
**Dependencies**: Task 1.1  
**Estimated Time**: 20 minutes

**Steps**:
1. Create SQLAlchemy model for `discovered_communities`
2. Add relationships to `tasks` and `users` tables
3. Add type annotations (mypy --strict)

**Validation**:
```bash
cd backend
mypy app/models/discovered_community.py --strict
# Should pass with 0 errors
```

**Acceptance**:
- [ ] Model created with all fields
- [ ] Relationships defined
- [ ] mypy --strict passes

---

### Task 1.3: Create Pydantic Schemas
**File**: `backend/app/schemas/community_pool.py`  
**Dependencies**: Task 1.2  
**Estimated Time**: 30 minutes

**Steps**:
1. Create `DiscoveredCommunityCreate` schema
2. Create `DiscoveredCommunityResponse` schema
3. Create `CommunityPoolStats` schema
4. Add validation rules

**Validation**:
```bash
cd backend
mypy app/schemas/community_pool.py --strict
python -c "from app.schemas.community_pool import *; print('✅ Schemas import successfully')"
```

**Acceptance**:
- [ ] All schemas created
- [ ] Validation rules added
- [ ] mypy --strict passes
- [ ] Schemas can be imported

---

### Task 1.4: Write Unit Tests for Models
**File**: `backend/tests/models/test_discovered_community.py`  
**Dependencies**: Task 1.2  
**Estimated Time**: 40 minutes

**Steps**:
1. Test model creation
2. Test relationships
3. Test constraints
4. Test validation

**Validation**:
```bash
cd backend
pytest tests/models/test_discovered_community.py -v
# Should pass all tests
```

**Acceptance**:
- [ ] All tests pass
- [ ] Coverage > 90%

**✓ Checkpoint 1**: Database schema and models complete

---

## Phase 2: Community Pool Loader (Day 13 上午, ~2 hours) ✅ 已完成

**完成日期**: 2025-10-15
**技术债清零**: ✅ 已完成（详见 `phase-1-2-3-tech-debt-clearance.md`）
**验证命令**: `make phase-1-2-3-verify`

### Task 2.1: Create Seed Communities Data
**File**: `backend/data/seed_communities.json`  
**Dependencies**: None  
**Estimated Time**: 30 minutes

**Steps**:
1. Research and compile 100 seed communities
2. Categorize by priority (high/medium/low)
3. Create JSON file with structure

**Validation**:
```bash
cd backend
python -c "import json; data=json.load(open('data/seed_communities.json')); print(f'✅ {sum(len(v) for v in data.values())} communities loaded')"
# Should show 100 communities
```

**Acceptance**:
- [ ] 100 communities listed
- [ ] Valid JSON format
- [ ] Categorized by priority

---

### Task 2.2: Implement CommunityPoolLoader Service
**File**: `backend/app/services/community_pool_loader.py`  
**Dependencies**: Task 1.3, Task 2.1  
**Estimated Time**: 1 hour

**Steps**:
1. Create `CommunityPoolLoader` class
2. Implement `load_seed_communities()` method
3. Implement `initialize_community_cache()` method
4. Add error handling and logging

**Validation**:
```bash
cd backend
mypy app/services/community_pool_loader.py --strict
python -c "from app.services.community_pool_loader import CommunityPoolLoader; print('✅ Service imports successfully')"
```

**Acceptance**:
- [ ] Service created
- [ ] Methods implemented
- [ ] mypy --strict passes
- [ ] Logging added

---

### Task 2.3: Write Unit Tests for Loader
**File**: `backend/tests/services/test_community_pool_loader.py`  
**Dependencies**: Task 2.2  
**Estimated Time**: 30 minutes

**Steps**:
1. Test loading seed communities
2. Test initializing cache
3. Test error handling
4. Mock database operations

**Validation**:
```bash
cd backend
pytest tests/services/test_community_pool_loader.py -v
```

**Acceptance**:
- [ ] All tests pass
- [ ] Coverage > 90%

**✓ Checkpoint 2**: Community pool loader complete

---

## Phase 3: Warmup Crawler Task (Day 13 下午, ~3 hours) ✅ 已完成

**完成日期**: 2025-10-15
**技术债清零**: ✅ 已完成（详见 `phase-1-2-3-tech-debt-clearance.md`）
**验证命令**: `make phase-1-2-3-verify`
**关键修复**: Redis 帖子缓存已实现（使用统一的 RedditAPIClient + CacheManager）

### Task 3.1: Install PRAW Library
**File**: `backend/requirements.txt`  
**Dependencies**: None  
**Estimated Time**: 10 minutes

**Steps**:
1. Add `praw>=7.7.0` to requirements.txt
2. Add `aiolimiter>=1.1.0` for rate limiting
3. Install dependencies

**Validation**:
```bash
cd backend
pip install -r requirements.txt
python -c "import praw; import aiolimiter; print('✅ Libraries installed')"
```

**Acceptance**:
- [ ] Libraries added to requirements.txt
- [ ] Libraries installed successfully

---

### Task 3.2: Create Reddit Client Wrapper
**File**: `backend/app/clients/reddit_client.py`  
**Dependencies**: Task 3.1  
**Estimated Time**: 1 hour

**Steps**:
1. Create `RedditClient` class
2. Implement OAuth2 authentication
3. Implement `fetch_subreddit_posts()` method
4. Add rate limiting (58 req/min)
5. Add error handling and retries

**Validation**:
```bash
cd backend
mypy app/clients/reddit_client.py --strict
# Test with real Reddit API (manual)
python -c "
from app.clients.reddit_client import RedditClient
import asyncio
async def test():
    client = RedditClient()
    posts = await client.fetch_subreddit_posts('artificial', limit=10)
    print(f'✅ Fetched {len(posts)} posts')
asyncio.run(test())
"
```

**Acceptance**:
- [ ] Client created
- [ ] Rate limiting works
- [ ] Can fetch posts from Reddit
- [ ] mypy --strict passes

---

### Task 3.3: Implement Warmup Crawler Task
**File**: `backend/app/tasks/warmup_crawler.py`  
**Dependencies**: Task 2.2, Task 3.2  
**Estimated Time**: 1.5 hours

**Steps**:
1. Create `crawl_seed_communities` Celery task
2. Load seed communities
3. Crawl each community with rate limiting
4. Store posts in Redis
5. Update community_cache metadata
6. Add comprehensive logging

**Validation**:
```bash
cd backend
mypy app/tasks/warmup_crawler.py --strict
# Manual test (requires Redis + Celery)
celery -A app.core.celery_app worker --loglevel=info &
python -c "from app.tasks.warmup_crawler import crawl_seed_communities; crawl_seed_communities.delay()"
```

**Acceptance**:
- [ ] Task created
- [ ] Can crawl communities
- [ ] Rate limit respected
- [ ] Data stored correctly
- [ ] mypy --strict passes

---

### Task 3.4: Write Integration Tests for Crawler
**File**: `backend/tests/tasks/test_warmup_crawler.py`  
**Dependencies**: Task 3.3  
**Estimated Time**: 30 minutes

**Steps**:
1. Mock Reddit API responses
2. Test successful crawl
3. Test rate limiting
4. Test error handling
5. Test data storage

**Validation**:
```bash
cd backend
pytest tests/tasks/test_warmup_crawler.py -v
```

**Acceptance**:
- [ ] All tests pass
- [ ] Coverage > 80%

**✓ Checkpoint 3**: Warmup crawler complete

---

## Phase 4: Celery Beat Configuration (Day 13 下午, ~1 hour)

### Task 4.1: Configure Celery Beat Schedule
**File**: `backend/app/core/celery_app.py`  
**Dependencies**: Task 3.3  
**Estimated Time**: 30 minutes

**Steps**:
1. Add beat_schedule configuration
2. Add warmup crawler task (every 2 hours)
3. Add monitoring task (every 15 minutes)
4. Test schedule configuration

**Validation**:
```bash
cd backend
celery -A app.core.celery_app beat --loglevel=info
# Should show scheduled tasks
```

**Acceptance**:
- [ ] Schedule configured
- [ ] Tasks appear in beat schedule
- [ ] Celery Beat starts successfully

---

### Task 4.2: Create Makefile Targets
**File**: `Makefile`  
**Dependencies**: Task 4.1  
**Estimated Time**: 30 minutes

**Steps**:
1. Add `warmup-start` target
2. Add `warmup-stop` target
3. Add `warmup-status` target
4. Add `warmup-logs` target

**Validation**:
```bash
make warmup-start
make warmup-status
# Should show running workers
make warmup-stop
```

**Acceptance**:
- [ ] All targets work
- [ ] Can start/stop warmup system
- [ ] Can view logs

**✓ Checkpoint 4**: Celery Beat configured

---

## Phase 5: Community Discovery Service (Day 14-15, ~4 hours)

### Task 5.1: Implement Keyword Extraction
**File**: `backend/app/services/keyword_extractor.py`  
**Dependencies**: None  
**Estimated Time**: 1 hour

**Steps**:
1. Install scikit-learn for TF-IDF
2. Create `KeywordExtractor` class
3. Implement TF-IDF extraction
4. Add stopwords filtering

**Validation**:
```bash
cd backend
python -c "
from app.services.keyword_extractor import KeywordExtractor
extractor = KeywordExtractor()
keywords = extractor.extract('AI-powered note-taking app for researchers')
print(f'✅ Extracted keywords: {keywords}')
"
```

**Acceptance**:
- [ ] Can extract keywords
- [ ] Stopwords filtered
- [ ] Returns relevant keywords

---

### Task 5.2: Implement Community Discovery Service
**File**: `backend/app/services/community_discovery.py`  
**Dependencies**: Task 3.2, Task 5.1  
**Estimated Time**: 2 hours

**Steps**:
1. Create `CommunityDiscoveryService` class
2. Implement `discover_from_product_description()` method
3. Use Reddit Search API
4. Extract communities from search results
5. Record to `discovered_communities` table

**Validation**:
```bash
cd backend
mypy app/services/community_discovery.py --strict
```

**Acceptance**:
- [ ] Service created
- [ ] Can discover communities
- [ ] Records to database
- [ ] mypy --strict passes

---

### Task 5.3: Write Unit Tests for Discovery
**File**: `backend/tests/services/test_community_discovery.py`  
**Dependencies**: Task 5.2  
**Estimated Time**: 1 hour

**Steps**:
1. Mock Reddit Search API
2. Test keyword extraction
3. Test community discovery
4. Test database recording

**Validation**:
```bash
cd backend
pytest tests/services/test_community_discovery.py -v
```

**Acceptance**:
- [ ] All tests pass
- [ ] Coverage > 85%

**✓ Checkpoint 5**: Community discovery complete

---

## Phase 6: Admin Community Pool API (Day 15, ~3 hours)

### Task 6.1: Implement Admin API Endpoints
**File**: `backend/app/api/routes/admin_community_pool.py`  
**Dependencies**: Task 1.3, Task 5.2  
**Estimated Time**: 2 hours

**Steps**:
1. Create router
2. Implement GET /api/admin/communities/pool
3. Implement GET /api/admin/communities/discovered
4. Implement POST /api/admin/communities/approve
5. Implement POST /api/admin/communities/reject
6. Implement DELETE /api/admin/communities/{name}
7. Add admin authentication check

**Validation**:
```bash
cd backend
mypy app/api/routes/admin_community_pool.py --strict
# Start server and test manually
curl http://localhost:8006/api/admin/communities/pool \
  -H "Authorization: Bearer <admin_token>"
```

**Acceptance**:
- [ ] All endpoints implemented
- [ ] Admin auth required
- [ ] mypy --strict passes
- [ ] OpenAPI docs updated

---

### Task 6.2: Write API Tests
**File**: `backend/tests/api/test_admin_community_pool.py`  
**Dependencies**: Task 6.1  
**Estimated Time**: 1 hour

**Steps**:
1. Test all endpoints
2. Test admin authentication
3. Test non-admin rejection
4. Test data validation

**Validation**:
```bash
cd backend
pytest tests/api/test_admin_community_pool.py -v
```

**Acceptance**:
- [ ] All tests pass
- [ ] Coverage > 90%

**✓ Checkpoint 6**: Admin API complete

---

## Phase 7: Adaptive Crawler & Monitoring (Day 16-17, ~4 hours)

### Task 7.1: Implement Cache Hit Rate Calculator
**File**: `backend/app/services/cache_metrics.py`  
**Dependencies**: None  
**Estimated Time**: 1 hour

**Steps**:
1. Create `CacheMetrics` class
2. Implement `calculate_hit_rate()` method
3. Track cache hits/misses in Redis
4. Add time-window aggregation

**Validation**:
```bash
cd backend
python -c "
from app.services.cache_metrics import CacheMetrics
import asyncio
async def test():
    metrics = CacheMetrics()
    rate = await metrics.calculate_hit_rate()
    print(f'✅ Cache hit rate: {rate:.2%}')
asyncio.run(test())
"
```

**Acceptance**:
- [ ] Can calculate hit rate
- [ ] Accurate tracking
- [ ] Time-window support

---

### Task 7.2: Implement Adaptive Crawler
**File**: `backend/app/services/adaptive_crawler.py`  
**Dependencies**: Task 7.1  
**Estimated Time**: 1.5 hours

**Steps**:
1. Create `AdaptiveCrawler` class
2. Implement `adjust_crawl_frequency()` method
3. Update Celery Beat schedule dynamically
4. Add logging for frequency changes

**Validation**:
```bash
cd backend
mypy app/services/adaptive_crawler.py --strict
```

**Acceptance**:
- [ ] Can adjust frequency
- [ ] Celery Beat schedule updates
- [ ] Logging works
- [ ] mypy --strict passes

---

### Task 7.3: Implement Monitoring Task
**File**: `backend/app/tasks/monitoring_task.py`  
**Dependencies**: Task 7.1  
**Estimated Time**: 1.5 hours

**Steps**:
1. Create `monitor_warmup_metrics` task
2. Collect all metrics (API calls, cache hit rate, etc.)
3. Check thresholds and trigger alerts
4. Store metrics in database

**Validation**:
```bash
cd backend
celery -A app.core.celery_app worker --loglevel=info &
python -c "from app.tasks.monitoring_task import monitor_warmup_metrics; monitor_warmup_metrics.delay()"
```

**Acceptance**:
- [ ] Task runs successfully
- [ ] Metrics collected
- [ ] Alerts triggered correctly

**✓ Checkpoint 7**: Adaptive crawler and monitoring complete

---

## Phase 8: Beta Testing & Reporting (Day 17-19, ~3 hours)

### Task 8.1: Create Beta User Script
**File**: `backend/scripts/create_beta_users.py`  
**Dependencies**: None  
**Estimated Time**: 30 minutes

**Steps**:
1. Create CLI script
2. Accept email list as argument
3. Create users with beta_tester role
4. Generate random passwords
5. Send welcome emails (optional)

**Validation**:
```bash
cd backend
python scripts/create_beta_users.py --emails "test1@example.com,test2@example.com"
# Should create 2 users
```

**Acceptance**:
- [ ] Script works
- [ ] Users created
- [ ] Passwords generated

---

### Task 8.2: Create Warmup Report Generator
**File**: `backend/scripts/generate_warmup_report.py`  
**Dependencies**: Task 7.1  
**Estimated Time**: 2 hours

**Steps**:
1. Create report generator script
2. Collect all warmup metrics
3. Generate JSON report
4. Generate human-readable summary
5. Save to `reports/warmup-report.json`

**Validation**:
```bash
cd backend
python scripts/generate_warmup_report.py
cat ../reports/warmup-report.json
# Should show complete report
```

**Acceptance**:
- [ ] Report generates
- [ ] All metrics included
- [ ] JSON and summary formats
- [ ] Saved to correct location

---

### Task 8.3: Write End-to-End Test
**File**: `backend/tests/e2e/test_warmup_cycle.py`  
**Dependencies**: All previous tasks  
**Estimated Time**: 30 minutes

**Steps**:
1. Test complete warmup cycle
2. Verify seed communities loaded
3. Verify crawler runs
4. Verify cache populated
5. Verify metrics collected

**Validation**:
```bash
cd backend
pytest tests/e2e/test_warmup_cycle.py -v
```

**Acceptance**:
- [ ] E2E test passes
- [ ] All components verified

**✓ Checkpoint 8**: Beta testing and reporting complete

---

## Final Validation Checklist

### Day 13 End
- [ ] Database migrations complete
- [ ] Seed communities loaded (100)
- [ ] Warmup crawler running
- [ ] First crawl cycle complete

### Day 15 End
- [ ] Community discovery working
- [ ] Admin API functional
- [ ] Internal testing complete (10 users)
- [ ] Community pool expanded (150)

### Day 17 End
- [ ] Adaptive crawler active
- [ ] Monitoring running
- [ ] Beta testing started (20-50 users)

### Day 19 End
- [ ] Cache hit rate > 90%
- [ ] Community pool size 250+
- [ ] Warmup report generated
- [ ] System ready for Day 20 launch

---

**Total Estimated Time**: ~25 hours (3-4 days with parallel work)  
**Next Step**: Begin execution with Task 1.1

