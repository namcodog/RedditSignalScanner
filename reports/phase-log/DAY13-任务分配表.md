# Day 13 任务分配表

**日期**: 2025-10-14（Day 13）  
**阶段**: Phase 0 准备阶段 + Phase 1 基础缓存预热（启动）  
**目标**: 完成数据库迁移、种子社区准备、爬虫系统实现并启动预热

---

## 🎯 Day 13 总体目标

- ✅ 数据库迁移完成（`community_pool` 和 `pending_communities` 表）
- ✅ 种子社区数据准备完成（50-100 个社区 JSON 文件）
- ✅ 社区池加载器实现完成
- ✅ 爬虫任务实现完成
- ✅ 预热爬虫启动并运行
- ✅ 监控系统搭建完成

---

## 👨‍💻 Backend Agent A - 任务清单

### 上午任务（9:00-12:00，3小时）

#### 任务 A1: 数据库迁移（优先级 P0）

**时间**: 9:00-11:00（2小时）

**任务清单**:
- [ ] 创建 Alembic 迁移文件
  ```bash
  cd backend
  alembic revision -m "add_community_pool_and_pending_communities"
  ```

- [ ] 编写 `community_pool` 表迁移 SQL
  ```python
  # backend/alembic/versions/xxx_add_community_pool.py
  
  def upgrade():
      op.create_table(
          'community_pool',
          sa.Column('id', sa.Integer(), nullable=False),
          sa.Column('name', sa.String(100), nullable=False),
          sa.Column('tier', sa.String(20), nullable=False),
          sa.Column('categories', sa.JSON(), nullable=False),
          sa.Column('description_keywords', sa.JSON(), nullable=False),
          sa.Column('daily_posts', sa.Integer(), default=0),
          sa.Column('avg_comment_length', sa.Integer(), default=0),
          sa.Column('quality_score', sa.Numeric(3, 2), default=0.50),
          sa.Column('user_feedback_count', sa.Integer(), default=0),
          sa.Column('discovered_count', sa.Integer(), default=0),
          sa.Column('is_active', sa.Boolean(), default=True),
          sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
          sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
          sa.PrimaryKeyConstraint('id'),
          sa.UniqueConstraint('name')
      )
      
      op.create_index('idx_community_pool_tier', 'community_pool', ['tier'])
      op.create_index('idx_community_pool_is_active', 'community_pool', ['is_active'])
      op.create_index('idx_community_pool_quality_score', 'community_pool', ['quality_score'])
  ```

- [ ] 编写 `pending_communities` 表迁移 SQL
  ```python
  def upgrade():
      op.create_table(
          'pending_communities',
          sa.Column('id', sa.Integer(), nullable=False),
          sa.Column('name', sa.String(100), nullable=False),
          sa.Column('discovered_from_keywords', sa.JSON()),
          sa.Column('discovered_count', sa.Integer(), default=1),
          sa.Column('first_discovered_at', sa.DateTime(), server_default=sa.func.now()),
          sa.Column('last_discovered_at', sa.DateTime(), server_default=sa.func.now()),
          sa.Column('status', sa.String(20), default='pending'),
          sa.Column('admin_reviewed_at', sa.DateTime()),
          sa.Column('admin_notes', sa.Text()),
          sa.PrimaryKeyConstraint('id'),
          sa.UniqueConstraint('name')
      )
      
      op.create_index('idx_pending_communities_status', 'pending_communities', ['status'])
      op.create_index('idx_pending_communities_discovered_count', 'pending_communities', ['discovered_count'])
  ```

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
- ✅ 迁移可以正常回滚（`alembic downgrade -1`）

**输出文件**:
- `backend/alembic/versions/xxx_add_community_pool_and_pending_communities.py`

---

### 下午任务（13:00-18:00，5小时）

#### 任务 A2: 社区池加载器实现（优先级 P0）

**时间**: 13:00-16:00（3小时）

**任务清单**:
- [ ] 创建数据模型
  ```bash
  # backend/app/models/community_pool.py
  ```

- [ ] 实现 `CommunityPool` 和 `PendingCommunity` SQLAlchemy 模型
  ```python
  class CommunityPool(Base):
      __tablename__ = "community_pool"
      
      id = Column(Integer, primary_key=True)
      name = Column(String(100), unique=True, nullable=False)
      tier = Column(String(20), nullable=False)
      categories = Column(JSON, nullable=False)
      description_keywords = Column(JSON, nullable=False)
      daily_posts = Column(Integer, default=0)
      avg_comment_length = Column(Integer, default=0)
      quality_score = Column(Numeric(3, 2), default=0.50)
      user_feedback_count = Column(Integer, default=0)
      discovered_count = Column(Integer, default=0)
      is_active = Column(Boolean, default=True)
      created_at = Column(DateTime, server_default=func.now())
      updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
  ```

- [ ] 创建社区池加载器服务
  ```bash
  # backend/app/services/community_pool_loader.py
  ```

- [ ] 实现 `load_seed_communities()` 函数（从 JSON 加载）
- [ ] 实现 `import_to_database()` 函数（导入到数据库）
- [ ] 实现 `load_community_pool()` 函数（从数据库加载，带缓存）
- [ ] 实现 `get_community_by_name()` 函数
- [ ] 实现 `get_communities_by_tier()` 函数

**核心代码**:
```python
class CommunityPoolLoader:
    def __init__(self):
        self._cache: List[CommunityProfile] = []
        self._last_refresh: datetime | None = None
        self._refresh_interval = timedelta(hours=1)
    
    async def load_seed_communities(self) -> List[Dict]:
        """从 JSON 文件加载种子社区"""
        json_path = Path("backend/config/seed_communities.json")
        with open(json_path) as f:
            data = json.load(f)
        return data["seed_communities"]
    
    async def import_to_database(self):
        """导入种子社区到数据库"""
        seed_communities = await self.load_seed_communities()
        async with get_session() as session:
            for community_data in seed_communities:
                existing = await session.execute(
                    select(CommunityPool).where(CommunityPool.name == community_data["name"])
                )
                if not existing.scalar_one_or_none():
                    new_community = CommunityPool(**community_data)
                    session.add(new_community)
            await session.commit()
    
    async def load_community_pool(self, force_refresh: bool = False) -> List[CommunityProfile]:
        """从数据库加载社区池（带缓存）"""
        if force_refresh or self._should_refresh():
            async with get_session() as session:
                result = await session.execute(
                    select(CommunityPool).where(CommunityPool.is_active == True)
                )
                communities = result.scalars().all()
                self._cache = [self._to_profile(c) for c in communities]
                self._last_refresh = datetime.now(timezone.utc)
        
        return self._cache
```

- [ ] 编写单元测试
  ```bash
  # backend/tests/services/test_community_pool_loader.py
  ```

- [ ] 运行测试
  ```bash
  pytest backend/tests/services/test_community_pool_loader.py -v
  ```

**验收标准**:
- ✅ 可以从 JSON 文件加载种子社区
- ✅ 可以导入到数据库（去重）
- ✅ 可以从数据库加载社区池（带缓存）
- ✅ 单元测试通过（覆盖率 > 80%）

**输出文件**:
- `backend/app/models/community_pool.py`
- `backend/app/services/community_pool_loader.py`
- `backend/tests/services/test_community_pool_loader.py`

---

#### 任务 A3: 协助种子社区数据准备（优先级 P0）

**时间**: 16:00-17:00（1小时）

**任务清单**:
- [ ] 与 Lead 协作验证种子社区名称有效性
- [ ] 编写验证脚本
  ```bash
  # backend/scripts/validate_seed_communities.py
  ```

- [ ] 验证 JSON 文件格式
- [ ] 验证社区名称（调用 Reddit API）
- [ ] 生成验证报告

**验收标准**:
- ✅ 所有社区名称有效
- ✅ JSON 格式正确
- ✅ 验证报告生成

**输出文件**:
- `backend/scripts/validate_seed_communities.py`
- `backend/config/seed_communities_validation_report.json`

---

#### 任务 A4: 代码审查与文档（优先级 P1）

**时间**: 17:00-18:00（1小时）

**任务清单**:
- [ ] 审查 Backend Agent B 的爬虫任务代码
- [ ] 更新 API 文档（如有新增接口）
- [ ] 更新 README（如有新增依赖）
- [ ] 提交代码并推送到远程仓库

**验收标准**:
- ✅ 代码审查完成
- ✅ 文档更新完成
- ✅ 代码提交成功

---

## 👨‍💻 Backend Agent B - 任务清单

### 上午任务（9:00-12:00，3小时）

#### 任务 B1: 环境准备与配置（优先级 P0）

**时间**: 9:00-10:00（1小时）

**任务清单**:
- [ ] 验证 Celery 环境
  ```bash
  pip install celery[redis]
  ```

- [ ] 验证 Redis 连接
  ```bash
  redis-cli ping
  ```

- [ ] 配置 Celery 应用
  ```python
  # backend/app/core/celery_app.py
  
  celery_app = Celery(
      "reddit_scanner",
      broker="redis://localhost:6379/0",
      backend="redis://localhost:6379/0"
  )
  
  celery_app.conf.update(
      task_serializer="json",
      accept_content=["json"],
      result_serializer="json",
      timezone="UTC",
      enable_utc=True,
  )
  ```

- [ ] 测试 Celery 连接
  ```bash
  celery -A app.core.celery_app inspect ping
  ```

**验收标准**:
- ✅ Celery 安装成功
- ✅ Redis 连接正常
- ✅ Celery 配置正确

---

#### 任务 B2: 爬虫任务实现（优先级 P0）

**时间**: 10:00-12:00（2小时）

**任务清单**:
- [ ] 创建爬虫任务文件
  ```bash
  # backend/app/tasks/crawler_task.py
  ```

- [ ] 实现 `crawl_community()` 任务（爬取单个社区）
  ```python
  @celery_app.task(name="tasks.crawler.crawl_community", bind=True, max_retries=3)
  async def crawl_community(self, community_name: str):
      """
      爬取单个社区
      
      API 调用：1 次
      """
      try:
          logger.info(f"开始爬取社区: {community_name}")
          
          # 1. 调用 Reddit API
          posts = await reddit_client.fetch_subreddit_posts(
              community_name,
              limit=100,
              time_filter="week",
              sort="top"
          )
          
          # 2. 更新 Redis 缓存
          cache_manager.set_cached_posts(
              community_name,
              posts,
              ttl_seconds=86400  # 24 小时
          )
          
          # 3. 更新 CommunityCache 表（元数据）
          await update_community_cache_metadata(
              community_name,
              posts_cached=len(posts),
              last_crawled_at=datetime.now(timezone.utc)
          )
          
          logger.info(f"✅ {community_name}: 缓存 {len(posts)} 个帖子")
          
          return {
              "community": community_name,
              "posts_count": len(posts),
              "status": "success"
          }
          
      except Exception as e:
          logger.error(f"❌ {community_name}: 爬取失败 - {e}")
          raise self.retry(exc=e, countdown=60)
  ```

- [ ] 实现 `crawl_seed_communities()` 任务（批量爬取）
  ```python
  @celery_app.task(name="tasks.crawler.crawl_seed_communities")
  async def crawl_seed_communities():
      """
      爬取种子社区池（50-100个）
      
      策略：
      - 分批爬取（每批 12 个社区）
      - 每批间隔 30 分钟
      - 总 API 调用：12 次/30分钟 = 0.4 次/分钟
      """
      loader = CommunityPoolLoader()
      seed_communities = await loader.load_community_pool()
      seed_communities = [c for c in seed_communities if c.tier == "seed"]
      
      logger.info(f"开始爬取 {len(seed_communities)} 个种子社区")
      
      # 分批爬取（每批 12 个社区）
      batch_size = 12
      for i in range(0, len(seed_communities), batch_size):
          batch = seed_communities[i:i+batch_size]
          
          # 并发爬取（最多 5 个并发）
          tasks = [
              crawl_community.apply_async(args=[community.name])
              for community in batch
          ]
          
          logger.info(f"批次 {i//batch_size + 1}: 爬取 {len(batch)} 个社区")
          
          # 等待批次完成
          await asyncio.gather(*[AsyncResult(task.id).get() for task in tasks])
          
          # 等待 30 分钟后爬取下一批
          if i + batch_size < len(seed_communities):
              logger.info("等待 30 分钟后爬取下一批...")
              await asyncio.sleep(1800)
      
      logger.info("✅ 种子社区爬取完成")
  ```

**验收标准**:
- ✅ 可以爬取单个社区并存入 Redis 缓存
- ✅ 可以批量爬取种子社区
- ✅ 错误处理和重试机制正常

**输出文件**:
- `backend/app/tasks/crawler_task.py`

---

### 下午任务（13:00-18:00，5小时）

#### 任务 B3: Celery Beat 定时任务配置（优先级 P0）

**时间**: 13:00-14:00（1小时）

**任务清单**:
- [ ] 配置 Celery Beat 定时任务
  ```python
  # backend/app/core/celery_app.py
  
  celery_app.conf.beat_schedule = {
      # 种子社区爬虫（每 30 分钟）
      'crawl-seed-communities': {
          'task': 'tasks.crawler.crawl_seed_communities',
          'schedule': crontab(minute='*/30'),
      },
  }
  ```

- [ ] 测试定时任务配置
  ```bash
  celery -A app.core.celery_app beat --loglevel=info --dry-run
  ```

**验收标准**:
- ✅ Celery Beat 配置正确
- ✅ 定时任务可以正常调度

---

#### 任务 B4: 启动预热爬虫（优先级 P0）

**时间**: 14:00-15:00（1小时）

**任务清单**:
- [ ] 创建启动脚本
  ```bash
  # backend/scripts/start_warmup_crawler.sh
  ```

- [ ] 启动 Celery Beat
  ```bash
  celery -A app.core.celery_app beat --loglevel=info &
  ```

- [ ] 启动 Celery Worker
  ```bash
  celery -A app.core.celery_app worker --loglevel=info --concurrency=2 &
  ```

- [ ] 手动触发首次爬取
  ```bash
  python backend/scripts/crawl/trigger_initial_crawl.py
  ```

- [ ] 监控爬取进度
  ```bash
  celery -A app.core.celery_app events
  ```

**验收标准**:
- ✅ Celery Beat 和 Worker 正常运行
- ✅ 首次爬取成功
- ✅ 50-100 个种子社区已爬取
- ✅ Redis 缓存命中率：100%（种子社区）

**输出文件**:
- `backend/scripts/start_warmup_crawler.sh`
- `backend/scripts/crawl/trigger_initial_crawl.py`

---

#### 任务 B5: 监控系统搭建（优先级 P1）

**时间**: 15:00-17:00（2小时）

**任务清单**:
- [ ] 创建监控任务文件
  ```bash
  # backend/app/tasks/monitoring_task.py
  ```

- [ ] 实现 API 调用监控
  ```python
  @celery_app.task(name="tasks.monitoring.monitor_api_calls")
  async def monitor_api_calls():
      """监控 Reddit API 调用次数"""
      # 从 Redis 获取最近 1 分钟的 API 调用次数
      calls_per_minute = await redis_client.get("api_calls_per_minute")
      
      if calls_per_minute and int(calls_per_minute) > 55:
          logger.warning(f"⚠️ API 调用接近限制: {calls_per_minute}/60")
          # 发送告警
          await send_alert(
              level="warning",
              message=f"API 调用接近限制: {calls_per_minute}/60"
          )
  ```

- [ ] 实现缓存命中率监控
- [ ] 实现爬虫健康检查
- [ ] 配置告警机制（API 调用 > 55 次/分钟）
- [ ] 配置定时监控任务（每分钟）

**验收标准**:
- ✅ 可以实时监控 API 调用次数
- ✅ 可以实时监控缓存命中率
- ✅ 告警机制正常工作

**输出文件**:
- `backend/app/tasks/monitoring_task.py`

---

#### 任务 B6: 集成测试与文档（优先级 P1）

**时间**: 17:00-18:00（1小时）

**任务清单**:
- [ ] 编写集成测试
  ```bash
  # backend/tests/tasks/test_crawler_task.py
  ```

- [ ] 运行集成测试
  ```bash
  pytest backend/tests/tasks/test_crawler_task.py -v
  ```

- [ ] 更新爬虫系统文档
- [ ] 提交代码并推送到远程仓库

**验收标准**:
- ✅ 集成测试通过
- ✅ 文档更新完成
- ✅ 代码提交成功

**输出文件**:
- `backend/tests/tasks/test_crawler_task.py`
- `docs/CRAWLER_SYSTEM.md`

---

## 👨‍💻 Frontend Agent - 任务清单

### 全天任务（9:00-18:00）

#### 任务 F1: 学习与准备（优先级 P2）

**时间**: 9:00-12:00（3小时）

**任务清单**:
- [ ] 阅读 PRD-09（动态社区池与预热期实施计划）
- [ ] 阅读 PRD-03 更新内容（后台爬虫系统）
- [ ] 了解社区池架构和预热期计划
- [ ] 准备 Beta 测试注册页面设计稿

**验收标准**:
- ✅ 理解动态社区池架构
- ✅ 理解预热期计划
- ✅ Beta 测试注册页面设计稿完成

---

#### 任务 F2: 环境准备（优先级 P2）

**时间**: 13:00-15:00（2小时）

**任务清单**:
- [ ] 验证前端开发环境
  ```bash
  cd frontend
  npm install
  npm run dev
  ```

- [ ] 验证与后端 API 连接
- [ ] 准备 Beta 测试注册页面组件

**验收标准**:
- ✅ 前端开发环境正常
- ✅ 可以连接后端 API
- ✅ 组件准备完成

---

#### 任务 F3: 代码审查与学习（优先级 P2）

**时间**: 15:00-18:00（3小时）

**任务清单**:
- [ ] 审查现有前端代码
- [ ] 学习 SSE 客户端实现
- [ ] 准备 Day 15-16 的开发任务

**验收标准**:
- ✅ 代码审查完成
- ✅ 理解 SSE 客户端实现
- ✅ Day 15-16 任务准备完成

---

## 👨‍💼 Lead - 任务清单

### 全天任务（9:00-18:00）

#### 任务 L1: 种子社区数据准备（优先级 P0）

**时间**: 9:00-11:00（2小时）

**任务清单**:
- [ ] 准备 50-100 个种子社区列表
- [ ] 分类社区（创业、产品、技术、营销、设计、通用）
- [ ] 填充社区元数据
  - categories（类别）
  - description_keywords（关键词）
  - daily_posts（每日帖子数，估算）
  - avg_comment_length（平均评论长度，估算）
  - quality_score（质量分数，初始 0.8-0.95）

**种子社区分类建议**:
```json
{
  "version": "1.0",
  "last_updated": "2025-10-14",
  "seed_communities": [
    {
      "name": "r/startups",
      "tier": "seed",
      "categories": ["startup", "business", "founder"],
      "description_keywords": ["startup", "founder", "product", "launch", "mvp", "funding"],
      "daily_posts": 200,
      "avg_comment_length": 150,
      "quality_score": 0.95
    },
    {
      "name": "r/Entrepreneur",
      "tier": "seed",
      "categories": ["startup", "business", "entrepreneur"],
      "description_keywords": ["entrepreneur", "business", "growth", "revenue", "marketing"],
      "daily_posts": 180,
      "avg_comment_length": 140,
      "quality_score": 0.90
    }
    // ... 共 50-100 个
  ]
}
```

- [ ] 保存到 `backend/config/seed_communities.json`
- [ ] 与 Backend Agent A 协作验证数据

**验收标准**:
- ✅ 至少 50 个种子社区
- ✅ JSON 格式正确
- ✅ 所有必需字段完整
- ✅ 社区名称有效

**输出文件**:
- `backend/config/seed_communities.json`

---

#### 任务 L2: 项目协调与监督（优先级 P0）

**时间**: 11:00-12:00, 14:00-15:00（2小时）

**任务清单**:
- [ ] 11:00 主持 Stand-up 会议（15 分钟）
  - Backend Agent A 汇报数据库迁移进度
  - Backend Agent B 汇报环境准备进度
  - Frontend Agent 汇报学习进度

- [ ] 监督各团队进度
- [ ] 解决阻塞问题
- [ ] 协调资源分配

- [ ] 14:00 中期检查（15 分钟）
  - 确认数据库迁移完成
  - 确认种子社区数据准备完成
  - 确认爬虫任务实现进度

**验收标准**:
- ✅ Stand-up 会议完成
- ✅ 中期检查完成
- ✅ 无阻塞问题

---

#### 任务 L3: 验收与总结（优先级 P0）

**时间**: 17:00-18:00（1小时）

**任务清单**:
- [ ] 17:00 主持 Stand-down 会议（30 分钟）
  - Backend Agent A 演示数据库迁移和社区池加载器
  - Backend Agent B 演示爬虫系统运行状态
  - Frontend Agent 汇报准备情况

- [ ] 验收 Day 13 成果
  - 数据库迁移完成 ✅
  - 种子社区数据准备完成 ✅
  - 社区池加载器实现完成 ✅
  - 爬虫任务实现完成 ✅
  - 预热爬虫启动并运行 ✅
  - 监控系统搭建完成 ✅

- [ ] 记录 Day 13 进度到 `reports/phase-log/day13-progress.md`
- [ ] 准备 Day 14 任务分配

**验收标准**:
- ✅ Stand-down 会议完成
- ✅ 所有 P0 任务完成
- ✅ Day 13 进度记录完成
- ✅ Day 14 任务分配完成

**输出文件**:
- `reports/phase-log/day13-progress.md`
- `reports/phase-log/day14-task-assignment.md`

---

## 📊 Day 13 验收标准

### 必须完成（P0）

- ✅ 数据库迁移完成（`community_pool` 和 `pending_communities` 表）
- ✅ 种子社区数据准备完成（50-100 个社区 JSON 文件）
- ✅ 社区池加载器实现完成
- ✅ 爬虫任务实现完成
- ✅ 预热爬虫启动并运行
- ✅ 50-100 个种子社区已爬取
- ✅ Redis 缓存命中率：100%（种子社区）

### 应该完成（P1）

- ✅ 监控系统搭建完成
- ✅ 单元测试和集成测试通过
- ✅ 文档更新完成
- ✅ 代码提交并推送到远程仓库

### 可选完成（P2）

- ✅ Frontend Agent 完成学习和准备
- ✅ Beta 测试注册页面设计稿完成

---

## 📅 时间线总览

```
09:00-09:15  Stand-up 会议（Lead 主持）
09:15-11:00  Backend A: 数据库迁移
             Backend B: 环境准备
             Lead: 种子社区数据准备
             Frontend: 学习 PRD

11:00-12:00  Backend A: 数据库迁移验证
             Backend B: 爬虫任务实现
             Lead: 协调监督
             Frontend: 学习 PRD

12:00-13:00  午休

13:00-14:00  Backend A: 社区池加载器实现
             Backend B: Celery Beat 配置
             Lead: 协调监督
             Frontend: 环境准备

14:00-14:15  中期检查（Lead 主持）

14:15-15:00  Backend A: 社区池加载器实现
             Backend B: 启动预热爬虫
             Lead: 协调监督
             Frontend: 环境准备

15:00-17:00  Backend A: 单元测试
             Backend B: 监控系统搭建
             Lead: 准备验收
             Frontend: 代码审查

17:00-17:30  Stand-down 会议（Lead 主持）

17:30-18:00  Backend A: 代码审查与文档
             Backend B: 集成测试与文档
             Lead: 记录进度，准备 Day 14
             Frontend: 准备 Day 15-16 任务
```

---

**文档版本**: 1.0  
**创建时间**: 2025-10-14  
**负责人**: Lead Agent  
**状态**: ✅ 准备执行

