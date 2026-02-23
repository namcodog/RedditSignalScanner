# 016 - 统一业务闭环架构（语义库+报告生成）

- 状态: Proposed
- Owner: 架构/后端联合
- 创建日期: 2025-11-23
- 关联阶段: Spec 015（报告主线）+ 语义库系统
- 关联文件: [design](./design.md) / [plan](./plan.md) / [tasks](./tasks.md)

---

## 一、背景与问题陈述

### 1.1 当前系统两条线路

RedditSignalScanner 当前存在两条相对独立的业务线路：

#### 线路A：报告生成主线（Spec 015）
```
用户请求 → /api/analyze → 任务调度 → 分析引擎 → 报告服务 → 导出
                          ↓
                     社区选择 → 数据采集 → 信号提取 → 结果组装
                          ↓
                     Stats Layer → Clustering Layer → Report Agent
```

#### 线路B：语义库闭环
```
语义库 → 社区评分 → 动态分级 → 分级抓取 → 数据标注 → 候选词提取 → 审核 → 回流语义库
```

### 1.2 核心问题

虽然两条线路的基础组件都已实现，但存在**4大架构问题**：

1. **紧耦合**
   - `TextClassifier` 直接依赖 `UnifiedLexicon` 实现，无接口抽象
   - 特性开关分散（`ENABLE_UNIFIED_LEXICON`, `ENABLE_LLM_SUMMARY` 等）
   - 修改语义库加载逻辑需要改动多处代码

2. **单向流动**
   - 语义库 → 分析引擎 → 报告生成（单向依赖）
   - 缺少"报告质量 → 语义库优化"的反馈机制
   - 无法根据报告效果自动调整语义权重

3. **降级脆弱**
   - YAML fallback 逻辑在多处重复实现
   - 降级策略不统一（有的默认降级，有的直接报错）
   - 缺少统一的异常处理和监控

4. **监控盲区**
   - 无法追踪语义库命中率（DB vs YAML）
   - 无法关联语义质量与报告质量的因果关系
   - 系统健康度缺少量化指标

### 1.3 典型症状

- 语义库更新后需要手动重启所有服务才能生效
- 数据库连接失败时，部分模块降级到YAML，部分直接崩溃
- 无法回答"当前系统使用了多少次DB加载？多少次YAML降级？"
- 报告质量问题无法追溯到是语义库覆盖不足还是分析逻辑问题

---

## 二、目标与非目标

### 2.1 目标（V1）

1. **架构解耦**
   - 定义 `SemanticProvider` 接口，实现依赖倒置
   - 所有消费者（TextClassifier/SemanticScorer/CandidateExtractor）通过接口调用
   - 支持运行时切换实现（DB/YAML/Mock）

2. **事件驱动**
   - 建立轻量级事件总线（SemanticEventBus）
   - 语义库更新时自动通知所有消费者reload
   - 候选词审核通过时触发社区重评分

3. **统一降级策略**
   - 标准化 `SemanticLoadStrategy`（DB_ONLY/DB_YAML_FALLBACK/YAML_ONLY）
   - 统一异常处理和日志记录
   - 所有降级路径有监控指标

4. **可观测性**
   - 监控仪表盘展示5大层次指标（语义/标注/社区/分析/报告）
   - 每个关键环节有成功率/延迟/降级次数等指标
   - 支持追踪完整的请求链路

5. **闭环自动化**
   - 补齐"主动社区发现"任务（基于L1品牌词）
   - 补齐"报告质量反馈"机制
   - 强化T1/T2语义门槛（L1覆盖率+L4痛点密度）

### 2.2 非目标（V1）

- 不重写整个语义库系统，仅在其上增加抽象层
- 不改变数据库Schema（仅增加字段，不删除/重命名）
- 不迁移到新的事件系统（使用轻量级内存总线，后续可升级到Kafka）
- 不一次性清理所有历史代码，仅重构核心路径

---

## 三、统一架构设计

### 3.1 核心原则

```
依赖倒置 + 事件驱动 + 多级缓存 + 可观测性
```

### 3.2 架构层次

```
┌────────────────────────────────────────────────┐
│ 语义层 (Semantic Layer)                         │
│  - SemanticProvider (接口抽象)                  │
│  - RobustSemanticLoader (DB+YAML双轨)           │
│  - SemanticEventBus (事件通知)                  │
└────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────┐
│ 标注层 + 评分层 (并行消费语义库)                 │
│  - TextClassifier (内容分类)                    │
│  - SemanticScorer (社区质量评分)                │
│  - CandidateExtractor (候选词提取)              │
└────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────┐
│ 数据层 (Data Layer)                             │
│  - posts_hot / posts_raw                       │
│  - comments                                    │
│  - content_labels / content_entities           │
└────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────┐
│ 智能层 (Intelligence Layer)                     │
│  - TierIntelligence (动态分级)                  │
│  - CommunityDiscovery (主动发现)                │
└────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────┐
│ 分析层 (Analysis Layer)                         │
│  - AnalysisEngine (核心引擎)                    │
│  - StatsLayer / ClusteringLayer                │
│  - OpportunityScorer                           │
└────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────┐
│ 报告层 (Reporting Layer)                        │
│  - ReportService (统一服务)                     │
│  - T1MarketAgent (市场报告)                     │
│  - ControlledGenerator (技术报告)               │
└────────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────────┐
│ 反馈闭环 (Feedback Loop)                        │
│  - 报告质量指标 → 语义库权重调整                 │
│  - 候选词优先级 → 基于报告置信度                │
└────────────────────────────────────────────────┘
```

### 3.3 核心接口设计

#### SemanticProvider接口

```python
from typing import Protocol, Callable
from dataclasses import dataclass

class SemanticProvider(Protocol):
    """语义库提供者接口 - 依赖倒置核心"""

    async def load(self) -> UnifiedLexicon:
        """加载语义库（含TTL缓存）"""
        ...

    async def reload(self) -> None:
        """强制刷新缓存"""
        ...

    async def subscribe(self, event: str, callback: Callable) -> None:
        """订阅更新事件"""
        ...

    async def get_metrics(self) -> SemanticMetrics:
        """获取运行指标"""
        ...

@dataclass
class SemanticMetrics:
    """语义库运行指标"""
    db_hits: int              # DB加载成功次数
    yaml_fallbacks: int       # YAML降级次数
    cache_hit_rate: float     # 缓存命中率
    last_refresh: datetime    # 最后刷新时间
    total_terms: int          # 词库总数
    load_latency_ms: float    # 平均加载延迟
```

#### 降级策略枚举

```python
class SemanticLoadStrategy(Enum):
    """语义库加载策略"""
    DB_ONLY = "db_only"               # 仅数据库（生产默认）
    DB_YAML_FALLBACK = "fallback"     # DB失败→YAML（开发/测试）
    YAML_ONLY = "yaml_only"           # 仅YAML（纯离线）
```

#### 事件总线

```python
class SemanticEventBus:
    """轻量级事件总线（进程内）"""

    async def publish(self, event: str, payload: Any) -> None:
        """发布事件"""
        ...

    def subscribe(self, event: str, callback: Callable) -> None:
        """订阅事件"""
        ...

# 标准事件
EVENTS = {
    "lexicon.updated": "语义库已更新",
    "candidate.approved": "候选词已批准",
    "report.completed": "报告已生成",
    "tier.adjusted": "社区分级已调整",
}
```

### 3.4 监控指标体系

```yaml
语义层:
  semantic_db_hit_rate: 0.95         # DB命中率 > 95%
  semantic_fallback_count: <10/day   # YAML降级 < 10次/天
  semantic_load_latency_ms: <100     # 加载延迟 < 100ms

标注层:
  labeling_coverage: 0.80            # 标注覆盖率 > 80%
  label_quality_score: 0.90          # 标注质量 > 0.90

社区层:
  community_semantic_score_avg: 0.65  # 平均语义评分 > 0.65
  tier_distribution:                  # 分级分布
    T1: 20%
    T2: 50%
    T3: 30%

分析层:
  analysis_success_rate: 0.95         # 分析成功率 > 95%
  sample_sufficiency_rate: 0.90       # 样本充足率 > 90%

报告层:
  report_quality_score: 4.0/5.0       # 报告质量 > 4.0
  market_mode_usage: 0.60             # market模式占比 > 60%
```

### 3.5 降级策略矩阵

| 故障场景 | 降级方案 | 影响评估 | 恢复策略 |
|---------|---------|---------|---------|
| 语义库DB不可用 | YAML fallback | 缺失最新审核词条 | 15min TTL自动重试 |
| SemanticScorer超时 | 使用历史缓存分数 | 社区分数可能过期 | 6小时重新评分 |
| 候选词提取失败 | 跳过，不阻塞主流程 | 语义库扩展延迟 | 下周定时任务重试 |
| LLM API超时 | 降级到模板生成 | 报告内容质量下降 | 人工审核标记 |
| DB连接池耗尽 | 限流+排队机制 | 请求延迟增加 | 自动扩容Worker |

---

## 四、数据流与结合点

### 4.1 七个核心结合点

1. **语义库加载层**
   - `SemanticLoader` 作为统一入口
   - 被 `TextClassifier` / `SemanticScorer` / `CandidateExtractor` 调用

2. **社区质量评分**
   - `semantic_quality_score` 字段
   - 影响：社区选择 → 抓取调度 → 动态分级

3. **内容标注流水线**
   - `UnifiedLexicon` → `TextClassifier` → `ContentLabel` / `ContentEntity`
   - 再被 `AnalysisEngine` / `T1MarketAgent` 消费

4. **候选词反馈闭环**
   - 分析结果 → `CandidateExtractor` → `semantic_candidates` → 审核 → `semantic_terms`

5. **T1市场报告依赖**
   - `T1MarketAgent` → `T1StatsSnapshot` → `ContentLabel` → `UnifiedLexicon`

6. **Tier动态调级**
   - `TierIntelligence` 基于 `pain_density` / `brand_mentions` / `labeling_coverage`

7. **定时任务编排**
   - 30分钟抓取 / 12小时标注 / 每日调级 / 每周发现

### 4.2 完整请求链路

```
用户请求
  ↓
POST /api/analyze (product_description)
  ↓
SemanticLoader.load() → UnifiedLexicon
  ↓
社区选择（优先 semantic_quality_score > 0.7 的T1社区）
  ↓
数据采集（posts_hot缓存优先）
  ↓
TextClassifier.classify() → ContentLabel (基于UnifiedLexicon)
  ↓
SignalExtractor.extract() → 查询 content_labels（而非关键词匹配）
  ↓
PainCluster.cluster() → 基于aspect聚合
  ↓
T1StatsLayer.build_snapshot() → 统计指标
  ↓
T1ClusteringLayer.build_clusters() → 痛点簇
  ↓
T1MarketAgent.render() → Markdown报告（可选LLM润色）
  ↓
ReportService.get_report() → ReportPayload
  ↓
GET /api/report/{task_id} → 返回用户
  ↓
（可选）用户打分 → ReportQualityFeedback事件 → 语义库优化
```

---

## 五、执行顺序

### Phase 0: 架构重构准备（3天）
- 定义接口（SemanticProvider / SemanticMetrics / SemanticEventBus）
- 建立测试基线（当前功能回归测试）
- 设计事件Schema

### Phase 1: 语义层解耦（5天）
- 实现 RobustSemanticLoader
- 重构调用点（TextClassifier / SemanticScorer / CandidateExtractor）
- 集成事件总线
- 添加监控指标API

### Phase 2: 主线集成（7天）
- 修复 report_service.py 集成三层大脑
- 重构 AnalysisEngine 使用 content_labels
- LLM集成（premium模式）
- 端到端测试

### Phase 3: 后台闭环（5天）
- 实现主动社区发现任务
- 强化T1/T2语义门槛
- 候选词提取差异化（T1/T2/T3不同阈值）
- 报告质量反馈闭环

### Phase 4: 监控与优化（5天）
- 可观测性仪表盘
- 性能优化（Redis缓存/批量查询）
- 降级策略验证
- 压力测试

---

## 六、验收标准（Definition of Done）

### 6.1 功能完整性
- [ ] HTTP主线可稳定生成T1级市场报告（对齐 `t1价值的报告.md` 结构）
- [ ] 语义库可自动发现社区+提取候选词+审核回流
- [ ] 所有降级路径可用且有监控

### 6.2 性能指标
- [ ] 语义库DB命中率 > 95%
- [ ] 报告生成成功率 > 95%（premium模式）
- [ ] 端到端响应时间 < 5s（P95）
- [ ] 缓存命中率 > 90%

### 6.3 鲁棒性
- [ ] 模拟故障场景测试通过（DB断开/API超时/连接池耗尽）
- [ ] 压力测试100并发成功率 > 95%
- [ ] 所有异常有日志和告警

### 6.4 可观测性
- [ ] 监控仪表盘覆盖5大层次指标
- [ ] 关键指标有告警阈值配置
- [ ] 可追踪完整请求链路（tracing）

### 6.5 文档完整性
- [ ] Spec文档完整（spec.md / design.md / plan.md / tasks.md）
- [ ] 架构指南可供新人理解
- [ ] 运维手册可供oncall使用
- [ ] 接口有完整的docstring和类型注解

---

## 七、风险与缓解

### 7.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|-----|------|------|---------|
| 回归bug | 破坏现有功能 | 中 | Phase 0建立测试基线，每个Phase后回归 |
| 性能劣化 | 响应时间增加 | 中 | Phase 4压测验证，提前暴露瓶颈 |
| 数据迁移失败 | 语义库数据损坏 | 低 | 所有DB变更先在测试环境验证，有回滚脚本 |
| 依赖服务不稳定 | LLM API/Redis失败 | 中 | 所有外部依赖有降级策略 |

### 7.2 业务风险

| 风险 | 影响 | 概率 | 缓解措施 |
|-----|------|------|---------|
| 报告质量下降 | 用户体验差 | 低 | 对比测试，确保新版本>=旧版本 |
| 语义库覆盖率不足 | 社区评分不准 | 中 | T1/T2/T3差异化阈值，逐步提升 |
| 监控告警过多 | 运维负担增加 | 低 | 合理设置阈值，按优先级分级 |

### 7.3 进度风险

| 风险 | 影响 | 概率 | 缓解措施 |
|-----|------|------|---------|
| 工作量低估 | 延期交付 | 中 | Phase划分清晰，可根据进度调整优先级 |
| 依赖阻塞 | 后续Phase无法开始 | 低 | Phase 0-2串行，Phase 3-4可并行 |
| 人力不足 | 质量下降 | 低 | 核心模块代码review，关键测试人工验证 |

---

## 八、关联文档

- Spec 015: [分析报告主线与生成优化](../015-分析报告主线与生成优化.md)
- 主业务线说明书: [docs/archive/2025-11-主业务线说明书.md](../../../docs/archive/2025-11-主业务线说明书.md)
- 语义库指南: [docs/semantic-library-guide.md](../../../docs/semantic-library-guide.md)
- 参考报告: [reports/t1价值的报告.md](../../../reports/t1价值的报告.md)

---

## 九、更新日志

- 2025-11-23: 初始版本，定义统一架构和5个Phase
