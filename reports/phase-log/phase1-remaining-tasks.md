# Phase 1 未完成任务清单

**文档日期**: 2025-10-17  
**项目**: Reddit Signal Scanner - 数据与算法双轨优化  
**状态**: Phase 1 已完成，Phase 2 待启动

---

## 📋 说明

Phase 1 的 8 个核心任务（T1.1-T1.8）已全部完成。本文档列出的是**优化项**和**Phase 2 准备工作**，非阻塞性任务。

---

## 1. Phase 1 优化项（可选）

### 1.1 社区池扩容至目标容量

**任务编号**: T1.5-补充  
**优先级**: 中  
**预计工时**: 2 小时  
**当前状态**: 200/300 (67%)

**任务描述**:
补充 100 个高质量社区，达到目标容量 300 个。

**执行步骤**:
1. 从 Reddit 筛选 100 个高质量社区（subscribers > 50K，活跃度高）
2. 更新 `backend/data/community_expansion_300.json`
3. 运行导入脚本：
   ```bash
   PYTHONPATH=backend python3 scripts/import_community_expansion.py
   ```
4. 验证社区数量：
   ```sql
   SELECT COUNT(*) FROM community_pool WHERE is_active = true;
   ```

**验收标准**:
- 社区总数 ≥ 300
- 新增社区 quality_score ≥ 0.60
- 类目分布均衡（tech/business/finance/lifestyle）

---

### 1.2 创建黑名单配置文件

**任务编号**: T1.6-补充  
**优先级**: 低  
**预计工时**: 30 分钟  
**当前状态**: 数据库字段已创建，配置文件缺失

**任务描述**:
创建 `config/community_blacklist.yaml` 配置文件，启用黑名单功能。

**执行步骤**:
1. 创建配置文件：
   ```bash
   mkdir -p config
   touch config/community_blacklist.yaml
   ```

2. 填写配置内容：
   ```yaml
   # 完全黑名单（不抓取）
   blacklist:
     - name: "spam_community"
       reason: "垃圾内容"
       penalty: 100
     - name: "nsfw_community"
       reason: "不适合内容"
       penalty: 100

   # 降权社区（降低优先级）
   downgrade:
     - name: "low_quality_community"
       reason: "质量下降"
       penalty: 30
     - name: "inactive_community"
       reason: "活跃度低"
       penalty: 20

   # 白名单（强制抓取）
   whitelist:
     - name: "high_value_community"
       reason: "高价值社区"
       bonus: 50
   ```

3. 应用配置：
   ```bash
   PYTHONPATH=backend python3 scripts/apply_blacklist_config.py
   ```

**验收标准**:
- 配置文件存在且格式正确
- 黑名单社区 `is_blacklisted = true`
- 降权社区 `priority_penalty > 0`
- 日志不再显示 "黑名单配置文件不存在"

---

### 1.3 优化 crawl_metrics 写入逻辑

**任务编号**: T1.3-优化  
**优先级**: 低  
**预计工时**: 1 小时  
**当前状态**: 偶发写入失败（非阻塞）

**任务描述**:
优化 `_record_crawl_metrics()` 函数，减少数据库连接池竞争。

**问题现象**:
```
ERROR app.tasks.crawler_task:crawler_task.py:236 写入 crawl_metrics 失败
```

**优化方案**:
1. 使用独立的 DB session（避免与主抓取流程共享）
2. 增加重试机制（最多 3 次）
3. 异步写入（不阻塞主流程）

**代码修改**:
```python
# backend/app/tasks/crawler_task.py

async def _record_crawl_metrics(...):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with SessionFactory() as metrics_db:  # 独立 session
                # ... 写入逻辑
                await metrics_db.commit()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"写入 crawl_metrics 失败（已重试 {max_retries} 次）: {e}")
            else:
                await asyncio.sleep(0.5 * (attempt + 1))  # 指数退避
```

**验收标准**:
- 日志不再显示 "写入 crawl_metrics 失败"
- crawl_metrics 表数据完整

---

### 1.4 清理 pytest 配置警告

**任务编号**: 测试优化  
**优先级**: 低  
**预计工时**: 15 分钟  
**当前状态**: 警告不影响测试运行

**问题现象**:
```
PytestConfigWarning: Unknown config option: asyncio_default_fixture_loop_scope
```

**解决方案**:
1. 升级 pytest-asyncio：
   ```bash
   pip install --upgrade pytest-asyncio
   ```

2. 或移除配置项：
   ```ini
   # backend/pytest.ini
   # 删除或注释以下行
   # asyncio_default_fixture_loop_scope = function
   ```

**验收标准**:
- pytest 运行无警告

---

## 2. Phase 2 准备工作

### 2.1 数据积累

**任务编号**: Phase 2 前置  
**优先级**: 高  
**预计工时**: 7-14 天（自动运行）  
**当前状态**: 1-2 天数据

**任务描述**:
运行增量抓取 7-14 天，积累足够的历史数据，为算法优化提供基础。

**执行步骤**:
1. 配置 Celery Beat 定时任务：
   ```python
   # backend/app/celery_app.py
   
   beat_schedule = {
       'incremental-crawl-tier1': {
           'task': 'app.tasks.crawler_task.incremental_crawl_task',
           'schedule': crontab(minute=0),  # 每小时
           'args': ('tier1',)
       },
       'incremental-crawl-tier2': {
           'task': 'app.tasks.crawler_task.incremental_crawl_task',
           'schedule': crontab(minute=0, hour='*/4'),  # 每 4 小时
           'args': ('tier2',)
       },
       'incremental-crawl-tier3': {
           'task': 'app.tasks.crawler_task.incremental_crawl_task',
           'schedule': crontab(minute=0, hour='*/12'),  # 每 12 小时
           'args': ('tier3',)
       },
   }
   ```

2. 启动 Celery Beat：
   ```bash
   cd backend
   celery -A app.celery_app beat -l info
   ```

3. 监控数据积累：
   ```sql
   SELECT 
       DATE(created_at) as date,
       COUNT(*) as posts_count
   FROM posts_raw
   GROUP BY DATE(created_at)
   ORDER BY date DESC;
   ```

**验收标准**:
- 数据积累 ≥ 7 天
- 每日新增帖子 ≥ 1,000 条
- 抓取成功率 ≥ 90%

---

### 2.2 监控面板开发

**任务编号**: Phase 2-监控  
**优先级**: 中  
**预计工时**: 4 小时  
**当前状态**: 未开始

**任务描述**:
开发实时监控面板，展示关键指标。

**功能需求**:
1. **抓取成功率趋势图**（24 小时）
2. **社区活跃度分布图**（Tier 1/2/3）
3. **数据一致性监控**（PostHot vs PostRaw）
4. **水位线覆盖率**
5. **告警列表**（成功率 < 90%，数据不一致等）

**技术栈**:
- Frontend: React + Chart.js
- Backend: FastAPI + WebSocket (实时推送)

**API 端点**:
```python
# backend/app/api/v1/monitoring.py

@router.get("/metrics/crawl-success-rate")
async def get_crawl_success_rate(hours: int = 24):
    """获取抓取成功率趋势"""
    pass

@router.get("/metrics/community-activity")
async def get_community_activity():
    """获取社区活跃度分布"""
    pass

@router.get("/metrics/data-consistency")
async def get_data_consistency():
    """获取数据一致性状态"""
    pass
```

**验收标准**:
- 监控面板可访问
- 数据实时更新（WebSocket）
- 告警功能正常

---

### 2.3 智能参数组合优化（Phase 2 核心）

**任务编号**: Phase 2-算法优化  
**优先级**: 高  
**预计工时**: 16 小时  
**当前状态**: 未开始

**任务描述**:
实现智能参数组合优化，提升抓取效率和数据质量。

**子任务**:

#### 2.3.1 双轮抓取策略

**目标**: 提升实时性 + 覆盖质量

**实现方案**:
1. **第一轮**: sort=new, time_filter=day（实时性）
2. **第二轮**: sort=top, time_filter=week（质量）
3. 合并去重

**代码示例**:
```python
async def dual_round_crawl(community: str):
    # 第一轮：实时性
    round1 = await crawl_community(
        community, sort='new', time_filter='day', limit=50
    )
    
    # 第二轮：质量
    round2 = await crawl_community(
        community, sort='top', time_filter='week', limit=30
    )
    
    # 合并去重
    all_posts = merge_and_deduplicate(round1, round2)
    return all_posts
```

**验收标准**:
- 新增帖子数提升 ≥ 50%
- 高质量帖子比例提升 ≥ 30%

#### 2.3.2 自适应 limit

**目标**: 根据历史成功率动态调整 limit

**实现方案**:
```python
def calculate_adaptive_limit(community: str) -> int:
    cache = get_community_cache(community)
    
    if cache.avg_valid_posts > 80:
        return 100  # 高活跃度
    elif cache.avg_valid_posts > 30:
        return 50   # 中活跃度
    else:
        return 20   # 低活跃度
```

**验收标准**:
- 抓取效率提升 ≥ 30%（减少无效请求）
- 成功率保持 ≥ 90%

#### 2.3.3 时间窗口自适应

**目标**: 根据社区发帖频率调整 time_filter

**实现方案**:
```python
def calculate_adaptive_time_filter(community: str) -> str:
    cache = get_community_cache(community)
    
    if cache.avg_valid_posts > 100:
        return 'day'    # 高频社区
    elif cache.avg_valid_posts > 30:
        return 'week'   # 中频社区
    else:
        return 'month'  # 低频社区
```

**验收标准**:
- 数据覆盖率提升 ≥ 20%
- 抓取成功率保持 ≥ 90%

---

## 3. 长期优化项

### 3.1 算法优化

- **信号识别算法**: 基于 NLP 识别高价值帖子
- **趋势预测算法**: 预测社区活跃度变化
- **推荐算法**: 推荐高价值社区

### 3.2 性能优化

- **数据库查询优化**: 添加复合索引
- **缓存优化**: Redis 缓存热点数据
- **并发优化**: 提升抓取并发度

### 3.3 功能扩展

- **多语言支持**: 支持非英语社区
- **多平台支持**: 支持 Twitter, HackerNews 等
- **API 开放**: 提供 RESTful API

---

## 4. 任务优先级总结

### 高优先级（立即执行）

1. ✅ Phase 1 验收（已完成）
2. 🔄 数据积累（7-14 天）
3. 🔄 Phase 2 准备（智能参数组合优化）

### 中优先级（1-2 周内）

1. 社区池扩容至 300
2. 监控面板开发

### 低优先级（可选）

1. 创建黑名单配置文件
2. 优化 crawl_metrics 写入逻辑
3. 清理 pytest 配置警告

---

**文档维护**: AI Agent  
**最后更新**: 2025-10-17

