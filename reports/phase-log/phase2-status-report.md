# Phase 2 开发状态报告

**生成时间**: 2025-10-17 17:10:00  
**Phase 2 目标**: 智能参数组合优化（双轮抓取/自适应 limit/时间窗口自适应）  
**验收标准**: 成功率≥60%，平均每社区新增帖子数较基线提升≥50%，生成效果评估报告

---

## 📊 当前状态总结

| 组件 | 状态 | 说明 |
|------|------|------|
| **AdaptiveCrawler** | ✅ 已实现 | 自适应抓取频率调整 |
| **TieredScheduler** | ✅ 已实现 | 分级调度策略 |
| **RecrawlScheduler** | ✅ 已实现 | 精准补抓低质量社区 |
| **单元测试** | ✅ 已编写 | 3 个测试文件 |
| **集成测试** | ❌ 未编写 | 需要补充 |
| **E2E 测试** | ❌ 未编写 | 需要补充 |

---

## ✅ 已完成的功能

### 1. AdaptiveCrawler（自适应抓取频率）

**文件**: `backend/app/services/adaptive_crawler.py`

**功能**:
- 根据缓存命中率动态调整抓取频率
- 策略：
  - 命中率 > 90% → 每 4 小时抓取
  - 命中率 70-90% → 每 2 小时抓取
  - 命中率 < 70% → 每 1 小时抓取
- 自动更新 Celery Beat 调度配置

**测试**: `backend/tests/services/test_adaptive_crawler.py`
- ✅ `test_adjust_sets_interval_to_4h_when_hit_rate_gt_90pct`
- ✅ `test_adjust_sets_interval_to_1h_when_hit_rate_lt_70pct`
- ✅ `test_adjust_sets_interval_to_2h_when_hit_rate_between_70_and_90pct`

**代码示例**:
```python
from app.services.adaptive_crawler import AdaptiveCrawler

crawler = AdaptiveCrawler()
hours = await crawler.adjust_crawl_frequency()
# 根据当前缓存命中率返回 1, 2, 或 4 小时
```

---

### 2. TieredScheduler（分级调度策略）

**文件**: `backend/app/services/tiered_scheduler.py`

**功能**:
- 根据 `avg_valid_posts` 将社区分配到 3 个层级
- Tier 1（高活跃）:
  - 阈值: avg_valid_posts > 20
  - 频率: 每 2 小时
  - 策略: sort=new, time_filter=week, limit=50
- Tier 2（中活跃）:
  - 阈值: 10 < avg_valid_posts ≤ 20
  - 频率: 每 6 小时
  - 策略: sort=top, time_filter=week, limit=80
- Tier 3（低活跃）:
  - 阈值: avg_valid_posts ≤ 10
  - 频率: 每 24 小时
  - 策略: sort=top, time_filter=month, limit=100

**测试**: `backend/tests/services/test_tiered_scheduler.py`
- ✅ `test_tiered_scheduler_assignments_and_application`

**代码示例**:
```python
from app.services.tiered_scheduler import TieredScheduler

async with SessionFactory() as db:
    scheduler = TieredScheduler(db)
    assignments = await scheduler.calculate_assignments()
    # {'tier1': [...], 'tier2': [...], 'tier3': [...]}
    
    await scheduler.apply_assignments(assignments)
    # 更新 community_cache 表的 crawl_frequency_hours 和 quality_tier
    
    tier1_communities = await scheduler.get_communities_for_tier("tier1")
    # 获取 Tier 1 的所有社区名称
```

---

### 3. RecrawlScheduler（精准补抓）

**文件**: `backend/app/services/recrawl_scheduler.py`

**功能**:
- 查找低质量且长时间未抓取的社区
- 条件:
  - `last_crawled_at` > 8 小时
  - `avg_valid_posts` < 50
  - 不在黑名单中
- 用于精准补抓任务

**测试**: `backend/tests/services/test_recrawl_scheduler.py`
- ✅ `test_find_low_quality_candidates_filters_by_thresholds`

**代码示例**:
```python
from app.services.recrawl_scheduler import find_low_quality_candidates

async with SessionFactory() as db:
    candidates = await find_low_quality_candidates(
        db,
        hours_threshold=8,
        avg_posts_threshold=50,
    )
    # 返回需要补抓的社区名称列表
```

---

## ❌ 待完成的任务

### 1. 集成测试

**需要创建**: `backend/tests/integration/test_phase2_integration.py`

**测试内容**:
1. **自适应频率调整集成测试**:
   - 模拟不同的缓存命中率
   - 验证 Celery Beat 配置是否正确更新
   - 验证抓取任务是否按新频率执行

2. **分级调度集成测试**:
   - 创建不同质量的社区数据
   - 运行分级调度
   - 验证 `community_cache` 表更新正确
   - 验证不同 tier 的抓取策略生效

3. **精准补抓集成测试**:
   - 创建低质量社区数据
   - 运行补抓任务
   - 验证数据更新

### 2. E2E 测试

**需要创建**: `scripts/e2e-test-phase2.sh`

**测试流程**:
1. 启动 Celery Worker 和 Beat
2. 导入测试社区数据（不同质量层级）
3. 运行分级调度
4. 等待一个抓取周期
5. 验证数据增长
6. 验证成功率 ≥ 60%
7. 验证平均新增帖子数提升 ≥ 50%
8. 生成效果评估报告

### 3. 双轮抓取功能

**需求**: 对同一社区进行两轮抓取（new + top）以提升覆盖率

**实现方案**:
- 修改 `IncrementalCrawler` 支持双轮抓取
- 第一轮: sort=new, time_filter=day
- 第二轮: sort=top, time_filter=week
- 合并去重结果

**文件**: `backend/app/services/incremental_crawler.py`

### 4. 时间窗口自适应

**需求**: 根据社区发帖频率动态调整 `time_filter`

**实现方案**:
- 计算社区的平均发帖间隔
- 高频社区（< 1h/帖）: time_filter=day
- 中频社区（1-6h/帖）: time_filter=week
- 低频社区（> 6h/帖）: time_filter=month

**文件**: 需要扩展 `TieredScheduler` 或创建新的 `TimeWindowAdapter`

### 5. 效果评估报告

**需要创建**: `backend/app/services/phase2_evaluator.py`

**功能**:
- 计算成功率（成功抓取数 / 总抓取数）
- 计算平均新增帖子数
- 对比基线数据
- 生成 Markdown 报告

---

## 📋 Phase 2 完整任务清单

- [x] T2.1: 实现 AdaptiveCrawler（自适应抓取频率）
- [x] T2.2: 实现 TieredScheduler（分级调度策略）
- [x] T2.3: 实现 RecrawlScheduler（精准补抓）
- [x] T2.4: 编写单元测试
- [ ] T2.5: 实现双轮抓取功能
- [ ] T2.6: 实现时间窗口自适应
- [ ] T2.7: 编写集成测试
- [ ] T2.8: 编写 E2E 测试
- [ ] T2.9: 实现效果评估报告
- [ ] T2.10: Phase 2 验收

**当前进度**: 4/10 任务完成（40%）

---

## 🎯 下一步行动计划

### 优先级 1: 补充缺失功能（预计 4 小时）

1. **实现双轮抓取**（1.5h）:
   ```python
   # 修改 IncrementalCrawler
   async def crawl_with_dual_strategy(self, community: str):
       # 第一轮: new + day
       posts_new = await self._fetch_posts(community, sort="new", time_filter="day")
       # 第二轮: top + week
       posts_top = await self._fetch_posts(community, sort="top", time_filter="week")
       # 合并去重
       all_posts = self._merge_and_deduplicate(posts_new, posts_top)
       return all_posts
   ```

2. **实现时间窗口自适应**（1.5h）:
   ```python
   # 创建 TimeWindowAdapter
   class TimeWindowAdapter:
       async def calculate_optimal_time_filter(self, community: str) -> str:
           avg_interval = await self._calculate_post_interval(community)
           if avg_interval < 3600:  # < 1 hour
               return "day"
           elif avg_interval < 21600:  # < 6 hours
               return "week"
           else:
               return "month"
   ```

3. **实现效果评估报告**（1h）:
   ```python
   # 创建 Phase2Evaluator
   class Phase2Evaluator:
       async def generate_report(self) -> dict:
           success_rate = await self._calculate_success_rate()
           avg_new_posts = await self._calculate_avg_new_posts()
           baseline_improvement = await self._compare_with_baseline()
           return {
               "success_rate": success_rate,
               "avg_new_posts": avg_new_posts,
               "improvement": baseline_improvement,
           }
   ```

### 优先级 2: 编写测试（预计 3 小时）

1. **集成测试**（1.5h）
2. **E2E 测试脚本**（1h）
3. **运行测试并修复问题**（0.5h）

### 优先级 3: 验收和文档（预计 1 小时）

1. **运行完整测试套件**
2. **生成 Phase 2 完成报告**
3. **更新实施检查清单**

---

## 📝 验收标准检查

| 标准 | 目标 | 当前状态 | 说明 |
|------|------|---------|------|
| **成功率** | ≥ 60% | ❓ 待测试 | 需要运行 E2E 测试 |
| **新增帖子数提升** | ≥ 50% | ❓ 待测试 | 需要对比基线数据 |
| **双轮抓取** | 实现 | ❌ 未实现 | 需要开发 |
| **自适应 limit** | 实现 | ✅ 已实现 | TieredScheduler 已支持 |
| **时间窗口自适应** | 实现 | ❌ 未实现 | 需要开发 |
| **效果评估报告** | 生成 | ❌ 未实现 | 需要开发 |

---

## 💡 建议

1. **立即行动**: 先实现双轮抓取和时间窗口自适应，这是 Phase 2 的核心功能
2. **测试驱动**: 先写集成测试，再运行 E2E 测试验证效果
3. **数据对比**: 保存 Phase 1 的基线数据，用于对比 Phase 2 的提升效果
4. **迭代优化**: 如果首次测试未达标，根据数据分析调整参数

---

**报告生成时间**: 2025-10-17 17:10:00  
**下次更新**: 完成优先级 1 任务后

