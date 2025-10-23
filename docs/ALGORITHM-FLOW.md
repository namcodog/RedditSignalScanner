# Reddit Signal Scanner - 算法调用链路文档

**版本**: v0.1.0  
**生成时间**: 2025-10-22  
**文档类型**: 算法架构与调用流程

---

## 目录

- [1. 算法调用总览](#1-算法调用总览)
- [2. 完整调用链路](#2-完整调用链路)
- [3. 核心算法模块](#3-核心算法模块)
- [4. 算法执行流程](#4-算法执行流程)
- [5. 数据流转图](#5-数据流转图)
- [6. 算法配置文件](#6-算法配置文件)

---

## 1. 算法调用总览

### 1.1 算法执行位置

**关键点**: 算法在**后台Celery任务**中执行，不在API接口中执行。

```
用户请求 → API接口 → Celery任务 → 算法引擎 → 数据库存储 → API返回结果
```

### 1.2 算法模块分布

```
backend/app/
├── api/routes/
│   ├── analyze.py              # API入口：创建分析任务
│   └── reports.py              # API出口：返回分析结果
├── tasks/
│   └── analysis_task.py        # Celery任务：调度算法执行
├── services/
│   ├── analysis_engine.py      # 核心引擎：四步流水线
│   ├── analysis/               # 算法子模块
│   │   ├── opportunity_scorer.py    # 机会评分算法
│   │   ├── deduplicator.py         # 去重算法（MinHash + LSH）
│   │   ├── signal_extraction.py    # 信号提取算法
│   │   ├── keyword_extraction.py   # 关键词提取
│   │   ├── template_matcher.py     # 模板匹配
│   │   ├── text_cleaner.py         # 文本清洗
│   │   ├── sample_guard.py         # 样本检查
│   │   └── community_discovery.py  # 社区发现
│   ├── reporting/
│   │   └── opportunity_report.py   # 报告生成（行动位）
│   └── evaluation/
│       └── threshold_optimizer.py  # 阈值优化
└── models/
    ├── posts_storage.py        # 数据模型：PostHot, PostRaw
    ├── analysis.py             # 分析结果模型
    └── report.py               # 报告模型
```

---

## 2. 完整调用链路

### 2.1 用户发起分析请求

```
POST /api/analyze
{
  "product_description": "一款帮助开发者快速构建API的SaaS工具"
}
```

**处理流程**:

1. **API层** (`backend/app/api/routes/analyze.py`)
   - 接收请求
   - 验证JWT Token
   - 创建Task记录（状态：pending）
   - 返回task_id和SSE端点

2. **任务调度** (`backend/app/api/routes/analyze.py::_schedule_analysis`)
   - 判断环境（dev/test/prod）
   - 开发环境：内联执行（绕过Celery）
   - 生产环境：发送到Celery队列

---

### 2.2 Celery任务执行

**文件**: `backend/app/tasks/analysis_task.py`

#### 主函数: `execute_analysis_pipeline(task_id)`

```python
async def execute_analysis_pipeline(task_id: uuid.UUID) -> Dict[str, Any]:
    """
    执行分析流水线
    
    步骤：
    1. 标记任务为processing
    2. 调用核心算法引擎
    3. 存储分析结果
    4. 标记任务为completed
    5. 缓存任务状态（SSE推送）
    """
```

#### 执行流程

```
1. _mark_processing(task_id)
   ↓ 更新Task状态为processing
   
2. _cache_status(task_id, progress=10, message="任务开始处理")
   ↓ 推送SSE事件
   
3. _cache_status(task_id, progress=25, message="正在发现相关社区...")
   ↓
   
4. result = await run_analysis(summary)  ← 调用核心算法
   ↓
   
5. _cache_status(task_id, progress=75, message="分析完成，生成报告中...")
   ↓
   
6. _store_analysis_results(task_id, result)
   ↓ 存储到Analysis和Report表
   
7. _cache_status(task_id, progress=100, message="分析完成")
   ↓ 推送完成事件
```

---

### 2.3 核心算法引擎

**文件**: `backend/app/services/analysis_engine.py`

#### 主函数: `run_analysis(task: TaskSummary) -> AnalysisResult`

这是整个系统的**算法核心**，实现PRD-03定义的四步流水线。

---

## 3. 核心算法模块

### 3.1 四步流水线架构

根据 `docs/PRD/PRD-03-分析引擎.md`，算法分为四个步骤：

```
步骤1: 智能社区发现
  ↓
步骤2: 并行数据采集
  ↓
步骤3: 信号提取
  ↓
步骤4: 智能排序输出
```

---

### 3.2 步骤1：智能社区发现

**目标**: 从社区池中筛选与产品描述最相关的社区

#### 算法模块

1. **关键词提取** (`keyword_extraction.py`)
   ```python
   keywords = _extract_keywords(product_description)
   # 提取产品描述中的关键词
   ```

2. **关键词增强** (`analysis_engine.py::_augment_keywords`)
   ```python
   keywords = _augment_keywords(keywords, product_description)
   # 添加同义词、相关词
   ```

3. **样本检查** (`sample_guard.py`)
   ```python
   sample_result = await _run_sample_guard(keywords, product_description)
   # 检查样本量是否 ≥1500
   # 不足时触发关键词补抓
   ```

4. **社区评分** (`analysis_engine.py::_score_communities`)
   ```python
   scored_communities = _score_communities(communities, keywords)
   # 基于关键词匹配度、社区质量分数评分
   # 返回Top 10社区
   ```

**数据来源**:
- 数据库表：`community_pool`（社区池）
- 字段：`name`, `categories`, `description_keywords`, `quality_score`, `priority`

---

### 3.3 步骤2：并行数据采集

**目标**: 从热缓存和Reddit API采集帖子数据

#### 算法模块

1. **缓存管理器** (`cache_manager.py`)
   ```python
   cache_manager = CacheManager()
   cached_posts = await cache_manager.get_cached_posts(community_name)
   # 从posts_hot表读取热缓存数据
   ```

2. **数据采集服务** (`data_collection.py`)
   ```python
   collection_service = DataCollectionService()
   result = await collection_service.collect_from_communities(
       communities=top_communities,
       keywords=keywords
   )
   # 并行采集多个社区的数据
   # 缓存优先：先读热缓存，不足时调用Reddit API
   ```

3. **Reddit客户端** (`reddit_client.py`)
   ```python
   reddit_client = RedditAPIClient()
   posts = await reddit_client.search_posts(
       subreddit=community_name,
       query=keywords,
       limit=50  # 优化：从100减少到50
   )
   # 调用Reddit API搜索帖子
   ```

**数据来源**:
- 热缓存：`posts_hot`表（最近24小时）
- 冷库：`posts_raw`表（历史30天）
- Reddit API：实时搜索

**缓存命中率计算**:
```python
cache_hit_rate = cache_hits / (cache_hits + cache_misses)
# 目标：≥90%
```

---

### 3.4 步骤3：信号提取

**目标**: 从帖子中提取痛点、竞品、机会信号

#### 算法模块

1. **文本清洗** (`text_cleaner.py`)
   ```python
   cleaned_text = clean_text(post_content)
   # 去除URL、代码块、引用块
   ```

2. **去重算法** (`deduplicator.py`)
   ```python
   deduplicated_posts = deduplicate_posts(posts, threshold=0.85)
   # 使用MinHash + LSH算法
   # 相似度阈值：0.85
   # 主贴保留，重复项聚合
   ```

   **去重统计**:
   ```python
   @dataclass
   class DeduplicationStats:
       total_posts: int           # 总帖子数
       unique_posts: int          # 去重后数量
       duplicate_posts: int       # 重复帖子数
       dedup_rate: float         # 去重率
       clusters_found: int       # 聚类数量
   ```

3. **机会评分** (`opportunity_scorer.py`)
   ```python
   scorer = OpportunityScorer()
   score = scorer.score_post(post_text, keywords)
   # 正负关键词对冲评分
   # 句级评分 + 上下文窗口（±1句）
   # 模板匹配加成/降权
   ```

   **评分规则** (配置文件：`config/scoring_rules.yaml`):
   - 正例关键词：need, urgent, looking for, problem, issue
   - 负例关键词：giveaway, for fun, just sharing
   - 语义否定：not interested, don't need

4. **模板匹配** (`template_matcher.py`)
   ```python
   matcher = TemplateMatcher()
   template_score = matcher.match(post_text)
   # 正向模板：金额、时间、数量表达
   # 反模板：招聘、抽奖、宣发
   ```

   **模板配置** (配置文件：`config/scoring_templates.yaml`):
   - 正向模板：`$\d+`, `\d+ hours`, `\d+ users`
   - 反模板：`hiring`, `giveaway`, `promo`

5. **信号提取器** (`signal_extraction.py`)
   ```python
   extractor = SignalExtractor()
   insights = extractor.extract_signals(posts, keywords)
   # 提取痛点、竞品、机会
   ```

   **提取逻辑**:
   - **痛点**: 包含负面情感词 + 问题描述
   - **竞品**: 提到其他产品名称
   - **机会**: 高评分帖子 + 需求表达

---

### 3.5 步骤4：智能排序输出

**目标**: 生成结构化报告和行动位

#### 算法模块

1. **置信度计算** (`analysis_engine.py::_calculate_confidence_score`)
   ```python
   confidence_score = _calculate_confidence_score(
       cache_hit_rate=0.92,
       posts_analyzed=1500,
       communities_found=10,
       pain_points_count=8,
       competitors_count=5,
       opportunities_count=12
   )
   # 综合评分：缓存命中率(40%) + 数据量(30%) + 洞察质量(30%)
   ```

2. **报告生成** (`reporting/opportunity_report.py`)
   ```python
   action_items = build_opportunity_reports(insights)
   # 生成行动位（Action Items）
   ```

   **行动位结构**:
   ```python
   @dataclass
   class OpportunityReport:
       problem_definition: str        # 问题定义
       evidence_chain: List[Evidence] # 证据链（2-3条）
       suggested_actions: List[str]   # 建议动作
       confidence: float              # 置信度
       urgency: float                 # 紧迫性
       product_fit: float             # 产品契合度
       priority: float                # 优先级 = confidence × urgency × product_fit
   ```

3. **HTML报告生成** (`analysis_engine.py::_generate_html_report`)
   ```python
   html_report = _generate_html_report(insights, sources)
   # 生成HTML格式的分析报告
   ```

---

## 4. 算法执行流程

### 4.1 完整流程图

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 智能社区发现                                              │
├─────────────────────────────────────────────────────────────┤
│ 输入: product_description                                    │
│ ↓                                                            │
│ 关键词提取 (keyword_extraction.py)                           │
│ ↓                                                            │
│ 关键词增强 (_augment_keywords)                               │
│ ↓                                                            │
│ 样本检查 (sample_guard.py)                                   │
│ ├─ 样本充足 → 继续                                           │
│ └─ 样本不足 → 关键词补抓 (keyword_crawler.py)                │
│ ↓                                                            │
│ 加载社区池 (community_pool表, 限制10个)                      │
│ ↓                                                            │
│ 社区评分 (_score_communities)                                │
│ ↓                                                            │
│ 输出: Top 10 社区                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. 并行数据采集                                              │
├─────────────────────────────────────────────────────────────┤
│ 输入: Top 10 社区, keywords                                  │
│ ↓                                                            │
│ 并行采集 (data_collection.py)                                │
│ ├─ 读取热缓存 (posts_hot表)                                  │
│ ├─ 读取冷库 (posts_raw表, 最近30天)                          │
│ └─ 调用Reddit API (reddit_client.py, 限制50条/社区)          │
│ ↓                                                            │
│ 计算缓存命中率 (cache_hit_rate)                              │
│ ↓                                                            │
│ 输出: 1500+ 帖子, cache_hit_rate ≥ 90%                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. 信号提取                                                  │
├─────────────────────────────────────────────────────────────┤
│ 输入: 1500+ 帖子                                             │
│ ↓                                                            │
│ 文本清洗 (text_cleaner.py)                                   │
│ ├─ 去除URL                                                   │
│ ├─ 去除代码块                                                │
│ └─ 去除引用块                                                │
│ ↓                                                            │
│ 去重 (deduplicator.py)                                       │
│ ├─ MinHash签名生成                                           │
│ ├─ LSH聚类（相似度阈值0.85）                                 │
│ └─ 主贴保留，重复项聚合                                       │
│ ↓                                                            │
│ 机会评分 (opportunity_scorer.py)                             │
│ ├─ 加载评分规则 (config/scoring_rules.yaml)                  │
│ ├─ 正例关键词评分                                            │
│ ├─ 负例关键词对冲                                            │
│ ├─ 语义否定检测                                              │
│ └─ 句级评分 + 上下文窗口（±1句）                             │
│ ↓                                                            │
│ 模板匹配 (template_matcher.py)                               │
│ ├─ 加载模板配置 (config/scoring_templates.yaml)              │
│ ├─ 正向模板匹配（金额、时间、数量）                          │
│ └─ 反模板匹配（招聘、抽奖、宣发）                            │
│ ↓                                                            │
│ 信号提取 (signal_extraction.py)                              │
│ ├─ 提取痛点 (pain_points)                                    │
│ ├─ 提取竞品 (competitors)                                    │
│ └─ 提取机会 (opportunities)                                  │
│ ↓                                                            │
│ 输出: insights = {pain_points, competitors, opportunities}   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. 智能排序输出                                              │
├─────────────────────────────────────────────────────────────┤
│ 输入: insights, sources                                      │
│ ↓                                                            │
│ 置信度计算 (_calculate_confidence_score)                     │
│ ├─ 缓存命中率权重 40%                                        │
│ ├─ 数据量权重 30%                                            │
│ └─ 洞察质量权重 30%                                          │
│ ↓                                                            │
│ 生成行动位 (opportunity_report.py)                           │
│ ├─ 问题定义 (problem_definition)                             │
│ ├─ 证据链 (evidence_chain, 2-3条)                            │
│ ├─ 建议动作 (suggested_actions)                              │
│ └─ 优先级 (priority = confidence × urgency × product_fit)    │
│ ↓                                                            │
│ 生成HTML报告 (_generate_html_report)                         │
│ ↓                                                            │
│ 输出: AnalysisResult                                         │
│ ├─ insights: {pain_points, competitors, opportunities}       │
│ ├─ sources: {communities, posts_analyzed, cache_hit_rate}    │
│ ├─ report_html: HTML格式报告                                 │
│ ├─ action_items: 行动位列表                                  │
│ └─ confidence_score: 置信度分数                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. 数据流转图

### 5.1 数据库表关系

```
用户请求
  ↓
Task (任务表)
  ├─ id: UUID
  ├─ user_id: UUID
  ├─ product_description: string
  ├─ status: pending|processing|completed|failed
  └─ created_at, completed_at
  
  ↓ (1对1)
  
Analysis (分析结果表)
  ├─ id: UUID
  ├─ task_id: UUID (外键)
  ├─ insights: JSONB {pain_points, competitors, opportunities}
  ├─ sources: JSONB {communities, posts_analyzed, cache_hit_rate}
  ├─ confidence_score: float
  └─ analysis_version: string
  
  ↓ (1对1)
  
Report (报告表)
  ├─ id: UUID
  ├─ analysis_id: UUID (外键)
  ├─ html_content: text
  ├─ template_version: string
  └─ generated_at: datetime
```

### 5.2 数据采集表

```
CommunityPool (社区池)
  ├─ name: string (r/webdev)
  ├─ tier: string (high|medium|low)
  ├─ categories: JSONB
  ├─ description_keywords: JSONB
  ├─ quality_score: float
  └─ is_active: boolean
  
  ↓ (用于采集)
  
PostHot (热缓存，24小时)
  ├─ post_id: string
  ├─ subreddit: string
  ├─ title: string
  ├─ content: text
  ├─ score: int
  ├─ created_at: datetime
  └─ extra_data: JSONB
  
PostRaw (冷库，30天+)
  ├─ post_id: string
  ├─ subreddit: string
  ├─ title: string
  ├─ content: text
  ├─ score: int
  ├─ created_at: datetime
  └─ extra_data: JSONB
```

---

## 6. 算法配置文件

### 6.1 评分规则配置

**文件**: `config/scoring_rules.yaml`

```yaml
positive_keywords:
  - need
  - urgent
  - looking for
  - problem
  - issue
  - help
  - solution

negative_keywords:
  - giveaway
  - for fun
  - just sharing
  - spam
  - promo

semantic_negation_patterns:
  - not interested
  - don't need
  - no longer
```

### 6.2 模板配置

**文件**: `config/scoring_templates.yaml`

```yaml
positive_templates:
  - pattern: '\$\d+'
    weight: 1.2
    description: 金额表达
  - pattern: '\d+ hours'
    weight: 1.1
    description: 时间表达
  - pattern: '\d+ users'
    weight: 1.15
    description: 用户数量

negative_templates:
  - pattern: 'hiring|job opening'
    weight: 0.5
    description: 招聘信息
  - pattern: 'giveaway|contest'
    weight: 0.3
    description: 抽奖活动
```

### 6.3 去重配置

**文件**: `config/deduplication.yaml`

```yaml
similarity_threshold: 0.85  # MinHash相似度阈值
num_perm: 128              # MinHash排列数
lsh_threshold: 0.85        # LSH阈值
max_cluster_size: 50       # 最大聚类大小
```

---

## 总结

### 算法调用链路

```
API请求 → Celery任务 → 核心引擎 → 算法模块 → 数据库 → API响应
```

### 关键算法

1. **社区发现**: 关键词提取 + 社区评分
2. **数据采集**: 缓存优先 + Reddit API
3. **信号提取**: 去重 + 评分 + 模板匹配
4. **报告生成**: 置信度计算 + 行动位生成

### 性能优化

- 社区查询：50 → 10（减少80%）
- Reddit API：100 → 50条/社区（减少50%）
- 去重性能：O(n²) → O(n)（MinHash + LSH）
- 缓存命中率：目标90%+

---

**文档维护**: 本文档随算法迭代更新，当前版本对应 Phase 3 完成状态。

