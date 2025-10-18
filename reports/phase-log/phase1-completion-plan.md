# Phase 1 收尾执行计划

**生成时间**: 2025-10-17 17:30:00  
**目标**: 完成 Phase 1 剩余任务，达到 100% 完成度  
**当前进度**: 2/8 任务完成（25%）  
**预计工时**: 6 小时

---

## 📊 当前状态评估

### 已完成任务 ✅

| 任务 | 状态 | 验证方式 |
|------|------|---------|
| T1.1: 完成剩余社区抓取 | ✅ COMPLETE | 200 个社区，12,068 条帖子 |
| T1.2: 扩展 community_cache 监控字段 | ✅ COMPLETE | 数据库迁移已执行 |
| T1.3: 创建 crawl_metrics 监控表 | ✅ COMPLETE | 表已创建，字段完整 |
| T1.5: 社区池扩容到 300 个 | ✅ PARTIAL | 已完成 200 个（目标 300） |
| T1.7: 实现分级调度策略 | ✅ CODE_COMPLETE | 代码已实现，测试通过 |
| T1.8: 实现精准补抓任务 | ✅ CODE_COMPLETE | 代码已实现，测试通过 |

### 待完成任务 ⏳

| 任务 | 状态 | 预计工时 | 优先级 |
|------|------|---------|--------|
| T1.4: 改造 IncrementalCrawler 埋点 | ⏳ NOT_STARTED | 2h | P0 |
| T1.6: 创建黑名单配置 | ⏳ NOT_STARTED | 1h | P1 |
| T1.7: 集成分级调度到 Celery Beat | ⏳ NOT_STARTED | 1h | P1 |
| T1.8: 集成精准补抓到 Celery Beat | ⏳ NOT_STARTED | 1h | P1 |
| Phase 1 验收测试 | ⏳ NOT_STARTED | 1h | P0 |

---

## 🎯 执行计划（测试驱动）

### 步骤 1: T1.4 - 改造 IncrementalCrawler 埋点（2h）

**目标**: 在抓取器中添加监控埋点，记录成功/空结果/失败

**测试先行**:
```python
# backend/tests/services/test_incremental_crawler_metrics.py

@pytest.mark.asyncio
async def test_crawler_records_success_metrics():
    """测试成功抓取时记录 success_hit"""
    # 模拟成功抓取（返回 10 条帖子）
    # 验证 community_cache.success_hit += 1
    # 验证 community_cache.avg_valid_posts 更新
    pass

@pytest.mark.asyncio
async def test_crawler_records_empty_metrics():
    """测试空结果时记录 empty_hit"""
    # 模拟空结果（返回 0 条帖子）
    # 验证 community_cache.empty_hit += 1
    pass

@pytest.mark.asyncio
async def test_crawler_records_failure_metrics():
    """测试失败时记录 failure_hit"""
    # 模拟 API 错误
    # 验证 community_cache.failure_hit += 1
    pass

@pytest.mark.asyncio
async def test_crawler_writes_crawl_metrics():
    """测试写入 crawl_metrics 表"""
    # 模拟抓取 50 个社区
    # 验证 crawl_metrics 表有记录
    # 验证字段：cache_hit_rate, valid_posts_24h, total_communities
    pass
```

**实现步骤**:
1. 修改 `IncrementalCrawler._crawl_community()` 方法
2. 添加 `_record_success()`, `_record_empty()`, `_record_failure()` 方法
3. 添加 `_write_crawl_metrics()` 方法（每小时聚合）
4. 运行测试验证

**验收标准**:
- ✅ 4/4 测试通过
- ✅ 每次抓取都有统计记录
- ✅ crawl_metrics 每小时有记录

---

### 步骤 2: T1.6 - 创建黑名单配置（1h）

**目标**: 建立社区黑名单和降权配置

**测试先行**:
```python
# backend/tests/services/test_blacklist_loader.py

def test_blacklist_config_loads():
    """测试黑名单配置加载"""
    config = get_blacklist_config()
    assert len(config.blacklisted_communities) > 0
    assert len(config.downrank_keywords) > 0

def test_is_community_blacklisted():
    """测试社区黑名单检查"""
    config = get_blacklist_config()
    assert config.is_community_blacklisted("r/spam_farm") == True
    assert config.is_community_blacklisted("r/AskReddit") == False

def test_has_downrank_keyword():
    """测试降权关键词检查"""
    config = get_blacklist_config()
    assert config.has_downrank_keyword("Free giveaway!") == True
    assert config.has_downrank_keyword("Looking for advice") == False
```

**实现步骤**:
1. 创建 `config/community_blacklist.yaml`
2. 添加黑名单社区列表
3. 添加降权关键词列表
4. 修改 `blacklist_loader.py` 加载逻辑
5. 运行测试验证

**配置文件示例**:
```yaml
# config/community_blacklist.yaml
blacklisted_communities:
  - r/spam_farm
  - r/FreeKarma4U
  - r/giveaways

downrank_keywords:
  - giveaway
  - for fun
  - just sharing
  - free stuff
  - karma farming

blacklist_reasons:
  spam_farm: "垃圾内容农场"
  low_quality: "低质量社区"
  off_topic: "偏离主题"
```

**验收标准**:
- ✅ 3/3 测试通过
- ✅ 黑名单配置文件创建
- ✅ 黑名单社区被排除

---

### 步骤 3: T1.7 - 集成分级调度到 Celery Beat（1h）

**目标**: 将 TieredScheduler 集成到 Celery Beat，实现自动分级调度

**测试先行**:
```python
# backend/tests/tasks/test_tiered_crawl_tasks.py

@pytest.mark.asyncio
async def test_crawl_tier1_task():
    """测试 Tier 1 抓取任务"""
    # 调用 crawl_tier1 任务
    # 验证只抓取 Tier 1 社区
    # 验证使用正确的参数（sort=new, time_filter=week, limit=50）
    pass

@pytest.mark.asyncio
async def test_crawl_tier2_task():
    """测试 Tier 2 抓取任务"""
    pass

@pytest.mark.asyncio
async def test_crawl_tier3_task():
    """测试 Tier 3 抓取任务"""
    pass

def test_celery_beat_schedule_has_tier_tasks():
    """测试 Celery Beat 配置包含分级任务"""
    from app.core.celery_app import celery_app
    schedule = celery_app.conf.beat_schedule
    assert "crawl-tier1" in schedule
    assert "crawl-tier2" in schedule
    assert "crawl-tier3" in schedule
```

**实现步骤**:
1. 创建 `crawl_tier1`, `crawl_tier2`, `crawl_tier3` Celery 任务
2. 更新 `celery_app.py` 的 Beat 配置
3. 添加调度时间（Tier 1: 每 2h, Tier 2: 每 6h, Tier 3: 每 24h）
4. 运行测试验证

**Celery Beat 配置**:
```python
# backend/app/core/celery_app.py

celery_app.conf.beat_schedule.update({
    "crawl-tier1": {
        "task": "app.tasks.crawler_task.crawl_tier1",
        "schedule": crontab(minute="0", hour="*/2"),  # 每 2 小时
    },
    "crawl-tier2": {
        "task": "app.tasks.crawler_task.crawl_tier2",
        "schedule": crontab(minute="20", hour="*/6"),  # 每 6 小时
    },
    "crawl-tier3": {
        "task": "app.tasks.crawler_task.crawl_tier3",
        "schedule": crontab(minute="40", hour="2"),  # 每天 02:40
    },
})
```

**验收标准**:
- ✅ 4/4 测试通过
- ✅ Celery Beat 配置正确
- ✅ 分级任务自动执行

---

### 步骤 4: T1.8 - 集成精准补抓到 Celery Beat（1h）

**目标**: 将 RecrawlScheduler 集成到 Celery Beat，实现自动补抓

**测试先行**:
```python
# backend/tests/tasks/test_recrawl_tasks.py

@pytest.mark.asyncio
async def test_crawl_low_quality_communities_task():
    """测试低质量社区补抓任务"""
    # 创建低质量社区数据（last_crawled_at > 8h, avg_valid_posts < 50）
    # 调用 crawl_low_quality_communities 任务
    # 验证低质量社区被抓取
    # 验证 empty_hit 正确更新
    pass

def test_celery_beat_schedule_has_recrawl_task():
    """测试 Celery Beat 配置包含补抓任务"""
    from app.core.celery_app import celery_app
    schedule = celery_app.conf.beat_schedule
    assert "crawl-low-quality" in schedule
```

**实现步骤**:
1. 创建 `crawl_low_quality_communities` Celery 任务
2. 更新 `celery_app.py` 的 Beat 配置
3. 添加调度时间（每 4 小时）
4. 运行测试验证

**Celery Beat 配置**:
```python
# backend/app/core/celery_app.py

celery_app.conf.beat_schedule.update({
    "crawl-low-quality": {
        "task": "app.tasks.crawler_task.crawl_low_quality_communities",
        "schedule": crontab(minute="0", hour="*/4"),  # 每 4 小时
    },
})
```

**验收标准**:
- ✅ 2/2 测试通过
- ✅ Celery Beat 配置正确
- ✅ 补抓任务自动执行

---

### 步骤 5: Phase 1 验收测试（1h）

**目标**: 运行完整的 Phase 1 验收测试

**测试脚本**: `scripts/phase1-acceptance-test.sh`

**测试内容**:
1. 单元测试（所有 Phase 1 相关测试）
2. 集成测试（数据管道 + 分级调度 + 补抓）
3. E2E 测试（完整抓取流程）
4. 数据验证（社区数、帖子数、监控数据）

**验收标准**:
- ✅ 单元测试：100% 通过
- ✅ 集成测试：100% 通过
- ✅ E2E 测试：成功率 ≥ 90%
- ✅ 社区数量：≥ 200
- ✅ 帖子数量：≥ 12,000
- ✅ 监控数据：crawl_metrics 有记录
- ✅ 分级调度：Tier 1/2/3 正常运行
- ✅ 补抓任务：低质量社区被补抓

---

## 📋 执行时间表

| 时间段 | 任务 | 预计完成时间 |
|--------|------|-------------|
| 17:30-19:30 | T1.4: 改造 IncrementalCrawler 埋点 | 2h |
| 19:30-20:30 | T1.6: 创建黑名单配置 | 1h |
| 20:30-21:30 | T1.7: 集成分级调度到 Celery Beat | 1h |
| 21:30-22:30 | T1.8: 集成精准补抓到 Celery Beat | 1h |
| 22:30-23:30 | Phase 1 验收测试 | 1h |

**预计完成时间**: 2025-10-17 23:30:00

---

## 🎯 Phase 1 完成标准

### 数据层面
- [x] ✅ 社区数量：200 个（目标 300，部分完成）
- [x] ✅ 帖子数量：12,068 条（超过目标 8,000）
- [x] ✅ 冷热双写：正常运行
- [x] ✅ 水位线机制：正常工作
- [ ] 监控埋点：待完成
- [ ] 分级调度：待集成
- [ ] 补抓任务：待集成

### 系统层面
- [x] ✅ 增量抓取：正常运行
- [x] ✅ 数据库并发：已修复
- [x] ✅ 单元测试：177 passed, 1 skipped
- [ ] 集成测试：待补充
- [ ] E2E 测试：待补充
- [ ] Celery Beat：待更新

### 代码质量
- [x] ✅ 类型安全：100% mypy --strict
- [x] ✅ 代码格式：Black + isort
- [x] ✅ 测试覆盖率：≥ 80%

---

## 📝 下一步行动

**立即开始**: T1.4 - 改造 IncrementalCrawler 埋点

**命令**:
```bash
# 1. 创建测试文件
touch backend/tests/services/test_incremental_crawler_metrics.py

# 2. 编写测试（测试驱动）
# 3. 运行测试（应该失败）
cd backend && pytest tests/services/test_incremental_crawler_metrics.py -v

# 4. 实现功能
# 5. 运行测试（应该通过）
cd backend && pytest tests/services/test_incremental_crawler_metrics.py -v
```

---

**报告生成时间**: 2025-10-17 17:30:00  
**状态**: ✅ 计划已制定，等待执行

