# 统一业务闭环架构 - 设计文档

## 一、架构设计概述

### 1.1 设计目标

将**报告生成主线**和**语义库闭环**有机统一，构建：
- **解耦**: 依赖接口而非实现
- **鲁棒**: 多级降级策略
- **可观测**: 全链路监控
- **可扩展**: 支持新增语义层级/标注类别

### 1.2 设计原则

```
1. 依赖倒置原则 (Dependency Inversion)
   - 高层模块不依赖低层模块，都依赖抽象
   - SemanticProvider 接口隔离具体实现

2. 事件驱动架构 (Event-Driven)
   - 模块间通过事件总线通信
   - 解耦发布者和订阅者

3. 多级缓存策略 (Multi-tier Cache)
   - L1: 进程内存 (TTL 5min)
   - L2: Redis (TTL 30min)
   - L3: PostgreSQL (持久化)

4. 优雅降级 (Graceful Degradation)
   - 每个外部依赖有fallback方案
   - 降级不影响核心流程

5. 可观测性优先 (Observability First)
   - 关键路径埋点监控
   - 指标/日志/追踪三位一体
```

---

## 二、核心组件设计

### 2.1 语义层 (Semantic Layer)

#### 2.1.1 SemanticProvider 接口

**职责**：提供统一的语义库访问接口，隔离具体实现

```python
# backend/app/interfaces/semantic_provider.py

from typing import Protocol, Callable, runtime_checkable
from dataclasses import dataclass
from datetime import datetime

@runtime_checkable
class SemanticProvider(Protocol):
    """
    语义库提供者接口

    设计原则：
    - 依赖倒置：所有消费者依赖此接口，而非具体实现
    - 可测试性：可轻松Mock进行单元测试
    - 可扩展性：可增加新的实现（如RemoteSemanticProvider）
    """

    async def load(self) -> UnifiedLexicon:
        """
        加载语义库

        Returns:
            UnifiedLexicon: 只读的语义库对象

        Raises:
            SemanticLoadError: 加载失败（所有降级策略已耗尽）
        """
        ...

    async def reload(self) -> None:
        """
        强制刷新缓存

        使用场景：
        - 收到 "lexicon.updated" 事件
        - 管理员手动触发刷新
        """
        ...

    async def subscribe(self, event: str, callback: Callable[[Any], None]) -> None:
        """
        订阅语义库事件

        Args:
            event: 事件名称（lexicon.updated / candidate.approved）
            callback: 异步回调函数
        """
        ...

    async def get_metrics(self) -> SemanticMetrics:
        """
        获取运行指标

        Returns:
            SemanticMetrics: 包含命中率/降级次数/延迟等
        """
        ...

@dataclass
class SemanticMetrics:
    """语义库运行指标"""
    db_hits: int                  # DB加载成功次数
    yaml_fallbacks: int           # YAML降级次数
    cache_hit_rate: float         # 缓存命中率 (0.0-1.0)
    last_refresh: datetime        # 最后刷新时间
    total_terms: int              # 词库总数
    load_latency_p50_ms: float    # P50加载延迟
    load_latency_p95_ms: float    # P95加载延迟
```

#### 2.1.2 RobustSemanticLoader 实现

**职责**：鲁棒的语义库加载器，支持多种策略和降级

```python
# backend/app/services/semantic/robust_loader.py

from enum import Enum
from pathlib import Path
from typing import Optional
import asyncio
from datetime import datetime, timedelta

class SemanticLoadStrategy(Enum):
    """语义库加载策略"""
    DB_ONLY = "db_only"               # 仅数据库（生产环境）
    DB_YAML_FALLBACK = "fallback"     # DB失败→YAML（默认）
    YAML_ONLY = "yaml_only"           # 仅YAML（测试环境）

class RobustSemanticLoader:
    """
    鲁棒的语义库加载器

    特性：
    - 多策略支持（DB_ONLY / FALLBACK / YAML_ONLY）
    - TTL缓存（避免频繁DB查询）
    - 指标收集（命中率/降级次数）
    - 事件通知（集成SemanticEventBus）
    """

    def __init__(
        self,
        session_factory: AsyncSessionMaker,
        fallback_yaml: Path,
        event_bus: SemanticEventBus,
        strategy: SemanticLoadStrategy = SemanticLoadStrategy.DB_YAML_FALLBACK,
        ttl_seconds: int = 300,  # 5分钟
    ):
        self._session_factory = session_factory
        self._fallback_yaml = fallback_yaml
        self._event_bus = event_bus
        self._strategy = strategy
        self._ttl = timedelta(seconds=ttl_seconds)

        # 缓存
        self._cached_lexicon: Optional[UnifiedLexicon] = None
        self._cache_expires_at: Optional[datetime] = None

        # 指标
        self._metrics = SemanticMetrics(
            db_hits=0,
            yaml_fallbacks=0,
            cache_hit_rate=0.0,
            last_refresh=datetime.now(),
            total_terms=0,
            load_latency_p50_ms=0.0,
            load_latency_p95_ms=0.0,
        )

        # 订阅事件
        self._event_bus.subscribe("lexicon.updated", self._on_lexicon_updated)

    async def load(self) -> UnifiedLexicon:
        """加载语义库（含缓存）"""
        # 检查缓存
        if self._is_cache_valid():
            return self._cached_lexicon

        # 根据策略加载
        start_time = datetime.now()
        try:
            if self._strategy == SemanticLoadStrategy.DB_ONLY:
                lexicon = await self._load_from_db()
                self._metrics.db_hits += 1
            elif self._strategy == SemanticLoadStrategy.YAML_ONLY:
                lexicon = self._load_from_yaml()
                self._metrics.yaml_fallbacks += 1
            else:  # FALLBACK
                try:
                    lexicon = await self._load_from_db()
                    self._metrics.db_hits += 1
                except Exception as e:
                    logger.warning(f"DB load failed, fallback to YAML: {e}")
                    lexicon = self._load_from_yaml()
                    self._metrics.yaml_fallbacks += 1

            # 更新缓存
            self._cached_lexicon = lexicon
            self._cache_expires_at = datetime.now() + self._ttl
            self._metrics.last_refresh = datetime.now()
            self._metrics.total_terms = len(lexicon.terms)

            # 记录延迟
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            self._update_latency_metrics(latency_ms)

            return lexicon
        except Exception as e:
            logger.error(f"All load strategies failed: {e}")
            raise SemanticLoadError("Failed to load semantic library") from e

    async def reload(self) -> None:
        """强制刷新"""
        self._cache_expires_at = None  # 使缓存失效
        await self.load()

    async def _on_lexicon_updated(self, payload: Any) -> None:
        """事件回调：语义库已更新"""
        logger.info("Received lexicon.updated event, reloading...")
        await self.reload()

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if self._cached_lexicon is None:
            return False
        if self._cache_expires_at is None:
            return False
        return datetime.now() < self._cache_expires_at

    async def _load_from_db(self) -> UnifiedLexicon:
        """从数据库加载"""
        async with self._session_factory() as session:
            repo = SemanticTermRepository(session)
            terms = await repo.get_all_approved()  # lifecycle='approved'
            return UnifiedLexicon.from_terms(terms)

    def _load_from_yaml(self) -> UnifiedLexicon:
        """从YAML加载"""
        return UnifiedLexicon.from_yaml(self._fallback_yaml)
```

#### 2.1.3 SemanticEventBus

**职责**：轻量级进程内事件总线

```python
# backend/app/events/semantic_bus.py

from typing import Callable, Dict, List, Any
from collections import defaultdict
import asyncio
import logging

logger = logging.getLogger(__name__)

class SemanticEventBus:
    """
    轻量级事件总线（进程内）

    设计：
    - 简单的发布-订阅模式
    - 异步回调执行
    - 异常隔离（单个回调失败不影响其他）

    后续可升级：
    - Redis Pub/Sub（跨进程）
    - Kafka（跨服务）
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)

    async def publish(self, event: str, payload: Any = None) -> None:
        """
        发布事件

        Args:
            event: 事件名称
            payload: 事件载荷（可选）
        """
        logger.info(f"Publishing event: {event}")
        callbacks = self._subscribers.get(event, [])

        # 并发执行所有回调
        tasks = []
        for callback in callbacks:
            tasks.append(self._safe_invoke(callback, payload))

        await asyncio.gather(*tasks, return_exceptions=True)

    def subscribe(self, event: str, callback: Callable[[Any], None]) -> None:
        """
        订阅事件

        Args:
            event: 事件名称
            callback: 回调函数（async def callback(payload)）
        """
        self._subscribers[event].append(callback)
        logger.info(f"Subscribed to event: {event}")

    async def _safe_invoke(self, callback: Callable, payload: Any) -> None:
        """安全调用回调（捕获异常）"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(payload)
            else:
                callback(payload)
        except Exception as e:
            logger.error(f"Event callback failed: {e}", exc_info=True)

# 全局单例
_event_bus = SemanticEventBus()

def get_event_bus() -> SemanticEventBus:
    """获取全局事件总线"""
    return _event_bus

# 标准事件定义
class Events:
    """标准事件常量"""
    LEXICON_UPDATED = "lexicon.updated"
    CANDIDATE_APPROVED = "candidate.approved"
    REPORT_COMPLETED = "report.completed"
    TIER_ADJUSTED = "tier.adjusted"
```

---

### 2.2 标注层改造

#### 2.2.1 TextClassifier 依赖注入

**改造前**：
```python
# ❌ 紧耦合
class TextClassifier:
    def __init__(self):
        self.lexicon = SemanticLoader.load()  # 直接依赖实现
```

**改造后**：
```python
# ✅ 依赖注入
class TextClassifier:
    def __init__(self, semantic_provider: SemanticProvider):
        self._provider = semantic_provider

    async def classify(self, text: str) -> Classification:
        lexicon = await self._provider.load()
        # 使用lexicon进行分类
        ...
```

#### 2.2.2 使用场景

```python
# 生产环境
semantic_provider = RobustSemanticLoader(
    session_factory=get_async_session,
    fallback_yaml=Path("config/unified_lexicon.yml"),
    event_bus=get_event_bus(),
    strategy=SemanticLoadStrategy.DB_YAML_FALLBACK,
)
text_classifier = TextClassifier(semantic_provider)

# 测试环境
mock_provider = MockSemanticProvider(fixed_lexicon)
text_classifier = TextClassifier(mock_provider)
```

---

### 2.3 监控层设计

#### 2.3.1 SystemHealthMetrics

**完整监控指标体系**：

```python
# backend/app/models/system_health.py

@dataclass
class SystemHealthMetrics:
    """系统健康度指标（5大层次）"""

    # 语义层
    semantic_db_hit_rate: float           # DB命中率
    semantic_yaml_fallback_count: int     # YAML降级次数
    semantic_term_count: int              # 词库总数
    semantic_load_latency_p95: float      # P95加载延迟

    # 标注层
    labeling_coverage: float              # 标注覆盖率
    labeling_quality_score: float         # 标注质量（人工抽检）
    entity_extraction_rate: float         # 实体提取率

    # 社区层
    community_count: int                  # 社区总数
    community_semantic_score_avg: float   # 平均语义评分
    tier_distribution: Dict[str, int]     # T1/T2/T3分布
    active_community_ratio: float         # 活跃社区占比

    # 分析层
    analysis_total_requests: int          # 总请求数
    analysis_success_rate: float          # 成功率
    analysis_avg_duration_sec: float      # 平均耗时
    sample_sufficiency_rate: float        # 样本充足率

    # 报告层
    report_generation_count: int          # 报告生成数
    report_quality_score: float           # 报告质量（用户打分）
    market_mode_usage: float              # market模式占比
    llm_success_rate: float               # LLM调用成功率

    # 时间戳
    collected_at: datetime                # 采集时间
```

#### 2.3.2 监控API

```python
# backend/app/api/admin/dashboard.py

@router.get("/dashboard/pipeline-health")
async def get_pipeline_health(
    db: AsyncSession = Depends(get_session),
) -> SystemHealthMetrics:
    """
    获取系统健康度指标

    聚合5大层次的监控数据：
    - 语义层：从 SemanticProvider.get_metrics()
    - 标注层：从 content_labels / content_entities 统计
    - 社区层：从 community_pool 统计
    - 分析层：从 tasks / analyses 统计
    - 报告层：从 reports 统计
    """
    # 语义层
    semantic_provider = get_semantic_provider()
    semantic_metrics = await semantic_provider.get_metrics()

    # 标注层
    labeling_coverage = await _compute_labeling_coverage(db)

    # 社区层
    tier_dist = await _compute_tier_distribution(db)

    # 分析层
    analysis_stats = await _compute_analysis_stats(db)

    # 报告层
    report_stats = await _compute_report_stats(db)

    return SystemHealthMetrics(
        semantic_db_hit_rate=semantic_metrics.cache_hit_rate,
        semantic_yaml_fallback_count=semantic_metrics.yaml_fallbacks,
        # ... 组装所有指标
        collected_at=datetime.now(),
    )
```

---

### 2.4 降级策略设计

#### 2.4.1 降级决策树

```
请求到达
  ↓
语义库加载
  ├─ DB可用？
  │   ├─ 是 → DB加载（metrics.db_hits++）
  │   └─ 否 → YAML降级（metrics.yaml_fallbacks++）
  ↓
社区选择
  ├─ semantic_quality_score可用？
  │   ├─ 是 → 按评分排序
  │   └─ 否 → 按活跃度排序（降级）
  ↓
数据采集
  ├─ posts_hot缓存命中？
  │   ├─ 是 → 读缓存
  │   └─ 否 → 查posts_raw → Reddit API（三级降级）
  ↓
内容标注
  ├─ UnifiedLexicon可用？
  │   ├─ 是 → 语义标注
  │   └─ 否 → 规则标注（降级）
  ↓
报告生成
  ├─ LLM API可用？
  │   ├─ 是 → 智能生成
  │   └─ 否 → 模板生成（降级）
  ↓
返回结果（附降级标记）
```

#### 2.4.2 降级标记

```python
@dataclass
class AnalysisResult:
    """分析结果（含降级信息）"""
    insights: Dict[str, Any]
    sources: Dict[str, Any]
    report_html: str
    confidence_score: float

    # 新增：降级追踪
    degradations: List[Degradation]  # 降级记录

@dataclass
class Degradation:
    """降级记录"""
    component: str          # 组件名（semantic_loader / llm_api / ...）
    reason: str             # 降级原因
    fallback_used: str      # 使用的降级方案
    impact: str             # 影响评估（minor / moderate / major）
    timestamp: datetime     # 降级时间
```

---

## 三、数据流设计

### 3.1 完整请求链路（含监控埋点）

```python
async def analyze_request_with_tracing(task_id: str):
    """带追踪的分析请求"""

    # Span 1: 语义库加载
    with tracer.start_span("semantic.load") as span1:
        lexicon = await semantic_provider.load()
        span1.set_attribute("term_count", len(lexicon.terms))
        span1.set_attribute("source", "db" if db_hit else "yaml")

    # Span 2: 社区选择
    with tracer.start_span("community.select") as span2:
        communities = await select_communities(lexicon, keywords)
        span2.set_attribute("selected_count", len(communities))
        span2.set_attribute("avg_semantic_score", avg_score)

    # Span 3: 数据采集
    with tracer.start_span("data.collect") as span3:
        posts = await collect_posts(communities)
        span3.set_attribute("posts_count", len(posts))
        span3.set_attribute("cache_hit_rate", cache_rate)

    # Span 4: 内容标注
    with tracer.start_span("labeling.classify") as span4:
        labels = await classify_batch(posts, lexicon)
        span4.set_attribute("labeled_count", len(labels))

    # Span 5: 信号提取
    with tracer.start_span("analysis.extract") as span5:
        insights = await extract_signals(posts, labels)
        span5.set_attribute("pain_count", len(insights.pain_points))

    # Span 6: 报告生成
    with tracer.start_span("report.generate") as span6:
        report = await generate_report(insights, mode="market")
        span6.set_attribute("quality_score", report.confidence_score)
        span6.set_attribute("llm_used", llm_success)

    return report
```

### 3.2 事件流

```
候选词审核通过事件流:
  ↓
SemanticCandidateRepository.approve()
  ↓
INSERT INTO semantic_terms (lifecycle='approved')
  ↓
event_bus.publish("candidate.approved", {term_id, canonical})
  ↓
订阅者1: SemanticLoader.reload()
  ↓
订阅者2: 触发社区重评分任务
  ↓
订阅者3: 记录审计日志
```

---

## 四、接口契约

### 4.1 SemanticProvider契约

```python
# 契约测试
class TestSemanticProviderContract:
    """所有SemanticProvider实现必须通过的契约测试"""

    async def test_load_returns_lexicon(self, provider: SemanticProvider):
        """load()必须返回UnifiedLexicon对象"""
        lexicon = await provider.load()
        assert isinstance(lexicon, UnifiedLexicon)
        assert len(lexicon.terms) > 0

    async def test_reload_updates_cache(self, provider: SemanticProvider):
        """reload()必须刷新缓存"""
        lex1 = await provider.load()
        await provider.reload()
        lex2 = await provider.load()
        # 如果DB有更新，lex2应该不同

    async def test_metrics_available(self, provider: SemanticProvider):
        """get_metrics()必须返回有效指标"""
        metrics = await provider.get_metrics()
        assert metrics.db_hits >= 0
        assert metrics.yaml_fallbacks >= 0
        assert 0.0 <= metrics.cache_hit_rate <= 1.0
```

---

## 五、性能优化设计

### 5.1 缓存策略

```python
# L1: 进程内存（最快，5分钟TTL）
_lexicon_cache: Optional[UnifiedLexicon] = None

# L2: Redis（跨进程共享，30分钟TTL）
await redis.set("lexicon:v1", lexicon.to_json(), ex=1800)

# L3: PostgreSQL（持久化）
SELECT * FROM semantic_terms WHERE lifecycle='approved'
```

### 5.2 批量查询优化

**改造前**：
```python
# ❌ N+1查询
for post in posts:
    labels = db.query(ContentLabel).filter_by(content_id=post.id).all()
```

**改造后**：
```python
# ✅ 批量查询
post_ids = [p.id for p in posts]
labels_map = db.query(ContentLabel).filter(
    ContentLabel.content_id.in_(post_ids)
).all()
labels_by_post = defaultdict(list)
for label in labels_map:
    labels_by_post[label.content_id].append(label)
```

---

## 六、安全性设计

### 6.1 输入验证

```python
def validate_semantic_term(term: str) -> bool:
    """验证候选词安全性"""
    # 长度限制
    if len(term) > 100:
        return False
    # 字符白名单
    if not re.match(r'^[A-Za-z0-9\s\-_]+$', term):
        return False
    # SQL注入检查
    if any(kw in term.lower() for kw in ['drop', 'delete', 'insert']):
        return False
    return True
```

### 6.2 权限控制

```python
# 仅管理员可审核候选词
@router.post("/admin/semantic-candidates/{id}/approve")
async def approve_candidate(
    id: int,
    current_user: User = Depends(get_current_admin_user),  # 权限检查
):
    ...
```

---

## 七、扩展性设计

### 7.1 新增语义层级

**当前**：L1/L2/L3/L4

**扩展**：增加L5（细粒度特征）

```python
# layer_definitions.yml
L5:
  name: "微观特征层"
  weight: 0.05
  description: "极细粒度的功能特性"
```

只需修改配置，无需改代码。

### 7.2 新增标注类别

**当前**：PAIN / SOLUTION / OTHER

**扩展**：增加NEUTRAL / PRAISE

```python
class Category(Enum):
    PAIN = "pain"
    SOLUTION = "solution"
    NEUTRAL = "neutral"     # 新增
    PRAISE = "praise"       # 新增
    OTHER = "other"
```

TextClassifier自动支持新类别（基于UnifiedLexicon动态加载）。

---

## 八、测试策略

### 8.1 单元测试

```python
# 接口契约测试
TestSemanticProviderContract

# 组件隔离测试
test_robust_loader_db_fallback()
test_event_bus_pub_sub()
test_text_classifier_with_mock_provider()
```

### 8.2 集成测试

```python
# 端到端流程测试
test_analyze_to_report_pipeline()
test_candidate_approval_triggers_reload()
```

### 8.3 性能测试

```python
# 压力测试
test_concurrent_100_requests()
test_cache_hit_rate_under_load()
```

---

## 九、部署架构

### 9.1 服务拓扑

```
┌──────────────────┐
│  Nginx (反向代理) │
└────────┬─────────┘
         │
    ┌────▼─────┐
    │  Gunicorn │ (多进程)
    │  Worker-1 │ ─┐
    │  Worker-2 │ ─┼─→ SemanticEventBus (进程内)
    │  Worker-3 │ ─┘
    └────┬──────┘
         │
    ┌────▼────┐
    │  Celery │ (后台任务)
    │  Worker │
    └────┬────┘
         │
    ┌────▼─────────────┐
    │  PostgreSQL       │
    │  - semantic_terms │
    │  - community_pool │
    └──────────────────┘
```

### 9.2 灰度发布

```
Phase 1: 10%流量 → 新架构（YAML_ONLY，验证功能）
Phase 2: 50%流量 → 新架构（DB_FALLBACK，验证性能）
Phase 3: 100%流量 → 新架构（DB_ONLY，生产稳定）
```

---

## 十、总结

本设计文档定义了统一业务闭环架构的**核心组件**、**接口契约**、**数据流**、**降级策略**和**监控体系**。

**关键设计亮点**：
1. 依赖倒置 → 解耦合
2. 事件驱动 → 解耦通知
3. 多级缓存 → 性能优化
4. 优雅降级 → 鲁棒性
5. 全链路追踪 → 可观测性

**下一步**：参考 [plan.md](./plan.md) 和 [tasks.md](./tasks.md) 开始分阶段实施。
