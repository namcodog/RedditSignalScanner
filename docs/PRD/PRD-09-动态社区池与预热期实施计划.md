# PRD-09: 动态社区池与预热期实施计划

## 1. 概述

### 1.1 背景

基于与用户的深入讨论，我们确定了以下核心问题和解决方案：

**核心问题**：
1. 无法保证初始提供的 500 个社区能覆盖所有用户需求
2. 社区池需要根据用户反馈动态更新和优化
3. 当社区池无法满足用户需求时，系统需要有降级策略
4. 需要在正式上线前积累足够的缓存数据

**解决方案**：
- **四层动态社区池架构**：种子社区 + 自动发现 + 用户反馈 + Admin 手动添加
- **智能优先级爬虫系统**：根据使用频率动态调整爬取优先级
- **7天预热期策略**：在正式上线前积累缓存数据并优化社区池
- **自动发现机制**：通过搜索 Reddit 帖子发现新社区

### 1.2 核心目标

- ✅ 初始只需提供 50-100 个种子社区（而非 500 个）
- ✅ 社区池从 50 个自动扩展到 500+ 个（3-6 个月）
- ✅ 缓存命中率从 60% 提升到 95%（预热期结束时）
- ✅ 用户体验：80% 的用户 2.5 分钟完成分析
- ✅ API 风险可控：平均 2-8 次 API 调用/分析

### 1.3 非目标

- ❌ 不支持实时动态发现社区（仅在覆盖率不足时触发）
- ❌ 不支持自动删除社区（需要 Admin 手动审核）
- ❌ 不支持多语言社区（专注英文 Reddit）

## 2. 四层动态社区池架构

### 2.1 第一层：种子社区池（50-100个）

**定义**：产品/运营团队提供的核心通用社区

**特点**：
- 覆盖率：60-70% 的用户需求
- 爬取频率：每 30 分钟一次
- 缓存命中率：> 95%
- API 预算：35 次/分钟（58%）

**数据格式**：
```json
// backend/config/seed_communities.json
{
  "version": "1.0",
  "last_updated": "2025-10-14",
  "seed_communities": [
    {
      "name": "r/startups",
      "tier": "seed",
      "categories": ["startup", "business", "founder"],
      "description_keywords": ["startup", "founder", "product", "launch", "mvp"],
      "daily_posts": 200,
      "avg_comment_length": 150,
      "quality_score": 0.95,
      "priority": "high"
    }
    // ... 50-100 个种子社区
  ]
}
```

**初始化流程**：
1. 系统启动时从 JSON 文件加载种子社区
2. 导入到 `community_pool` 表（tier = 'seed'）
3. 立即触发首次爬取（建立缓存）
4. 加入 Celery Beat 定期爬取计划

### 2.2 第二层：自动发现池（动态增长）

**定义**：通过 Reddit API 搜索帖子自动发现的社区

**触发条件**：
- 种子社区池相关性 < 0.3
- 用户分析时覆盖率不足

**发现机制**：
```python
async def discover_related_communities(
    keywords: List[str],
    limit: int = 20
) -> List[str]:
    """
    通过搜索 Reddit 帖子来发现相关社区
    
    策略：
    1. 使用关键词搜索 Reddit 帖子（/search 端点）
    2. 统计帖子来源的社区
    3. 返回最相关的社区列表
    
    API 调用：1 次搜索 = 1 次 API 调用
    """
    # 1. 搜索相关帖子
    search_query = " ".join(keywords[:3])
    posts = await reddit_client.search_posts(
        query=search_query,
        limit=100,
        sort="relevance"
    )
    
    # 2. 统计社区来源
    community_counts = {}
    for post in posts:
        subreddit = post.subreddit
        community_counts[subreddit] = community_counts.get(subreddit, 0) + 1
    
    # 3. 按帖子数量排序
    sorted_communities = sorted(
        community_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    return [community for community, count in sorted_communities[:limit]]
```

**记录流程**：
1. 发现新社区后记录到 `pending_communities` 表
2. 记录发现次数和关键词
3. 当发现次数 >= 5 时，自动批准并加入社区池
4. Admin 可以手动审核待审核社区

### 2.3 第三层：用户反馈驱动池（持续优化）

**定义**：基于用户反馈和分析结果优化的社区

**触发条件**：
- 用户分析后提供反馈
- 同一社区被 5+ 用户发现

**自动批准机制**：
```python
async def check_auto_approval_trigger(community_name: str) -> bool:
    """
    检查是否触发自动批准
    
    条件：被 5+ 个不同用户发现
    """
    pending = await get_pending_community(community_name)
    
    if pending and pending.discovered_count >= 5:
        # 自动批准并加入社区池
        await auto_approve_community(pending)
        return True
    
    return False
```

### 2.4 第四层：Admin 手动添加池（完全可控）

**定义**：Admin 后台手动添加的社区

**使用场景**：
- 战略性社区（竞品分析、行业趋势）
- 特殊需求社区（客户定制）
- 紧急补充社区（用户投诉）

**Admin 界面**：
```
Admin 后台 → 社区管理 → 手动添加

┌─────────────────────────────────────────────────────────┐
│ 社区名：[输入框]                                         │
│ 层级：  [下拉选择：seed / discovered / user_feedback]   │
│ 类别：  [多选：startup, tech, product, marketing...]    │
│ 关键词：[输入框，逗号分隔]                               │
│                                                          │
│ [添加社区] [批量导入]                                    │
└─────────────────────────────────────────────────────────┘
```

## 3. 智能优先级爬虫系统

### 3.1 优先级计算算法

```python
class CommunityPriorityManager:
    """社区爬取优先级管理器"""
    
    async def calculate_priority(self, community_name: str) -> float:
        """
        计算社区爬取优先级
        
        公式：
        priority = usage_frequency * 0.4 + activity_level * 0.3 + cache_freshness * 0.3
        
        Returns:
            0.0-1.0 的优先级分数
        """
        # 1. 使用频率（最近 7 天被多少用户使用）
        usage_frequency = await self._get_usage_frequency(community_name)
        
        # 2. 社区活跃度（每天帖子数量）
        activity_level = await self._get_activity_level(community_name)
        
        # 3. 缓存新鲜度（距离上次爬取的时间）
        cache_freshness = await self._get_cache_freshness(community_name)
        
        # 4. 计算优先级
        priority = (
            usage_frequency * 0.4 +
            activity_level * 0.3 +
            cache_freshness * 0.3
        )
        
        return priority
    
    async def get_crawl_interval(self, community_name: str) -> int:
        """
        计算爬取间隔（分钟）
        
        优先级越高，爬取越频繁
        """
        priority = await self.calculate_priority(community_name)
        
        # 优先级 → 爬取间隔映射
        interval = max(
            30,  # 最短 30 分钟
            min(
                360,  # 最长 6 小时
                int(1440 / (priority * 10))
            )
        )
        
        return interval
```

### 3.2 爬虫任务实现

详见 PRD-03 §5.3

### 3.3 API 调用预算分配

```
每分钟 60 次 API 调用预算：

├─ 种子社区爬虫（50-100个）：35 次/分钟（58%）
│   └─ 每 30 分钟爬取 12 个社区 → 0.4 次/分钟
│
├─ 扩展社区爬虫（动态增长）：10 次/分钟（17%）
│   └─ 根据优先级动态调整
│
├─ 自动发现（搜索帖子）：5 次/分钟（8%）
│   └─ 当社区池覆盖率不足时触发
│
└─ 实时分析请求：10 次/分钟（17%）
    └─ 补充缺失数据

总计：60 次/分钟（100% 利用率）
```

## 4. 7天预热期实施计划

### 4.1 时间线总览

```
Day 0-12：功能开发（已完成）
    ↓
Day 13-19：预热期（7 天）
    ├─ Day 13-14：基础缓存预热（种子社区）
    ├─ Day 15-16：内部测试 + 社区池扩展
    ├─ Day 17-18：Beta 用户测试 + 数据积累
    └─ Day 19：最终验证 + 准备上线
    ↓
Day 20：正式上线
```

### 4.2 Day 13-14：基础缓存预热

详见 PRD-03 §6.2

### 4.3 Day 15-16：内部测试 + 社区池扩展

详见 PRD-03 §6.3

### 4.4 Day 17-18：Beta 用户测试 + 数据积累

详见 PRD-03 §6.4

### 4.5 Day 19：最终验证 + 准备上线

详见 PRD-03 §6.5

## 5. 数据库设计

### 5.1 community_pool 表（动态社区池）

```sql
CREATE TABLE community_pool (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    tier VARCHAR(20) NOT NULL,  -- seed, discovered, user_feedback, admin
    categories JSONB NOT NULL,
    description_keywords JSONB NOT NULL,
    daily_posts INTEGER DEFAULT 0,
    avg_comment_length INTEGER DEFAULT 0,
    quality_score DECIMAL(3,2) DEFAULT 0.50,
    user_feedback_count INTEGER DEFAULT 0,
    discovered_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_community_pool_tier ON community_pool(tier);
CREATE INDEX idx_community_pool_is_active ON community_pool(is_active);
CREATE INDEX idx_community_pool_quality_score ON community_pool(quality_score);
```

### 5.2 pending_communities 表（待审核社区）

```sql
CREATE TABLE pending_communities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    discovered_from_keywords JSONB,
    discovered_count INTEGER DEFAULT 1,
    first_discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, rejected
    admin_reviewed_at TIMESTAMP,
    admin_notes TEXT
);

CREATE INDEX idx_pending_communities_status ON pending_communities(status);
CREATE INDEX idx_pending_communities_discovered_count ON pending_communities(discovered_count);
```

## 6. Admin 后台功能扩展

### 6.1 待审核社区管理

详见 PRD-07 扩展

### 6.2 社区池覆盖率分析

详见 PRD-07 扩展

### 6.3 降级事件监控

详见 PRD-07 扩展

## 7. 验收标准

### 7.1 预热期结束时（Day 19）

- ✅ 社区池规模：250+ 个社区
- ✅ 缓存命中率：> 90%
- ✅ 平均分析耗时：< 3 分钟
- ✅ 用户满意度：> 4.0/5 星
- ✅ API 调用：< 60 次/分钟（峰值）

### 7.2 正式上线后（1 个月）

- ✅ 社区池规模：400+ 个社区
- ✅ 缓存命中率：> 95%
- ✅ 平均分析耗时：< 2.5 分钟
- ✅ 用户满意度：> 4.5/5 星
- ✅ 降级事件：< 5%

## 8. 风险管理

### 8.1 技术风险

详见 PRD-03 §7.1

### 8.2 合规性风险

**Reddit API 使用条款**：
- ✅ 遵守 Rate Limiting（60 次/分钟）
- ✅ 使用 OAuth2 认证
- ✅ 正确的 User-Agent
- ✅ 缓存数据用于提升用户体验（合规）
- ✅ 尊重用户删除请求
- ✅ 不转售 Reddit 数据

### 8.3 运营风险

**社区池质量下降**：
- 影响：分析结果不准确
- 缓解：定期审核社区质量，删除低质量社区
- 监控：社区质量分数，用户反馈

**预热期用户体验差**：
- 影响：Beta 用户流失
- 缓解：明确告知预热期状态，提供反馈奖励
- 监控：用户留存率，反馈满意度

---

**文档版本**: 1.0  
**最后更新**: 2025-10-14  
**负责人**: Lead Agent  
**状态**: ✅ 已确认

