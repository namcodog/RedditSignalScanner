# 统一业务闭环架构 - 执行计划

## Phase 划分总览

| Phase | 工期 | 目标 | 关键里程碑 |
|-------|------|------|-----------|
| Phase 0 | 3天 | 架构重构准备 | 接口定义+测试基线 |
| Phase 1 | 5天 | 语义层解耦 | 依赖注入完成 |
| Phase 2 | 7天 | 主线集成 | HTTP生成T1报告 |
| Phase 3 | 5天 | 后台闭环 | 自动化运转 |
| Phase 4 | 5天 | 监控与优化 | 上线验收 |
| **总计** | **25天** | **统一架构上线** | **生产可用** |

---

## Phase 0: 架构重构准备（3天）

### 目标
建立接口定义和测试基线，为后续重构提供安全网。

### 任务清单

#### 0.1 定义核心接口（1天）

**交付物**：
- `backend/app/interfaces/semantic_provider.py`
- `backend/app/events/semantic_bus.py`
- `backend/app/models/system_health.py`

**内容**：
```python
# semantic_provider.py
- SemanticProvider 协议接口
- SemanticMetrics 数据类
- SemanticLoadStrategy 枚举

# semantic_bus.py
- SemanticEventBus 类
- Events 常量类
- get_event_bus() 工厂函数

# system_health.py
- SystemHealthMetrics 数据类
- Degradation 数据类
```

**验收**：
- [ ] 所有接口有完整的docstring
- [ ] 所有类型注解正确（mypy检查通过）
- [ ] 接口设计review通过

#### 0.2 建立测试基线（1.5天）

**交付物**：
- `backend/tests/baseline/test_current_features.py`

**覆盖功能**：
```python
test_semantic_loader_basic()              # 当前加载器可用
test_community_selection()                # 社区选择逻辑
test_text_classifier_labeling()           # 内容标注
test_analysis_engine_basic()              # 分析引擎基础流程
test_report_service_technical_mode()      # 报告生成（technical）
test_report_service_market_mode()         # 报告生成（market，如果已实现）
```

**验收**：
- [ ] 所有基线测试通过
- [ ] 覆盖率 >= 70%（核心路径）
- [ ] 测试可重复运行（无随机失败）

#### 0.3 设计事件Schema（0.5天）

**交付物**：
- `docs/events-schema.md`

**内容**：
```yaml
事件名称: lexicon.updated
  触发时机: semantic_terms表插入/更新
  载荷: {term_id: int, canonical: str, action: "insert"|"update"}
  订阅者: [SemanticLoader, SemanticScorer]

事件名称: candidate.approved
  触发时机: semantic_candidates.status → approved
  载荷: {candidate_id: int, term_id: int, operator_id: uuid}
  订阅者: [TierIntelligenceService, AuditLogger]

事件名称: report.completed
  触发时机: Report记录创建
  载荷: {task_id: str, report_id: int, quality_score: float}
  订阅者: [QualityFeedbackService, MetricsCollector]

事件名称: tier.adjusted
  触发时机: community_pool.tier更新
  载荷: {community_id: int, old_tier: str, new_tier: str, reason: str}
  订阅者: [CrawlerScheduler, NotificationService]
```

**验收**：
- [ ] 事件Schema文档完整
- [ ] 载荷结构清晰
- [ ] 订阅者列表明确

### Phase 0 总验收
- [ ] 所有接口定义完成且review通过
- [ ] 基线测试全部通过
- [ ] 事件Schema文档化

---

## Phase 1: 语义层解耦与鲁棒性加固（5天）

### 目标
重构SemanticLoader，实现依赖注入，统一降级策略。

### 任务清单

#### 1.1 实现RobustSemanticLoader（2天）

**交付物**：
- `backend/app/services/semantic/robust_loader.py`

**核心功能**：
```python
class RobustSemanticLoader:
    - __init__(session_factory, fallback_yaml, event_bus, strategy, ttl)
    - async load() → UnifiedLexicon
    - async reload() → None
    - async _load_from_db() → UnifiedLexicon
    - _load_from_yaml() → UnifiedLexicon
    - _is_cache_valid() → bool
    - async _on_lexicon_updated(payload)
    - _update_latency_metrics(latency_ms)
    - async get_metrics() → SemanticMetrics
```

**降级逻辑**：
```python
if strategy == DB_ONLY:
    return await _load_from_db()
elif strategy == YAML_ONLY:
    return _load_from_yaml()
else:  # FALLBACK
    try:
        return await _load_from_db()
    except Exception:
        logger.warning("DB load failed, fallback to YAML")
        return _load_from_yaml()
```

**验收**：
- [ ] 三种策略都可用（DB_ONLY/FALLBACK/YAML_ONLY）
- [ ] TTL缓存生效（5分钟）
- [ ] 指标正确统计（db_hits/yaml_fallbacks/latency）
- [ ] 单元测试通过（含Mock DB）

#### 1.2 重构TextClassifier依赖注入（1天）

**文件**：
- `backend/app/services/text_classifier.py`

**改造**：
```python
# Before
class TextClassifier:
    def __init__(self):
        self.lexicon = SemanticLoader.load()  # ❌ 直接依赖

# After
class TextClassifier:
    def __init__(self, semantic_provider: SemanticProvider):
        self._provider = semantic_provider  # ✅ 依赖注入

    async def classify(self, text: str) -> Classification:
        lexicon = await self._provider.load()
        # ... 使用lexicon
```

**调用点更新**：
```python
# backend/app/services/labeling/comments_labeling.py
# backend/app/services/analysis/pain_cluster.py
# backend/app/tasks/comments_task.py
```

**验收**：
- [ ] TextClassifier接受SemanticProvider参数
- [ ] 所有调用点更新完成
- [ ] 单元测试通过（使用MockProvider）
- [ ] 回归测试通过

#### 1.3 重构SemanticScorer依赖注入（1天）

**文件**：
- `backend/app/services/semantic/semantic_scorer.py`
- `backend/scripts/score_with_semantic.py`

**改造**：
```python
class SemanticScorer:
    def __init__(self, semantic_provider: SemanticProvider):
        self._provider = semantic_provider

    async def score_theme(
        self,
        texts: List[str],
        sample_size: int = 100,
    ) -> LayeredScore:
        lexicon = await self._provider.load()
        # ... 计算分层覆盖率
```

**验收**：
- [ ] SemanticScorer接受SemanticProvider参数
- [ ] `score_with_semantic.py` 脚本可用
- [ ] 分层评分逻辑不变
- [ ] 单元测试通过

#### 1.4 集成事件总线（0.5天）

**触发点**：
```python
# backend/app/repositories/semantic_candidate_repository.py
async def approve(self, candidate_id: int, ...) -> SemanticTerm:
    # ... 插入semantic_terms
    await event_bus.publish(
        Events.CANDIDATE_APPROVED,
        {"term_id": term.id, "canonical": term.canonical}
    )
```

**订阅点**：
```python
# backend/app/services/semantic/robust_loader.py
event_bus.subscribe(Events.LEXICON_UPDATED, self._on_lexicon_updated)

# backend/app/services/tier_intelligence.py
async def on_candidate_approved(payload):
    logger.info(f"New term approved: {payload['canonical']}")
    # 可选：触发社区重评分
```

**验收**：
- [ ] approve()后触发事件
- [ ] SemanticLoader订阅事件并reload
- [ ] 手动测试：approve → 30秒内reload成功

#### 1.5 添加监控指标API（0.5天）

**文件**：
- `backend/app/api/admin/metrics.py`

**接口**：
```python
@router.get("/metrics/semantic")
async def get_semantic_metrics() -> SemanticMetrics:
    provider = get_semantic_provider()
    return await provider.get_metrics()
```

**验收**：
- [ ] `GET /api/admin/metrics/semantic` 可访问
- [ ] 返回db_hits/yaml_fallbacks/cache_hit_rate等
- [ ] 权限控制（仅管理员）

### Phase 1 总验收
- [ ] RobustSemanticLoader实现完整
- [ ] TextClassifier/SemanticScorer依赖注入完成
- [ ] 事件总线集成且可用
- [ ] 监控API返回正确指标
- [ ] 所有单元测试通过
- [ ] 回归测试通过

---

## Phase 2: 主线集成三层大脑+语义库（7天）

### 目标
打通HTTP主线，让报告生成完整利用语义资产。

### 任务清单

#### 2.1 修复report_service.py集成（2天）

**文件**：
- `backend/app/services/report_service.py`

**任务**：
1. 启用 `_build_t1_market_report_md()` 函数
2. 修复已知bug：
   - 空指针检查（`insights` / `sources` 可能为None）
   - 异常处理（LLM API失败时降级）
3. 配置简化：
   ```python
   # 废弃分散的开关
   # ENABLE_MARKET_REPORT / ENABLE_UNIFIED_LEXICON / ENABLE_LLM_SUMMARY

   # 统一到
   REPORT_QUALITY_LEVEL = "basic" | "standard" | "premium"

   # basic: 规则引擎 + 模板
   # standard: 语义库 + 模板
   # premium: 语义库 + LLM
   ```

**验收**：
- [ ] `REPORT_QUALITY_LEVEL=premium` 时调用T1MarketAgent
- [ ] 空指针检查到位
- [ ] LLM失败时降级到模板
- [ ] 配置文档更新（.env.example）

#### 2.2 重构AnalysisEngine使用content_labels（2天）

**文件**：
- `backend/app/services/analysis_engine.py`
- `backend/app/services/analysis/signal_extractor.py`

**改造**：

**Before（关键词匹配）**：
```python
def extract_pain_points(posts: List[Post]) -> List[PainPoint]:
    pains = []
    for post in posts:
        if any(kw in post.text.lower() for kw in ["hate", "frustrated", "issue"]):
            pains.append(PainPoint(...))
```

**After（查询content_labels）**：
```python
async def extract_pain_points(
    db: AsyncSession,
    post_ids: List[str]
) -> List[PainPoint]:
    # 批量查询
    labels = await db.execute(
        select(ContentLabel)
        .where(ContentLabel.content_id.in_(post_ids))
        .where(ContentLabel.category == Category.PAIN)
    )
    # 按aspect聚合
    pain_by_aspect = defaultdict(list)
    for label in labels:
        pain_by_aspect[label.aspect].append(label)
    # ...
```

**验收**：
- [ ] SignalExtractor改为查询content_labels
- [ ] 不再使用硬编码关键词
- [ ] 批量查询（避免N+1）
- [ ] 单元测试通过（Mock DB）

#### 2.3 PainCluster基于DB聚合（1天）

**文件**：
- `backend/app/services/analysis/pain_cluster.py`

**改造**：
```python
async def cluster_pain_points(
    db: AsyncSession,
    subreddit_keys: List[str],
    lookback_days: int = 365,
) -> List[PainCluster]:
    # SQL聚合
    stmt = (
        select(
            ContentLabel.aspect,
            func.count().label("count"),
        )
        .join(Comment, ...)
        .where(ContentLabel.category == Category.PAIN)
        .where(Comment.created_utc >= cutoff_date)
        .group_by(ContentLabel.aspect)
    )

    # 为每个aspect采样代表性评论
    for aspect, count in results:
        samples = await _sample_top_comments(db, aspect, limit=5)
        clusters.append(PainCluster(
            topic=ASPECT_LABELS[aspect],
            size=count,
            aspects=[aspect],
            sample_comments=samples,
        ))
```

**验收**：
- [ ] 基于DB聚合而非规则分箱
- [ ] 采样top 5评论（按score排序）
- [ ] 输出与旧版结构兼容

#### 2.4 LLM集成（premium模式）（1.5天）

**文件**：
- `backend/app/services/report/t1_market_agent.py`

**Prompt模板**：
```python
BATTLEFIELD_PROMPT = """
根据以下社区数据生成目标用户画像：
社区：{subreddit}
帖子量：{post_count}/月
评论量：{comment_count}/月
痛点密度：{pain_density}

请输出：
1. 目标用户画像（2-3句）
2. 核心痛点（3个）
3. 策略建议（3条）

格式：JSON
"""

USER_VOICE_PROMPT = """
从以下5条原始评论中提炼最能引起共鸣的表述：
{raw_comments}

输出：精炼后的1句话引语（<30字）
"""

OPPORTUNITY_CARD_PROMPT = """
基于以下痛点簇生成商业机会卡：
痛点主题：{topic}
样本数：{size}
关键词：{keywords}

输出：
1. 机会描述（2-3句）
2. 目标客户群
3. 预估ROI（基于样本数推测市场规模）
"""
```

**实现**：
```python
async def _generate_battlefield_with_llm(
    self,
    community: str,
    metrics: dict,
) -> str:
    prompt = BATTLEFIELD_PROMPT.format(**metrics)
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"LLM failed, fallback to template: {e}")
        return self._generate_battlefield_template(community, metrics)
```

**验收**：
- [ ] premium模式调用LLM API
- [ ] 失败时降级到模板
- [ ] 3个Prompt模板都可用
- [ ] 生成内容质量人工review

#### 2.5 端到端测试（0.5天）

**文件**：
- `backend/tests/e2e/test_unified_pipeline.py`

**测试**：
```python
async def test_analyze_to_market_report_premium():
    # 创建分析任务
    task = await create_analysis_task("跨境支付")

    # 等待完成
    await wait_for_task(task.id, timeout=300)

    # 获取报告
    report = await get_report(task.id, mode="market")

    # 验证结构
    assert "## 已分析赛道" in report.markdown
    assert "## 决策卡片" in report.markdown
    assert "## 核心战场推荐" in report.markdown
    assert "## 用户痛点" in report.markdown
    assert "## 商业机会" in report.markdown

    # 验证质量
    assert report.confidence_score >= 0.7
    assert len(report.degradations) == 0  # 无降级
```

**验收**：
- [ ] 端到端测试通过
- [ ] 报告结构对齐 `t1价值的报告.md`
- [ ] 置信度 >= 0.7

### Phase 2 总验收
- [ ] HTTP主线可生成T1报告
- [ ] 报告包含4张决策卡片
- [ ] 分析引擎使用content_labels（而非关键词）
- [ ] LLM集成且有降级
- [ ] 端到端测试通过

---

## Phase 3: 后台闭环自动化（5天）

### 目标
补齐语义库自进化的自动化环节。

### 任务清单

#### 3.1 实现主动社区发现任务（2天）

**文件**：
- `backend/app/tasks/discovery_task.py`

**实现**：
```python
@celery_app.task(name="tasks.discovery.semantic_discovery")
async def semantic_community_discovery():
    """基于语义库L1品牌词主动发现社区"""

    # 1. 从语义库提取L1品牌词（top 20 by weight）
    lexicon = await semantic_provider.load()
    brands = sorted(
        [t for t in lexicon.terms if t.layer == "L1"],
        key=lambda x: x.weight,
        reverse=True
    )[:20]

    # 2. 构造Reddit搜索query
    for brand in brands:
        query = f"{brand.canonical} subreddit recommendations"
        results = await reddit_client.search_communities(query, limit=10)

        # 3. 初始语义评分
        for sub in results:
            score = await semantic_scorer.score_theme(
                await reddit_client.sample_posts(sub, limit=50)
            )

            # 4. 写入community_pool（tier=T3, 待验证）
            if score.layered_score > 0.4:
                await community_repo.create(
                    subreddit_key=sub,
                    tier="low",  # T3
                    semantic_quality_score=score.layered_score,
                    discovered_by="semantic_discovery",
                )
```

**Celery定时配置**：
```python
# backend/app/core/celery_app.py
beat_schedule = {
    "semantic-discovery-weekly": {
        "task": "tasks.discovery.semantic_discovery",
        "schedule": crontab(day_of_week=0, hour=2),  # 每周日凌晨2点
    },
}
```

**验收**：
- [ ] 任务可手动触发
- [ ] 发现至少10个候选社区
- [ ] 初始评分合理（>0.4）
- [ ] 写入community_pool

#### 3.2 强化T1/T2语义门槛（1天）

**文件**：
- `backend/app/services/tier_intelligence.py`

**修改阈值**：
```python
# Before
class PromoteToT1:
    min_posts_per_day: float = 100
    min_pain_density: float = 0.35

# After
class PromoteToT1:
    min_posts_per_day: float = 100
    min_pain_density: float = 0.35
    min_l1_coverage: float = 0.50  # 新增：L1覆盖率>50%
    min_l4_density: float = 0.30   # 新增：L4痛点密度>30%

class PromoteToT2:
    min_posts_per_day: float = 50
    min_pain_density: float = 0.25
    min_l1_coverage: float = 0.30  # 新增
    min_l4_density: float = 0.20   # 新增
```

**判定逻辑**：
```python
def should_promote_to_t1(metrics: CommunityMetrics) -> bool:
    return (
        metrics.posts_per_day >= 100
        and metrics.pain_density >= 0.35
        and metrics.semantic_score >= 0.75  # 已有
        and metrics.l1_coverage >= 0.50      # 新增
        and metrics.l4_pain_density >= 0.30  # 新增
    )
```

**验收**：
- [ ] T1社区L1覆盖率均>50%
- [ ] T2社区L1覆盖率均>30%
- [ ] 人工抽检：T1社区质量显著高于旧标准

#### 3.3 候选词提取差异化（1天）

**文件**：
- `backend/app/services/semantic/candidate_extractor.py`

**改造**：
```python
async def extract_from_communities(
    self,
    tier: str,  # "high" / "medium" / "low"
    lookback_days: int = 30,
) -> List[SemanticCandidate]:
    # T1/T2/T3不同阈值
    min_freq = {
        "high": 10,    # T1: 至少出现10次
        "medium": 5,   # T2: 至少出现5次
        "low": 3,      # T3: 至少出现3次
    }[tier]

    # 不同社区级别提炼不同层级
    preferred_layers = {
        "high": ["L1", "L4"],     # T1重点提炼品牌+痛点
        "medium": ["L2", "L3"],   # T2重点提炼功能+工具
        "low": ["L1", "L2"],      # T3边界探索
    }[tier]

    # ... 提取逻辑
```

**验收**：
- [ ] T1候选词min_frequency=10
- [ ] T2候选词min_frequency=5
- [ ] T3候选词min_frequency=3
- [ ] T1优先提炼L1/L4，T2优先L2/L3

#### 3.4 报告质量反馈闭环（1天）

**文件**：
- `backend/app/models/report.py`（增加字段）
- `backend/app/api/v1/endpoints/reports.py`（打分接口）

**DB变更**：
```sql
ALTER TABLE reports ADD COLUMN quality_rating FLOAT;
ALTER TABLE reports ADD COLUMN user_feedback TEXT;
```

**打分接口**：
```python
@router.post("/reports/{report_id}/rate")
async def rate_report(
    report_id: int,
    rating: float = Field(ge=1.0, le=5.0),
    feedback: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    # 更新report.quality_rating
    await report_repo.update(report_id, quality_rating=rating)

    # 发布事件
    await event_bus.publish(
        Events.REPORT_COMPLETED,
        {
            "report_id": report_id,
            "quality_score": rating,
            "feedback": feedback,
        }
    )
```

**反馈处理**：
```python
# backend/app/services/quality_feedback.py
async def on_report_completed(payload):
    """根据报告质量调整候选词优先级"""
    if payload["quality_score"] < 3.0:
        # 低分报告：提高相关候选词的审核优先级
        report = await get_report(payload["report_id"])
        low_confidence_terms = extract_low_confidence_terms(report)

        for term in low_confidence_terms:
            await semantic_repo.increase_candidate_priority(term)
```

**验收**：
- [ ] 打分接口可用
- [ ] 触发 `report.completed` 事件
- [ ] 低分报告提高相关候选词优先级

### Phase 3 总验收
- [ ] 主动社区发现任务运行成功
- [ ] T1社区质量提升（L1覆盖率>50%）
- [ ] 候选词提取区分T1/T2/T3
- [ ] 报告质量反馈流程可用

---

## Phase 4: 监控与优化（5天）

### 目标
建立可观测性仪表盘，性能调优，验证降级策略。

### 任务清单

#### 4.1 可观测性仪表盘（2天）

**文件**：
- `backend/app/api/admin/dashboard.py`

**接口**：
```python
@router.get("/dashboard/pipeline-health")
async def get_pipeline_health() -> SystemHealthMetrics:
    # 聚合5大层次指标
    ...

@router.get("/dashboard/degradation-log")
async def get_degradation_log(hours: int = 24) -> List[Degradation]:
    # 最近24小时降级记录
    ...
```

**前端展示**（可选）：
```tsx
<DashboardCard title="语义层">
  <Metric label="DB命中率" value={semantic.db_hit_rate} threshold={0.95} />
  <Metric label="YAML降级" value={semantic.yaml_fallbacks} threshold={10} />
</DashboardCard>
```

**验收**：
- [ ] 仪表盘API可访问
- [ ] 返回5大层次指标
- [ ] 前端展示（如已有UI框架）

#### 4.2 性能优化（1.5天）

**任务**：
1. Redis缓存集成
   ```python
   # 缓存UnifiedLexicon对象
   await redis.set("lexicon:v1", lexicon.to_json(), ex=1800)

   # 缓存社区评分
   await redis.set(f"score:{subreddit}", score, ex=21600)
   ```

2. 批量查询优化
   ```python
   # Before: N+1
   for post in posts:
       labels = db.query(...).filter_by(content_id=post.id).all()

   # After: 批量
   post_ids = [p.id for p in posts]
   labels = db.query(...).filter(content_id.in_(post_ids)).all()
   ```

3. 数据库索引检查
   ```sql
   CREATE INDEX IF NOT EXISTS idx_community_semantic_score
   ON community_pool(semantic_quality_score DESC);

   CREATE INDEX IF NOT EXISTS idx_content_labels_category_aspect
   ON content_labels(category, aspect);
   ```

**验收**：
- [ ] Redis缓存命中率>80%
- [ ] 批量查询减少DB round-trips
- [ ] 索引添加完成

#### 4.3 降级策略验证（1天）

**模拟故障场景**：
```python
# Test 1: 语义库DB不可用
async def test_semantic_db_failure():
    # 关闭DB连接
    await db_pool.close()

    # 验证YAML降级
    lexicon = await semantic_provider.load()
    assert lexicon is not None
    assert metrics.yaml_fallbacks > 0

# Test 2: SemanticScorer超时
async def test_semantic_scorer_timeout():
    # Mock超时
    with patch("semantic_scorer.score_theme", side_effect=asyncio.TimeoutError):
        # 验证使用历史缓存
        score = await get_community_score(subreddit)
        assert score is not None  # 从缓存读取

# Test 3: LLM API超时
async def test_llm_timeout():
    # Mock超时
    with patch("openai.ChatCompletion.create", side_effect=TimeoutError):
        # 验证模板降级
        report = await generate_report(insights, mode="premium")
        assert "战场画像" in report  # 模板生成
        assert report.degradations[0].component == "llm_api"
```

**验收**：
- [ ] 所有降级场景测试通过
- [ ] 降级有明确日志
- [ ] 降级标记记录到 `Degradation`

#### 4.4 压力测试（0.5天）

**工具**：Locust / Apache Bench

**场景**：
```python
# locustfile.py
class AnalysisUser(HttpUser):
    @task
    def create_analysis(self):
        self.client.post("/api/analyze", json={
            "product_description": "跨境支付解决方案"
        })

    @task(2)
    def get_report(self):
        self.client.get("/api/report/test-task-id")

# 运行
locust -f locustfile.py --users 100 --spawn-rate 10
```

**指标目标**：
- 成功率 >= 95%
- P95响应时间 < 5s
- 缓存命中率 > 90%

**验收**：
- [ ] 100并发成功率>95%
- [ ] P95<5s
- [ ] 无内存泄漏

### Phase 4 总验收
- [ ] 监控仪表盘上线
- [ ] 性能优化完成（缓存+索引）
- [ ] 降级策略全部验证
- [ ] 压力测试通过

---

## 总体验收（上线标准）

### 功能完整性
- [ ] HTTP主线可稳定生成T1级市场报告
- [ ] 语义库可自动发现社区+提取候选词+审核回流
- [ ] 所有降级路径可用且有监控

### 性能指标
- [ ] 语义库DB命中率 > 95%
- [ ] 报告生成成功率 > 95%（premium模式）
- [ ] 端到端响应时间 < 5s（P95）
- [ ] 缓存命中率 > 90%

### 鲁棒性
- [ ] 模拟故障场景测试通过
- [ ] 压力测试100并发成功率 > 95%
- [ ] 所有异常有日志和告警

### 可观测性
- [ ] 监控仪表盘覆盖5大层次指标
- [ ] 关键指标有告警阈值配置
- [ ] 可追踪完整请求链路

### 文档完整性
- [ ] Spec文档完整（4个md文件）
- [ ] 架构指南可供新人理解
- [ ] 运维手册可供oncall使用
- [ ] 接口有完整的docstring和类型注解

---

## 风险缓解策略

### 回归风险
- **策略**：Phase 0建立测试基线，每个Phase后运行回归测试
- **回滚**：每个Phase打Git tag，出问题可快速回滚

### 性能风险
- **策略**：Phase 4压测验证，提前暴露瓶颈
- **预案**：准备降级配置（关闭LLM/降低并发）

### 数据风险
- **策略**：所有DB变更先在测试环境验证
- **备份**：变更前备份 `semantic_terms` / `community_pool`

### 进度风险
- **策略**：Phase划分清晰，可根据进度调整优先级
- **并行**：Phase 3-4部分任务可并行（监控与发现任务）

---

## 灰度发布计划

### Week 1-2: Phase 0-1（开发环境）
- 仅开发环境部署
- 单元测试+回归测试

### Week 3: Phase 2（测试环境）
- 测试环境部署
- 端到端测试+人工验证

### Week 4: Phase 3-4（预发布）
- 预发布环境10%流量
- 监控指标+降级测试

### Week 5: 灰度上线
- 生产环境10% → 50% → 100%
- 持续监控降级次数

---

## 下一步

参考 [tasks.md](./tasks.md) 查看详细任务清单和跟踪进度。
