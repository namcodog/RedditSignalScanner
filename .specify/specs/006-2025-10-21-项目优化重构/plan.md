# Implementation Plan: Reddit Signal Scanner 项目优化重构

**Branch**: `006-project-optimization-refactor` | **Date**: 2025-10-21 | **Spec**: [spec.md](./spec.md)

## Summary

本次优化重构旨在清理技术债务、建立质量监控体系、完善产品闭环（导出功能）、优化数据质量（去重二级化）、提升开发效率（API 契约化）、降低运营成本（缓存策略）。分为三个里程碑：M0（1 周）清理债务 + 最小可用产品，M1（1 个月）产品闭环 + 质量提升，M2（1 季度）高级功能 + 优化。

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x (frontend)  
**Primary Dependencies**: FastAPI, Celery, Redis, PostgreSQL, React 18, Vite  
**Storage**: PostgreSQL (主数据库), Redis (缓存 + 消息队列)  
**Testing**: pytest (backend), vitest (frontend), Playwright (E2E)  
**Target Platform**: Linux server (backend), Modern browsers (frontend)  
**Project Type**: Web application (backend + frontend)  
**Performance Goals**: P95 端到端耗时 ≤ 5 分钟, 缓存命中率 ≥ 90%  
**Constraints**: 单条洞察成本下降 30%, 重复率 ≤ 8%  
**Scale/Scope**: 200 个社区池, 18,260 条帖子, 支持 100+ 并发用户

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 架构原则检查

✅ **单一职责**: 每个模块职责清晰（采集、分析、展示、导出）  
✅ **依赖倒置**: 使用接口抽象（如 `RedditClient`, `AnalysisEngine`）  
✅ **开闭原则**: 支持扩展（如新增导出格式、新增实体类型）  
✅ **最小惊讶**: API 设计符合 RESTful 规范  
⚠️ **复杂度控制**: NER v1 和趋势分析可能引入算法复杂度，需要评估

### 技术债务检查

🔴 **依赖目录入库**: 严重问题，必须立即清理  
🟡 **.env.local 入库**: 中等风险，已记录但暂缓处理  
🟡 **Reddit TOS 合规**: 中等风险，当前自用研究，后续启动合规清单

### 质量门禁

- **代码覆盖率**: 单元测试覆盖关键逻辑 ≥ 70%
- **类型检查**: `mypy --strict` 通过，前端 TypeScript 严格模式
- **Lint 清洁**: Black + isort (backend), ESLint + Prettier (frontend)
- **性能基准**: P95 端到端耗时 ≤ 5 分钟

## Project Structure

### Documentation (this feature)

```
.specify/specs/006-2025-10-21-项目优化重构/
├── spec.md              # 功能规格说明（本文档的输入）
├── plan.md              # 实施计划（本文档）
├── tasks.md             # 任务清单（待生成）
├── research.md          # 技术调研（待补充）
├── data-model.md        # 数据模型（待补充）
└── contracts/           # API 契约（待补充）
    ├── metrics-api.yaml
    ├── insights-api.yaml
    └── export-api.yaml
```

### Source Code (repository root)

```
backend/
├── app/
│   ├── api/
│   │   ├── endpoints/
│   │   │   ├── metrics.py          # 新增：质量指标 API
│   │   │   ├── insights.py         # 新增：洞察卡片 API
│   │   │   └── export.py           # 新增：导出 API
│   │   └── schemas/
│   │       ├── metrics.py          # 新增：指标响应模型
│   │       ├── insights.py         # 新增：洞察卡片响应模型
│   │       └── export.py           # 新增：导出请求/响应模型
│   ├── services/
│   │   ├── deduplication/
│   │   │   ├── minhash.py          # 新增：MinHash 去重
│   │   │   ├── simhash.py          # 新增：SimHash 去重
│   │   │   └── clustering.py       # 新增：主题聚类
│   │   ├── ner/
│   │   │   ├── extractor.py        # 新增：NER 实体抽取
│   │   │   ├── rules.py            # 新增：规则/词典
│   │   │   └── models.py           # 新增：小模型（可选）
│   │   ├── export/
│   │   │   ├── csv_exporter.py     # 新增：CSV 导出
│   │   │   ├── ppt_exporter.py     # 新增：PPT 导出
│   │   │   └── notion_exporter.py  # 新增：Notion 导出
│   │   ├── cache/
│   │   │   ├── embedding_cache.py  # 新增：Embedding 缓存
│   │   │   └── llm_cache.py        # 新增：LLM 调用缓存
│   │   └── metrics/
│   │       ├── collector.py        # 新增：指标采集
│   │       └── reporter.py         # 新增：报表生成
│   └── models/
│       ├── insight.py              # 新增：洞察卡片模型
│       └── entity.py               # 新增：实体模型
├── tests/
│   ├── unit/
│   │   ├── test_deduplication.py   # 新增：去重单元测试
│   │   ├── test_ner.py             # 新增：NER 单元测试
│   │   └── test_export.py          # 新增：导出单元测试
│   ├── integration/
│   │   ├── test_metrics_api.py     # 新增：指标 API 集成测试
│   │   └── test_insights_api.py    # 新增：洞察 API 集成测试
│   └── e2e/
│       └── test_critical_path.py   # 优化：只保留关键路径
└── scripts/
    └── cleanup_repo.sh             # 新增：仓库清理脚本

frontend/
├── src/
│   ├── api/
│   │   ├── types.ts                # 新增：自动生成的 API 类型
│   │   └── client.ts               # 优化：使用生成的类型
│   ├── components/
│   │   ├── InsightCard.tsx         # 新增：洞察卡片组件
│   │   ├── EvidencePanel.tsx       # 新增：证据面板组件
│   │   ├── MetricsDashboard.tsx    # 新增：质量看板组件
│   │   └── ExportButton.tsx        # 新增：导出按钮组件
│   ├── pages/
│   │   ├── InsightsPage.tsx        # 新增：洞察列表页
│   │   └── MetricsPage.tsx         # 新增：质量看板页
│   └── hooks/
│       ├── useInsights.ts          # 新增：洞察数据 Hook
│       └── useMetrics.ts           # 新增：指标数据 Hook
└── tests/
    └── e2e/
        └── critical-path.spec.ts   # 优化：只保留关键路径

reports/
├── daily_metrics.jsonl             # 新增：每日指标日志
├── weekly_summary.md               # 新增：每周摘要报告
└── failed_e2e/                     # 新增：E2E 失败快照目录
    └── {timestamp}/
        ├── screenshot.png
        └── trace.json
```

**Structure Decision**: 
- 采用 Web 应用结构（backend + frontend）
- 后端按功能模块组织（api, services, models）
- 前端按组件类型组织（components, pages, hooks）
- 测试按层级组织（unit, integration, e2e）

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| NER 引入小模型 | 规则/词典无法覆盖所有实体类型 | 纯规则方法 F1 < 0.6，无法满足 ≥ 0.75 的要求 |
| 趋势分析引入时序聚类 | 需要识别新兴主题和突发事件 | 简单统计无法捕捉主题演化趋势 |

## Phase 0: Research & Design

### 技术调研清单

#### 去重算法调研
- [ ] MinHash 算法原理与实现（推荐库：`datasketch`）
- [ ] SimHash 算法原理与实现（推荐库：`simhash`）
- [ ] 主题聚类算法对比（HDBSCAN vs KMeans）
- [ ] 性能基准测试（10,000 条帖子去重耗时）

#### NER 技术调研
- [ ] 规则/词典方法（正则表达式 + 实体词典）
- [ ] 小模型选型（spaCy vs Flair vs BERT-NER）
- [ ] 标注工具选型（Label Studio vs Prodigy）
- [ ] F1 评估方法（标注集准备、交叉验证）

#### 导出功能调研
- [ ] CSV 导出库（Python `csv` 模块）
- [ ] PPT 导出库（`python-pptx`）
- [ ] Notion API 集成（`notion-client`）
- [ ] 模板设计（PPT 模板、Notion 数据库结构）

#### 缓存策略调研
- [ ] Embedding 缓存方案（Redis Hash vs 向量数据库）
- [ ] LLM 调用缓存方案（Redis String + TTL）
- [ ] 缓存失效策略（LRU vs TTL）
- [ ] 成本计算方法（API 调用次数 × 单价）

#### API 契约化调研
- [ ] FastAPI `response_model` 最佳实践
- [ ] OpenAPI 文档生成（自动 vs 手动）
- [ ] `openapi-typescript` 使用方法
- [ ] 前端 SDK 生成流程

### 数据模型设计

#### 洞察卡片（Insight Card）

```python
class InsightCard(BaseModel):
    id: UUID
    title: str                      # 洞察标题
    summary: str                    # 洞察摘要
    confidence: float               # 置信度 (0.0-1.0)
    time_window: str                # 时间窗口（如 "2025-10-14 to 2025-10-21"）
    subreddits: List[str]           # 子版块列表
    evidences: List[Evidence]       # 证据段落列表
    entities: List[Entity]          # 实体列表（NER 抽取）
    created_at: datetime
```

#### 证据段落（Evidence）

```python
class Evidence(BaseModel):
    id: UUID
    post_url: str                   # 原帖链接
    excerpt: str                    # 摘录（200 字以内）
    timestamp: datetime             # 帖子时间
    subreddit: str                  # 子版块
    score: int                      # 帖子分数
```

#### 实体（Entity）

```python
class Entity(BaseModel):
    id: UUID
    type: EntityType                # 实体类型（品牌、功能、痛点、价格、平台、场景）
    value: str                      # 实体值（如 "Notion"）
    confidence: float               # 置信度 (0.0-1.0)
    source_post_id: str             # 来源帖子 ID
```

#### 质量指标（Metrics）

```python
class QualityMetrics(BaseModel):
    date: date                      # 日期
    collection_success_rate: float  # 采集成功率
    deduplication_rate: float       # 去重率
    processing_time_p50: float      # 处理耗时 P50（秒）
    processing_time_p95: float      # 处理耗时 P95（秒）
    language_distribution: Dict[str, float]  # 语言占比
    topic_drift: float              # 主题漂移（JS 散度）
    entity_recall: float            # 实体召回率
    cost_per_insight: float         # 单条洞察成本（美元）
```

### API 契约设计

#### 质量指标 API

```yaml
# contracts/metrics-api.yaml
GET /api/metrics:
  summary: 获取质量指标
  parameters:
    - name: start_date
      in: query
      schema:
        type: string
        format: date
    - name: end_date
      in: query
      schema:
        type: string
        format: date
    - name: metrics
      in: query
      schema:
        type: array
        items:
          type: string
          enum: [collection_success_rate, deduplication_rate, processing_time, cost]
  responses:
    200:
      content:
        application/json:
          schema:
            type: array
            items:
              $ref: '#/components/schemas/QualityMetrics'
```

#### 洞察卡片 API

```yaml
# contracts/insights-api.yaml
GET /api/insights:
  summary: 获取洞察卡片列表
  parameters:
    - name: task_id
      in: query
      schema:
        type: string
        format: uuid
    - name: entity_filter
      in: query
      schema:
        type: string
  responses:
    200:
      content:
        application/json:
          schema:
            type: array
            items:
              $ref: '#/components/schemas/InsightCard'
```

#### 导出 API

```yaml
# contracts/export-api.yaml
POST /api/export/csv:
  summary: 导出 CSV
  requestBody:
    content:
      application/json:
        schema:
          type: object
          properties:
            task_id:
              type: string
              format: uuid
  responses:
    200:
      content:
        text/csv:
          schema:
            type: string

POST /api/export/ppt:
  summary: 导出 PPT
  requestBody:
    content:
      application/json:
        schema:
          type: object
          properties:
            task_id:
              type: string
              format: uuid
  responses:
    200:
      content:
        application/vnd.openxmlformats-officedocument.presentationml.presentation:
          schema:
            type: string
            format: binary

POST /api/export/notion:
  summary: 导出到 Notion
  requestBody:
    content:
      application/json:
        schema:
          type: object
          properties:
            task_id:
              type: string
              format: uuid
            database_id:
              type: string
  responses:
    200:
      content:
        application/json:
          schema:
            type: object
            properties:
              notion_page_url:
                type: string
```

## Phase 1: M0 实施（1 周）

### 目标
清理技术债务、上线最小质量看板、洞察卡片 v0、E2E 收敛、CSV 导出

### 任务分解

#### Day 1-2: 仓库清理与 CI 优化
- [ ] 创建 `backend/scripts/cleanup_repo.sh` 脚本
- [ ] 移除 `node_modules/` 和 `venv/` 目录
- [ ] 更新 `.gitignore`（添加 `node_modules/`, `venv/`, `__pycache__/`, `.pytest_cache/`）
- [ ] 配置 GitHub Actions 依赖缓存
- [ ] 验证：仓库体积下降 ≥ 50%，CI 安装时长下降 ≥ 40%

#### Day 3-4: 最小质量看板 v0
- [ ] 创建 `backend/app/api/endpoints/metrics.py`
- [ ] 创建 `backend/app/services/metrics/collector.py`（采集成功率、重复率、处理耗时）
- [ ] 创建 `frontend/src/components/MetricsDashboard.tsx`
- [ ] 创建 `frontend/src/pages/MetricsPage.tsx`
- [ ] 验证：可访问 `/metrics` 页面，展示三项指标

#### Day 5-6: 洞察卡片 v0
- [ ] 创建 `backend/app/api/endpoints/insights.py`
- [ ] 创建 `backend/app/api/schemas/insights.py`（InsightCard, Evidence）
- [ ] 创建 `frontend/src/components/InsightCard.tsx`
- [ ] 创建 `frontend/src/components/EvidencePanel.tsx`
- [ ] 创建 `frontend/src/pages/InsightsPage.tsx`
- [ ] 验证：可浏览洞察卡片，点击展开证据

#### Day 7: E2E 收敛 + CSV 导出
- [ ] 优化 `backend/tests/e2e/test_critical_path.py`（只保留 3 条关键路径）
- [ ] 配置失败快照保存到 `reports/failed_e2e/`
- [ ] 创建 `backend/app/services/export/csv_exporter.py`
- [ ] 创建 `backend/app/api/endpoints/export.py`（CSV 导出）
- [ ] 创建 `frontend/src/components/ExportButton.tsx`
- [ ] 验证：E2E ≤ 5 分钟，CSV 导出可用

## Phase 2: M1 实施（1 个月）

### 目标
去重二级化、API 契约化、成本优化、导出完整版、NER v1、质量看板 v1

### Week 2: API 契约化 + 成本优化
- [ ] 后端启用严格 `response_model`
- [ ] 生成 OpenAPI 文档（`/openapi.json`）
- [ ] 前端运行 `openapi-typescript` 生成 `src/api/types.ts`
- [ ] 创建 `backend/app/services/cache/embedding_cache.py`
- [ ] 创建 `backend/app/services/cache/llm_cache.py`
- [ ] 验证：前端无手写类型，缓存命中率 ≥ 60%

### Week 3: 导出完整版
- [ ] 创建 `backend/app/services/export/ppt_exporter.py`
- [ ] 创建 `backend/app/services/export/notion_exporter.py`
- [ ] 设计 PPT 模板（标题页、要点页、证据页）
- [ ] 配置 Notion API 集成
- [ ] 验证：PPT 和 Notion 导出可用

### Week 4: 去重二级化 + 质量看板 v1
- [ ] 创建 `backend/app/services/deduplication/minhash.py`
- [ ] 创建 `backend/app/services/deduplication/simhash.py`
- [ ] 创建 `backend/app/services/deduplication/clustering.py`
- [ ] 扩展质量看板（语言占比、主题漂移、实体召回、成本）
- [ ] 配置每日报表自动生成
- [ ] 验证：重复率下降 ≥ 30%，主题簇纯度 ≥ 0.75

### Week 5: NER v1
- [ ] 创建 `backend/app/services/ner/extractor.py`
- [ ] 创建 `backend/app/services/ner/rules.py`（规则/词典）
- [ ] 准备标注集（200 条）
- [ ] 评估 F1 分数
- [ ] 前端实体高亮渲染
- [ ] 验证：F1 ≥ 0.75，实体可筛选

## Phase 3: M2 实施（1 季度）

### 目标
趋势分析 v1、竞品雷达、主动学习闭环

### Month 2: 趋势分析 v1
- [ ] 调研时序聚类算法（EARS/阈值+滑窗）
- [ ] 实现新兴主题检测
- [ ] 生成强度曲线
- [ ] 前端趋势卡片展示
- [ ] 验证：识别新兴主题（增长率 > 50%）

### Month 3: 竞品雷达 + 主动学习
- [ ] 实现竞品雷达生成（品牌/功能/口碑/价格）
- [ ] 前端雷达图可视化
- [ ] 实现主动学习闭环（低置信度样本池 → 标注 → 回灌）
- [ ] 验证：雷达图可导出，F1 提升或稳定

## Risk Mitigation

### 技术风险

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| NER F1 < 0.75 | 高 | 准备 Plan B（纯规则方法），降低目标到 0.65 |
| 去重算法性能差 | 中 | 使用 `datasketch` 库（已优化），限制样本量 ≤ 10,000 |
| PPT 导出失败 | 中 | 提供降级方案（只导出 CSV） |
| Notion API 限流 | 低 | 添加重试机制，限制导出频率 |

### 进度风险

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| M0 超期 | 中 | 砍掉 CSV 导出，放到 M1 |
| NER 标注集准备慢 | 高 | 使用合成数据 + 少量人工标注 |
| 趋势分析算法复杂 | 中 | 简化为基于阈值的突发检测 |

## Success Metrics

### M0 验收标准
- [ ] 仓库体积下降 ≥ 50%
- [ ] CI 安装时长下降 ≥ 40%
- [ ] 质量看板可访问
- [ ] 洞察卡片可浏览
- [ ] E2E ≤ 5 分钟
- [ ] CSV 导出可用

### M1 验收标准
- [ ] 重复率下降 ≥ 30%
- [ ] 前端无手写类型
- [ ] 单条洞察成本下降 ≥ 30%
- [ ] PPT 和 Notion 导出可用
- [ ] NER F1 ≥ 0.75
- [ ] 质量看板支持可配置

### M2 验收标准
- [ ] 趋势分析可识别新兴主题
- [ ] 竞品雷达可生成可视化
- [ ] 主动学习闭环运转

## Next Steps

1. **立即执行**: 创建 `tasks.md`（使用 `/speckit.tasks` 命令）
2. **Day 1**: 开始仓库清理与 CI 优化
3. **Week 1 结束**: 完成 M0 验收
4. **Week 2-5**: 执行 M1 任务
5. **Month 2-3**: 执行 M2 任务

