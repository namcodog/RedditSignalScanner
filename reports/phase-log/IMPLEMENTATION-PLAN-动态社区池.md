# 动态社区池与预热期 - 完整实施计划

## 📋 执行摘要

**项目名称**: 动态社区池与智能爬虫系统  
**实施周期**: Day 13-20（8 天）  
**核心目标**: 建立自我进化的社区池系统，在正式上线前积累足够缓存数据  
**关键成果**: 社区池从 50 个扩展到 250+，缓存命中率 > 90%

---

## 🎯 Phase 0: 准备阶段（Day 13 上午，4小时）

### 任务 0.1: 数据库迁移

**负责人**: Backend Agent A  
**时间**: 2 小时  
**优先级**: P0

**任务清单**:
- [ ] 创建 Alembic 迁移文件
  ```bash
  cd backend
  alembic revision -m "add_community_pool_and_pending_communities"
  ```
- [ ] 编写迁移 SQL（创建 `community_pool` 和 `pending_communities` 表）
- [ ] 执行迁移
  ```bash
  alembic upgrade head
  ```
- [ ] 验证表结构
  ```bash
  psql -d reddit_scanner -c "\d community_pool"
  psql -d reddit_scanner -c "\d pending_communities"
  ```

**验收标准**:
- ✅ `community_pool` 表创建成功，包含所有字段和索引
- ✅ `pending_communities` 表创建成功
- ✅ 外键约束正确设置

### 任务 0.2: 种子社区数据准备

**负责人**: Lead + 产品/运营团队  
**时间**: 2 小时  
**优先级**: P0

**任务清单**:
- [ ] 准备 50-100 个种子社区列表（JSON 格式）
- [ ] 验证社区名称有效性（调用 Reddit API）
- [ ] 填充社区元数据（categories, keywords, daily_posts）
- [ ] 保存到 `backend/config/seed_communities.json`

**种子社区分类建议**:
```
创业/商业（20个）：
- r/startups, r/Entrepreneur, r/smallbusiness, r/business...

产品/SaaS（15个）：
- r/SaaS, r/ProductManagement, r/product, r/indiehackers...

技术/开发（15个）：
- r/programming, r/webdev, r/javascript, r/python...

营销/增长（10个）：
- r/marketing, r/SEO, r/socialmedia, r/GrowthHacking...

设计/UX（10个）：
- r/userexperience, r/UI_Design, r/web_design...

其他通用（10-30个）：
- r/technology, r/science, r/AskReddit...
```

**验收标准**:
- ✅ JSON 文件格式正确
- ✅ 至少 50 个社区
- ✅ 每个社区包含必需字段（name, tier, categories, description_keywords）

---

## 🚀 Phase 1: 基础缓存预热（Day 13-14，2天）

### 任务 1.1: 社区池加载器实现

**负责人**: Backend Agent A  
**时间**: 3 小时  
**优先级**: P0

**任务清单**:
- [ ] 创建 `backend/app/services/community_pool_loader.py`
- [ ] 实现 `load_seed_communities()` 函数（从 JSON 加载）
- [ ] 实现 `import_to_database()` 函数（导入到 `community_pool` 表）
- [ ] 实现 `load_community_pool()` 函数（从数据库加载，带缓存）
- [ ] 编写单元测试

**核心代码**:
```python
class CommunityPoolLoader:
    def __init__(self):
        self._cache: List[CommunityProfile] = []
        self._last_refresh: datetime | None = None
        self._refresh_interval = timedelta(hours=1)
    
    async def load_seed_communities(self) -> List[CommunityProfile]:
        """从 JSON 文件加载种子社区"""
        with open("backend/config/seed_communities.json") as f:
            data = json.load(f)
        return [CommunityProfile(**c) for c in data["seed_communities"]]
    
    async def import_to_database(self):
        """导入种子社区到数据库"""
        seed_communities = await self.load_seed_communities()
        async with get_session() as session:
            for community in seed_communities:
                existing = await session.execute(
                    select(CommunityPool).where(CommunityPool.name == community.name)
                )
                if not existing.scalar_one_or_none():
                    new_community = CommunityPool(
                        name=community.name,
                        tier="seed",
                        categories=community.categories,
                        description_keywords=community.description_keywords,
                        daily_posts=community.daily_posts,
                        avg_comment_length=community.avg_comment_length,
                        quality_score=community.quality_score,
                    )
                    session.add(new_community)
            await session.commit()
```

**验收标准**:
- ✅ 可以从 JSON 文件加载种子社区
- ✅ 可以导入到数据库
- ✅ 单元测试通过

### 任务 1.2: 爬虫任务实现

**负责人**: Backend Agent B  
**时间**: 4 小时  
**优先级**: P0

**任务清单**:
- [ ] 创建 `backend/app/tasks/crawler_task.py`
- [ ] 实现 `crawl_community()` 任务（爬取单个社区）
- [ ] 实现 `crawl_seed_communities()` 任务（批量爬取种子社区）
- [ ] 配置 Celery Beat 定时任务
- [ ] 编写集成测试

**验收标准**:
- ✅ 可以爬取单个社区并存入 Redis 缓存
- ✅ 可以批量爬取种子社区
- ✅ Celery Beat 定时任务正常运行
- ✅ 集成测试通过

### 任务 1.3: 启动预热爬虫

**负责人**: Backend Agent B  
**时间**: 1 小时  
**优先级**: P0

**任务清单**:
- [ ] 启动 Celery Beat
  ```bash
  celery -A app.core.celery_app beat --loglevel=info
  ```
- [ ] 启动 Celery Worker
  ```bash
  celery -A app.core.celery_app worker --loglevel=info --concurrency=2
  ```
- [ ] 手动触发首次爬取
  ```bash
  python backend/scripts/trigger_initial_crawl.py
  ```
- [ ] 监控爬取进度和 API 调用

**验收标准**:
- ✅ 50-100 个种子社区已爬取
- ✅ Redis 缓存命中率：100%（种子社区）
- ✅ 总 API 调用：50-100 次（1-2 分钟）
- ✅ 系统稳定运行

### 任务 1.4: 监控系统搭建

**负责人**: Backend Agent B  
**时间**: 2 小时  
**优先级**: P1

**任务清单**:
- [ ] 创建 `backend/app/tasks/monitoring_task.py`
- [ ] 实现 API 调用监控
- [ ] 实现缓存命中率监控
- [ ] 实现爬虫健康检查
- [ ] 配置告警（API 调用 > 55 次/分钟）

**验收标准**:
- ✅ 可以实时监控 API 调用次数
- ✅ 可以实时监控缓存命中率
- ✅ 告警机制正常工作

---

## 🧪 Phase 2: 内部测试 + 社区池扩展（Day 15-16，2天）

### 任务 2.1: 自动发现机制实现

**负责人**: Backend Agent A  
**时间**: 4 小时  
**优先级**: P0

**任务清单**:
- [ ] 扩展 `RedditAPIClient`，添加 `search_posts()` 方法
- [ ] 创建 `backend/app/services/community_discovery_service.py`
- [ ] 实现 `discover_related_communities()` 函数
- [ ] 实现 `record_discovered_communities()` 函数
- [ ] 编写单元测试

**验收标准**:
- ✅ 可以通过关键词搜索 Reddit 帖子
- ✅ 可以统计帖子来源的社区
- ✅ 可以记录到 `pending_communities` 表
- ✅ 单元测试通过

### 任务 2.2: 社区发现算法更新

**负责人**: Backend Agent A  
**时间**: 3 小时  
**优先级**: P0

**任务清单**:
- [ ] 更新 `backend/app/services/analysis/community_discovery.py`
- [ ] 添加降级策略（相关性 < 0.3 时触发自动发现）
- [ ] 添加通用社区兜底机制
- [ ] 添加用户警告信息返回
- [ ] 编写集成测试

**验收标准**:
- ✅ 覆盖率不足时触发自动发现
- ✅ 可以使用通用社区兜底
- ✅ 返回用户警告信息
- ✅ 集成测试通过

### 任务 2.3: 内部测试账号创建

**负责人**: Backend Agent B  
**时间**: 1 小时  
**优先级**: P1

**任务清单**:
- [ ] 创建 `backend/scripts/create_test_users.py`
- [ ] 创建 5-10 个内部测试账号
- [ ] 发送测试邀请邮件
- [ ] 准备测试指南文档

**验收标准**:
- ✅ 5-10 个测试账号创建成功
- ✅ 测试用户可以正常登录
- ✅ 测试指南文档完成

### 任务 2.4: 内部测试执行

**负责人**: Lead + QA Agent  
**时间**: 1 天  
**优先级**: P0

**任务清单**:
- [ ] 邀请内部用户测试（5-10 人）
- [ ] 收集测试反馈（产品描述、期望社区、满意度）
- [ ] 监控自动发现的新社区
- [ ] 记录降级事件

**测试场景**:
1. 常见需求（AI 笔记应用、SaaS 工具）
2. 垂直需求（区块链游戏、生物科技）
3. 长尾需求（量子计算、纳米技术）

**验收标准**:
- ✅ 20-30 次分析完成
- ✅ 发现 50-100 个新社区
- ✅ 收集到有效反馈

### 任务 2.5: Admin 审核新社区

**负责人**: Lead  
**时间**: 2 小时  
**优先级**: P0

**任务清单**:
- [ ] 查看 `pending_communities` 表
- [ ] 审核发现次数 >= 3 的社区
- [ ] 批准相关社区（30-50 个）
- [ ] 拒绝不相关社区
- [ ] 触发新社区首次爬取

**验收标准**:
- ✅ 30-50 个新社区批准并加入社区池
- ✅ 新社区已爬取并缓存
- ✅ 社区池规模：100-150 个

---

## 👥 Phase 3: Beta 用户测试 + 数据积累（Day 17-18，2天）

### 任务 3.1: Beta 测试注册页面

**负责人**: Frontend Agent  
**时间**: 3 小时  
**优先级**: P1

**任务清单**:
- [ ] 创建 Beta 测试注册页面
- [ ] 添加注册表单（邮箱、姓名、公司）
- [ ] 限制注册名额（50 人）
- [ ] 发送欢迎邮件

**验收标准**:
- ✅ Beta 注册页面上线
- ✅ 注册流程正常工作
- ✅ 欢迎邮件自动发送

### 任务 3.2: Beta 用户测试执行

**负责人**: Lead + QA Agent  
**时间**: 2 天  
**优先级**: P0

**任务清单**:
- [ ] 邀请 Beta 用户（20-50 人）
- [ ] 监控系统负载和 API 调用
- [ ] 收集用户反馈
- [ ] 动态调整爬虫策略

**监控指标**:
- API 调用次数/分钟
- 缓存命中率
- 平均分析耗时
- 用户满意度

**验收标准**:
- ✅ 20-50 个 Beta 用户注册
- ✅ 100-200 次分析完成
- ✅ 社区池规模：150-250 个
- ✅ 缓存命中率：85-95%

### 任务 3.3: 自适应爬虫实现

**负责人**: Backend Agent B  
**时间**: 4 小时  
**优先级**: P1

**任务清单**:
- [ ] 创建 `backend/app/services/adaptive_crawler.py`
- [ ] 实现优先级计算算法
- [ ] 实现动态爬取间隔调整
- [ ] 配置自动优化任务

**验收标准**:
- ✅ 可以根据使用频率计算优先级
- ✅ 可以动态调整爬取间隔
- ✅ 高频社区爬取更频繁

---

## ✅ Phase 4: 最终验证 + 准备上线（Day 19，1天）

### 任务 4.1: 系统健康检查

**负责人**: QA Agent  
**时间**: 2 小时  
**优先级**: P0

**任务清单**:
- [ ] 运行完整健康检查脚本
  ```bash
  python backend/scripts/health_check.py --full
  ```
- [ ] 检查 Redis 缓存状态
- [ ] 检查 PostgreSQL 数据库连接
- [ ] 检查 Celery Worker 运行状态
- [ ] 检查 Reddit API 连接

**验收标准**:
- ✅ 所有健康检查通过
- ✅ 系统正常运行时间 > 99%

### 任务 4.2: 预热期报告生成

**负责人**: Lead  
**时间**: 2 小时  
**优先级**: P0

**任务清单**:
- [ ] 运行报告生成脚本
  ```bash
  python backend/scripts/generate_warmup_report.py
  ```
- [ ] 分析社区池规模和覆盖率
- [ ] 分析缓存命中率和 API 使用
- [ ] 分析用户测试反馈
- [ ] 生成最终报告（JSON + PDF）

**验收标准**:
- ✅ 预热期报告生成成功
- ✅ 所有关键指标达标

### 任务 4.3: 最终优化

**负责人**: Backend Agent A + B  
**时间**: 4 小时  
**优先级**: P1

**任务清单**:
- [ ] 删除过期缓存（> 24 小时）
- [ ] 优化社区池（删除低质量社区）
- [ ] 调整爬虫频率（根据使用频率）
- [ ] 更新 Admin 后台数据
- [ ] 准备上线公告

**验收标准**:
- ✅ 缓存数据新鲜（< 12 小时）
- ✅ 社区池质量分数 > 0.7
- ✅ 爬虫频率优化完成

---

## 🎉 Phase 5: 正式上线（Day 20）

### 任务 5.1: 上线前检查

**负责人**: Lead  
**时间**: 1 小时  
**优先级**: P0

**任务清单**:
- [ ] 确认所有验收标准达标
- [ ] 确认监控和告警正常
- [ ] 确认备份策略就绪
- [ ] 确认回滚方案就绪

### 任务 5.2: 正式上线

**负责人**: Lead  
**时间**: 2 小时  
**优先级**: P0

**任务清单**:
- [ ] 发布上线公告
- [ ] 开放用户注册
- [ ] 监控系统负载
- [ ] 准备应急响应

**验收标准**:
- ✅ 系统正常运行
- ✅ 用户可以正常注册和使用
- ✅ 无重大故障

---

## 📊 关键指标追踪

### 预热期结束时（Day 19）

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| 社区池规模 | 250+ | - | - |
| 缓存命中率 | > 90% | - | - |
| 平均分析耗时 | < 3 分钟 | - | - |
| 用户满意度 | > 4.0/5 | - | - |
| API 调用峰值 | < 60 次/分钟 | - | - |

### 正式上线后（1 个月）

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| 社区池规模 | 400+ | - | - |
| 缓存命中率 | > 95% | - | - |
| 平均分析耗时 | < 2.5 分钟 | - | - |
| 用户满意度 | > 4.5/5 | - | - |
| 降级事件率 | < 5% | - | - |

---

**文档版本**: 1.0  
**创建时间**: 2025-10-14  
**负责人**: Lead Agent  
**状态**: ✅ 已确认

