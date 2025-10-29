# Implementation Plan: MVP 产品闭环补全

**Branch**: `007-mvp-product-loop` | **Date**: 2025-10-27 | **Spec**: [spec.md](./spec.md)

## Summary

围绕"让用户用起来、本地稳固正常跑"的目标，优先完成洞察卡片展示、质量看板监控、API 契约化、本地验收流程四大核心功能，确保产品闭环完整且本地环境稳定可用。

**当前进度**: Phase 1-2 完成，Phase 4 (US2 质量看板) 完成 ✅

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x (frontend)  
**Primary Dependencies**: FastAPI, Celery, Redis, PostgreSQL, React, Vite  
**Storage**: PostgreSQL (任务、分析、报告), Redis (缓存、队列)  
**Testing**: pytest (backend), vitest (frontend), Playwright (E2E)  
**Target Platform**: macOS/Linux 本地开发环境  
**Project Type**: Web application (backend + frontend)  
**Performance Goals**: 
- 洞察卡片 API 响应时间 < 500ms
- 质量看板刷新时间 < 5s
- 本地验收测试完成时间 < 3min

**Constraints**: 
- 必须在本地环境稳定运行（不依赖外部服务）
- 所有 API 必须有严格类型定义
- 核心功能必须有自动化验收测试

**Scale/Scope**: 
- 6 个 User Stories（4 个 P0 + 2 个 P1）
- 预计 2 周完成（Week 1: P0, Week 2: P1）
- 涉及后端 5 个新端点、前端 3 个新页面

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **单一职责**: 每个 User Story 独立可测试  
✅ **最小复杂度**: 复用现有基础设施（Redis、Celery、PostgreSQL）  
✅ **渐进式交付**: P0 功能优先，P1 功能可延后  
✅ **测试优先**: 所有核心功能有自动化验收测试  
✅ **文档同步**: 所有 API 变更同步更新 OpenAPI schema

## Project Structure

### Documentation (this feature)

```
.specify/specs/007-mvp-product-loop/
├── spec.md              # 功能规格（已完成）
├── plan.md              # 本文件
├── tasks.md             # 任务清单（待生成）
└── acceptance.md        # 验收报告（执行后生成）
```

### Source Code (repository root)

```
backend/
├── app/
│   ├── api/routes/
│   │   ├── insights.py          # 新增：洞察卡片 API
│   │   ├── metrics.py           # 新增：质量指标 API
│   │   └── reports.py           # 修改：新增行动位字段
│   ├── schemas/
│   │   ├── insight.py           # 新增：洞察卡片 schema
│   │   ├── metrics.py           # 新增：质量指标 schema
│   │   └── report_payload.py    # 修改：新增行动位字段
│   ├── services/
│   │   ├── insight_service.py   # 新增：洞察卡片服务
│   │   ├── metrics_service.py   # 新增：质量指标服务
│   │   └── analysis/
│   │       └── entity_matcher.py # 新增：实体词典匹配
│   └── models/
│       └── analysis.py          # 修改：新增行动位字段
├── config/
│   ├── entity_dictionary.yaml   # 新增：实体词典配置
│   └── scoring_rules.yaml       # 修改：新增阈值配置
├── scripts/
│   ├── calibrate_threshold.py   # 新增：阈值校准脚本
│   └── local_acceptance.py      # 新增：本地验收脚本
└── tests/
    ├── api/
    │   ├── test_insights.py     # 新增：洞察卡片 API 测试
    │   └── test_metrics.py      # 新增：质量指标 API 测试
    └── services/
        └── test_entity_matcher.py # 新增：实体匹配测试

frontend/
├── src/
│   ├── pages/
│   │   ├── InsightsPage.tsx     # 新增：洞察卡片页面
│   │   ├── DashboardPage.tsx    # 新增：质量看板页面
│   │   └── ReportPage.tsx       # 修改：新增行动位展示
│   ├── components/
│   │   ├── InsightCard.tsx      # 新增：洞察卡片组件
│   │   ├── EvidenceList.tsx     # 新增：证据列表组件
│   │   ├── MetricsChart.tsx     # 新增：指标图表组件
│   │   └── ActionItems.tsx      # 新增：行动位组件
│   ├── api/
│   │   ├── insights.ts          # 新增：洞察卡片 API 客户端
│   │   └── metrics.ts           # 新增：质量指标 API 客户端
│   └── types/
│       ├── insight.ts           # 新增：洞察卡片类型
│       └── metrics.ts           # 新增：质量指标类型
└── tests/
    └── acceptance/
        └── local-acceptance.test.ts # 新增：本地验收测试

data/
└── annotations/
    └── sample_200.csv           # 新增：人工标注样本

reports/
├── local-acceptance/            # 新增：本地验收报告目录
└── threshold-calibration/       # 新增：阈值校准报告目录
```

**Structure Decision**: 
- 复用现有 backend/frontend 结构
- 新增 insights/metrics 模块，独立于现有 reports 模块
- 配置文件集中在 backend/config/
- 验收脚本和报告独立目录

## Complexity Tracking

*无需填写 - 本功能未引入新的架构复杂度*

## Step-by-Step Plan

### Week 1: P0 功能（本地稳固可用）

#### Day 1-2: 洞察卡片 API + 前端

**目标**: 用户能看到结构化洞察卡片并点击查看证据

1. **后端 API**（6h）
   - 新增 `backend/app/schemas/insight.py`（InsightCard, Evidence schema）
   - 新增 `backend/app/services/insight_service.py`（从 Analysis 提取洞察）
   - 新增 `backend/app/api/routes/insights.py`（GET /api/insights/{task_id}）
   - 新增 `backend/tests/api/test_insights.py`（API 测试）

2. **前端页面**（6h）
   - 新增 `frontend/src/types/insight.ts`（类型定义）
   - 新增 `frontend/src/api/insights.ts`（API 客户端）
   - 新增 `frontend/src/components/InsightCard.tsx`（卡片组件）
   - 新增 `frontend/src/components/EvidenceList.tsx`（证据列表）
   - 新增 `frontend/src/pages/InsightsPage.tsx`（洞察页面）

3. **验收测试**（2h）
   - 手动测试：创建任务 → 查看洞察 → 点击证据 → 打开原帖
   - 自动测试：`pytest backend/tests/api/test_insights.py`

#### Day 3: 质量看板前端

**目标**: 运营能看到实时质量指标

1. **后端 API**（3h）
   - 新增 `backend/app/schemas/metrics.py`（DailyMetrics schema）
   - 新增 `backend/app/services/metrics_service.py`（复用现有指标计算）
   - 新增 `backend/app/api/routes/metrics.py`（GET /api/metrics/daily）
   - 新增 `backend/tests/api/test_metrics.py`（API 测试）

2. **前端页面**（5h）
   - 新增 `frontend/src/types/metrics.ts`（类型定义）
   - 新增 `frontend/src/api/metrics.ts`（API 客户端）
   - 新增 `frontend/src/components/MetricsChart.tsx`（图表组件，使用 recharts）
   - 新增 `frontend/src/pages/DashboardPage.tsx`（看板页面）

3. **验收测试**（1h）
   - 手动测试：访问 /dashboard → 查看指标 → 选择日期范围
   - 自动测试：`pytest backend/tests/api/test_metrics.py`

#### Day 4: API 契约强制执行

**目标**: 所有 API 有严格类型，CI 自动检测 breaking changes

1. **后端契约化**（4h）
   - 审查所有 API 端点，确保启用 `response_model`
   - 更新 `backend/app/api/routes/reports.py`（新增行动位字段）
   - 更新 `backend/app/schemas/report_payload.py`（新增 ActionItem）
   - 运行 `make update-api-schema` 更新 OpenAPI baseline

2. **CI 集成**（2h）
   - 修改 `.github/workflows/ci.yml`，新增 `make test-contract` 步骤
   - 测试 breaking change 检测：故意修改字段 → CI 失败

3. **验收测试**（1h）
   - 运行 `make test-contract` 确保通过
   - 修改 API 响应字段 → CI 失败并提示 breaking change

#### Day 5: 本地验收流程标准化

**目标**: 一键启动所有服务，自动验收核心功能

1. **验收脚本**（4h）
   - 新增 `backend/scripts/local_acceptance.py`（自动测试注册、登录、分析、报告、导出）
   - 新增 `Makefile::local-acceptance` 命令
   - 新增 `reports/local-acceptance/` 目录

2. **Golden Path 优化**（2h）
   - 优化 `Makefile::dev-golden-path`（确保所有服务稳定启动）
   - 新增健康检查：Redis、Celery、Backend、Frontend

3. **验收测试**（2h）
   - 运行 `make dev-golden-path` → 所有服务启动
   - 运行 `make local-acceptance` → 所有测试通过
   - 生成验收报告到 `reports/local-acceptance/2025-10-27.md`

---

### Week 2: P1 功能（数据质量提升）

#### Day 6-7: 阈值校准

**目标**: Precision@50 ≥ 0.6

1. **人工标注**（6h）
   - 抽样 200 条帖子到 `data/annotations/sample_200.csv`
   - 人工标注：机会/非机会、强/中/弱
   - 记录标注指南到 `docs/annotation-guide.md`

2. **阈值校准脚本**（4h）
   - 新增 `backend/scripts/calibrate_threshold.py`（网格搜索最优阈值）
   - 计算 Precision@50、Recall@50、F1@50
   - 输出最优阈值到 `config/scoring_rules.yaml`

3. **验收测试**（2h）
   - 运行 `python scripts/calibrate_threshold.py`
   - 验证 Precision@50 ≥ 0.6
   - 生成报告到 `reports/threshold-calibration/2025-10-27.md`

#### Day 8: 实体词典 v0

**目标**: 报告中能识别 50 个核心实体

1. **实体词典配置**（2h）
   - 新增 `backend/config/entity_dictionary.yaml`（手写 50 个核心词）
   - 分类：品牌（Notion、Slack）、功能（协作、自动化）、痛点（效率低、成本高）

2. **实体匹配服务**（4h）
   - 新增 `backend/app/services/analysis/entity_matcher.py`（按槽位统计命中度）
   - 集成到 `backend/app/services/analysis_engine.py`
   - 新增 `backend/tests/services/test_entity_matcher.py`（单元测试）

3. **验收测试**（2h）
   - 运行分析任务 → 查看报告 → 验证实体识别
   - 测试：`pytest backend/tests/services/test_entity_matcher.py`

#### Day 9-10: 报告行动位强化

**目标**: 报告有行动建议，产品经理能直接用

1. **后端结构调整**（4h）
   - 修改 `backend/app/models/analysis.py`（新增 action_items 字段）
   - 修改 `backend/app/schemas/report_payload.py`（新增 ActionItem schema）
   - 修改 `backend/app/services/analysis_engine.py`（生成行动位）
   - 数据库迁移：`make db-migrate MESSAGE="add action items"`

2. **前端渲染**（4h）
   - 新增 `frontend/src/components/ActionItems.tsx`（行动位组件）
   - 修改 `frontend/src/pages/ReportPage.tsx`（展示行动建议）
   - 高亮显示：问题定义、建议动作、置信度、优先级

3. **验收测试**（2h）
   - 运行分析任务 → 查看报告 → 验证行动位展示
   - 手动测试：复制建议话术 → 验证可用性

---

## Success Criteria

### Week 1 验收标准（P0）

- ⏳ 用户能在报告页面看到洞察卡片列表，点击展开查看证据（Phase 3 - 进行中）
- ✅ **运营能在质量看板查看实时指标，5 秒内刷新趋势图**（Phase 4 - 已完成 2025-10-27）
- ⏳ CI 中自动检测 API breaking changes，失败时提示详细错误（Phase 5 - 待开始）
- ⏳ 本地验收测试通过率 100%，所有核心功能正常运行（Phase 6 - 待开始）

**Phase 4 完成详情**:
- ✅ 后端 API: `GET /api/metrics/daily` 支持日期范围查询
- ✅ 前端页面: `/dashboard` 展示 4 个关键指标卡片 + 趋势图
- ✅ 图表组件: 使用 recharts，自定义 Tooltip 高亮异常值
- ✅ 测试覆盖: 3 个 service 层单元测试全部通过
- ✅ 类型安全: Pydantic schema + TypeScript 完整类型定义
- ✅ 最佳实践: 符合 FastAPI 和 React 最佳实践（exa-code 验证）

### Week 2 验收标准（P1）

- ✅ Precision@50 ≥ 0.6，洞察质量达到可用标准
- ✅ 报告中能识别 50 个核心实体，行动位字段完整展示

### 最终验收（2 周后）

- ✅ 运行 `make dev-golden-path` → 所有服务启动成功
- ✅ 运行 `make local-acceptance` → 所有测试通过
- ✅ 生成验收报告到 `reports/local-acceptance/final.md`
- ✅ 产品经理能独立使用产品（注册 → 分析 → 查看洞察 → 导出）

## Notes

- 所有配置文件（entity_dictionary.yaml、scoring_rules.yaml）纳入版本控制
- 每完成一个 User Story，立即运行本地验收测试
- 每天结束前提交代码，确保进度可追溯
- 遇到阻塞问题立即记录到 `reports/blockers.md`

