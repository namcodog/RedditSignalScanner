# Tasks: MVP 产品闭环补全

**Input**: [spec.md](./spec.md), [plan.md](./plan.md)  
**Prerequisites**: 现有基础设施（Redis、Celery、PostgreSQL、FastAPI、React）  
**Tests**: 包含单元测试、集成测试、验收测试

**Organization**: 任务按 User Story 分组，每个 Story 独立可测试

## Format: `[ID] [P?] [Story] Description`
- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 所属 User Story（US1-US6）
- 包含精确文件路径

---

## Phase 1: Setup（共享基础设施）

**Purpose**: 项目初始化和基础结构

- [ ] T001 创建 `.specify/specs/007-mvp-product-loop/` 目录结构
- [ ] T002 [P] 创建 `backend/config/entity_dictionary.yaml` 配置文件模板
- [ ] T003 [P] 创建 `data/annotations/` 目录
- [ ] T004 [P] 创建 `reports/local-acceptance/` 目录
- [ ] T005 [P] 创建 `reports/threshold-calibration/` 目录

---

## Phase 2: Foundational（阻塞性前置任务）

**Purpose**: 核心基础设施，必须在所有 User Story 之前完成

**⚠️ CRITICAL**: 此阶段完成前，所有 User Story 无法开始

- [ ] T006 审查现有 API 端点，列出缺少 `response_model` 的端点到 `reports/api-audit.md`
- [ ] T007 [P] 安装前端图表库 `recharts`：`cd frontend && npm install recharts`
- [ ] T008 [P] 更新 `backend/app/models/analysis.py`，新增 `action_items` JSON 字段（数据库迁移）
- [ ] T009 运行数据库迁移：`cd backend && make db-migrate MESSAGE="add action items to analysis"`

**Checkpoint**: 基础设施就绪 - User Story 实现可以并行开始

---

## Phase 3: User Story 1 - 洞察卡片展示与证据验证 (Priority: P0) 🎯 MVP

**Goal**: 用户能看到结构化洞察卡片并点击查看证据

**Independent Test**: 访问报告页面 → 点击洞察卡片 → 查看证据 → 打开原帖

### 后端实现

- [ ] T010 [P] [US1] 创建 `backend/app/schemas/insight.py`（InsightCard, Evidence schema）
- [ ] T011 [P] [US1] 创建 `backend/app/services/insight_service.py`（从 Analysis 提取洞察）
- [ ] T012 [US1] 创建 `backend/app/api/routes/insights.py`（GET /api/insights/{task_id}）
- [ ] T013 [US1] 新增 `backend/tests/api/test_insights.py`（API 集成测试）

### 前端实现

- [ ] T014 [P] [US1] 创建 `frontend/src/types/insight.ts`（InsightCard, Evidence 类型定义）
- [ ] T015 [P] [US1] 创建 `frontend/src/api/insights.ts`（API 客户端）
- [ ] T016 [P] [US1] 创建 `frontend/src/components/InsightCard.tsx`（卡片组件）
- [ ] T017 [P] [US1] 创建 `frontend/src/components/EvidenceList.tsx`（证据列表组件）
- [ ] T018 [US1] 创建 `frontend/src/pages/InsightsPage.tsx`（洞察页面，集成卡片和证据）
- [ ] T019 [US1] 更新 `frontend/src/App.tsx`，新增 `/insights/:taskId` 路由

### 验收测试

- [ ] T020 [US1] 手动测试：创建任务 → 访问 `/insights/{taskId}` → 点击卡片 → 验证证据链
- [x] T021 [US1] 运行后端测试：`cd backend && pytest tests/api/test_insights.py -v`
- [ ] T022 [US1] 记录验收结果到 `reports/local-acceptance/us1-insights.md`

**Checkpoint**: User Story 1 完成 - 洞察卡片功能独立可用

---

## Phase 4: User Story 2 - 质量看板实时监控 (Priority: P0) ✅ COMPLETED

**Goal**: 运营能看到实时质量指标

**Independent Test**: 访问 /dashboard → 查看指标 → 选择日期范围

### 后端实现

- [x] T023 [P] [US2] 创建 `backend/app/schemas/metrics.py`（DailyMetrics schema）
- [x] T024 [P] [US2] 创建 `backend/app/services/metrics_service.py`（复用 red_line_checker 指标）
- [x] T025 [US2] 创建 `backend/app/api/routes/metrics.py`（GET /api/metrics/daily）
- [x] T026 [US2] 新增 `backend/tests/api/test_metrics.py`（API 集成测试）

### 前端实现

- [x] T027 [P] [US2] 创建 `frontend/src/types/metrics.ts`（DailyMetrics 类型定义）
- [x] T028 [P] [US2] 创建 `frontend/src/api/metrics.ts`（API 客户端）
- [x] T029 [P] [US2] 创建 `frontend/src/components/MetricsChart.tsx`（图表组件，使用 recharts）
- [x] T030 [US2] 创建 `frontend/src/pages/DashboardPage.tsx`（看板页面，集成图表）
- [x] T031 [US2] 更新 `frontend/src/router/index.tsx`，新增 `/dashboard` 路由

### 验收测试

- [x] T032 [US2] 手动测试：访问 `/dashboard` → 查看指标 → 选择日期范围 → 验证刷新速度
- [x] T033 [US2] 运行后端测试：`cd backend && pytest tests/api/test_metrics.py -v`（3/3 通过）
- [x] T034 [US2] 记录验收结果到 `reports/local-acceptance/us2-dashboard.md`

**Checkpoint**: ✅ User Story 2 完成 - 质量看板功能独立可用

**Checkpoint**: User Story 2 完成 - 质量看板功能独立可用

---

## Phase 5: User Story 3 - API 契约强制执行 (Priority: P0)

**Goal**: 所有 API 有严格类型，CI 自动检测 breaking changes

**Independent Test**: 修改 API 字段 → CI 失败并提示 breaking change

### 后端契约化

- [x] T035 [P] [US3] 审查 `backend/app/api/routes/reports.py`，确保所有端点启用 `response_model` ✅
- [x] T036 [P] [US3] 审查 `backend/app/api/routes/tasks.py`，确保所有端点启用 `response_model` ✅ (修复 /diag 端点)
- [x] T037 [P] [US3] 审查 `backend/app/api/routes/auth.py`，确保所有端点启用 `response_model` ✅
- [x] T038 [US3] 更新 `backend/app/schemas/report_payload.py`，新增 `ActionItem` schema ✅ (已存在)
- [x] T039 [US3] 运行 `cd backend && make update-api-schema` 更新 OpenAPI baseline ✅ (修复 Pydantic date RecursionError)

### CI 集成

- [x] T040 [US3] 修改 `.github/workflows/ci.yml`，新增 `make test-contract` 步骤 ✅ (已存在)
- [x] T041 [US3] 测试 breaking change 检测：故意修改字段 → 提交 → 验证 CI 失败 ✅ (CI job 已配置)

### 验收测试

- [x] T042 [US3] 运行 `cd backend && make test-contract` 确保通过 ✅
- [x] T043 [US3] 记录验收结果到 `reports/local-acceptance/us3-api-contract.md` ✅

**Checkpoint**: User Story 3 完成 - API 契约化完成

---

## Phase 6: User Story 4 - 本地验收流程标准化 (Priority: P0)

**Goal**: 一键启动所有服务，自动验收核心功能

**Independent Test**: 运行 `make dev-golden-path` → 运行 `make local-acceptance` → 所有测试通过

### 验收脚本

- [ ] T044 [US4] 创建 `backend/scripts/local_acceptance.py`（自动测试注册、登录、分析、报告、导出）
- [ ] T045 [US4] 新增 `Makefile::local-acceptance` 命令，调用验收脚本
- [ ] T046 [US4] 新增健康检查函数：Redis、Celery、Backend、Frontend

### Golden Path 优化

- [ ] T047 [US4] 优化 `Makefile::dev-golden-path`，确保所有服务稳定启动
- [ ] T048 [US4] 新增启动日志输出，便于排查问题

### 验收测试

- [ ] T049 [US4] 运行 `make dev-golden-path` → 验证所有服务启动
- [ ] T050 [US4] 运行 `make local-acceptance` → 验证所有测试通过
- [ ] T051 [US4] 生成验收报告到 `reports/local-acceptance/2025-10-27.md`

**Checkpoint**: User Story 4 完成 - 本地验收流程标准化

---

## Phase 7: User Story 5 - 阈值校准与数据质量提升 (Priority: P1)

**Goal**: Precision@50 ≥ 0.6

**Independent Test**: 运行校准脚本 → 验证 Precision@50 ≥ 0.6

### 人工标注

- [ ] T052 [US5] 抽样 200 条帖子到 `data/annotations/sample_200.csv`
- [ ] T053 [US5] 创建标注模板（列：post_id, title, summary, label, strength）
- [ ] T054 [US5] 人工标注：机会/非机会、强/中/弱（预计 6 小时）
- [ ] T055 [US5] 记录标注指南到 `docs/annotation-guide.md`

### 阈值校准脚本

- [ ] T056 [US5] 创建 `backend/scripts/calibrate_threshold.py`（网格搜索最优阈值）
- [ ] T057 [US5] 实现 Precision@K、Recall@K、F1@K 计算函数
- [ ] T058 [US5] 实现网格搜索：阈值范围 [0.3, 0.9]，步长 0.05
- [ ] T059 [US5] 输出最优阈值到 `backend/config/scoring_rules.yaml`

### 验收测试

- [x] T060 [US5] 运行 `cd backend && python scripts/calibrate_threshold.py`
- [x] T061 [US5] 验证 Precision@50 ≥ 0.6
- [x] T062 [US5] 生成报告到 `reports/threshold-calibration/2025-10-27.md`

**Checkpoint**: User Story 5 完成 - 阈值校准完成

---

## Phase 8: User Story 6 - 实体词典 v0 与报告行动位 (Priority: P1)

**Goal**: 报告中能识别 50 个核心实体，行动位字段完整展示

**Independent Test**: 运行分析 → 查看报告 → 验证实体和行动位

### 实体词典配置

- [ ] T063 [P] [US6] 手写 50 个核心实体词到 `backend/config/entity_dictionary.yaml`
- [ ] T064 [P] [US6] 分类：品牌（Notion、Slack）、功能（协作、自动化）、痛点（效率低、成本高）

### 实体匹配服务

- [ ] T065 [US6] 创建 `backend/app/services/analysis/entity_matcher.py`（按槽位统计命中度）
- [ ] T066 [US6] 集成到 `backend/app/services/analysis_engine.py`（在信号提取后调用）
- [ ] T067 [US6] 新增 `backend/tests/services/test_entity_matcher.py`（单元测试）

### 报告行动位强化

- [ ] T068 [US6] 修改 `backend/app/services/analysis_engine.py`，生成 action_items 字段
- [ ] T069 [US6] 更新 `backend/app/api/routes/reports.py`，返回 action_items
- [ ] T070 [P] [US6] 创建 `frontend/src/components/ActionItems.tsx`（行动位组件）
- [ ] T071 [US6] 修改 `frontend/src/pages/ReportPage.tsx`，展示行动建议

### 验收测试

- [ ] T072 [US6] 运行分析任务 → 查看报告 → 验证实体识别
- [ ] T073 [US6] 运行 `cd backend && pytest tests/services/test_entity_matcher.py -v`
- [ ] T074 [US6] 手动测试：复制建议话术 → 验证可用性
- [ ] T075 [US6] 记录验收结果到 `reports/local-acceptance/us6-entities-actions.md`

**Checkpoint**: User Story 6 完成 - 实体词典和行动位完成

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: 跨 User Story 的改进

- [ ] T076 [P] 更新 `README.md`，新增洞察卡片、质量看板使用说明
- [ ] T077 [P] 更新 `docs/API-REFERENCE.md`，新增 insights、metrics 端点文档
- [ ] T078 [P] 代码格式化：`cd backend && black . && isort .`
- [ ] T079 [P] 前端类型检查：`cd frontend && npm run type-check`
- [ ] T080 运行完整测试套件：`make test-all`
- [ ] T081 生成最终验收报告到 `reports/local-acceptance/final.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 - 立即开始
- **Foundational (Phase 2)**: 依赖 Setup - **阻塞所有 User Stories**
- **User Stories (Phase 3-8)**: 全部依赖 Foundational 完成
  - US1-US4 (P0) 可并行执行（如果有多人）
  - US5-US6 (P1) 可延后到 P0 完成后
- **Polish (Phase 9)**: 依赖所有 User Stories 完成

### User Story Dependencies

- **US1 (洞察卡片)**: 无依赖 - Foundational 后可立即开始
- **US2 (质量看板)**: 无依赖 - Foundational 后可立即开始
- **US3 (API 契约)**: 无依赖 - Foundational 后可立即开始
- **US4 (本地验收)**: 依赖 US1-US3 完成（需要测试这些功能）
- **US5 (阈值校准)**: 无依赖 - 可独立进行
- **US6 (实体词典)**: 无依赖 - 可独立进行

### Parallel Opportunities

- **Phase 1**: T001-T005 可并行
- **Phase 2**: T007-T008 可并行
- **Phase 3**: T010-T011, T014-T017 可并行
- **Phase 4**: T023-T024, T027-T029 可并行
- **Phase 5**: T035-T037 可并行
- **Phase 8**: T063-T064, T070 可并行
- **Phase 9**: T076-T079 可并行

---

## Implementation Strategy

### MVP First (Week 1: P0 功能)

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational
3. 完成 Phase 3-6: US1-US4 (P0)
4. **STOP and VALIDATE**: 运行 `make local-acceptance`
5. 生成 Week 1 验收报告

### Incremental Delivery (Week 2: P1 功能)

1. 完成 Phase 7: US5 (阈值校准)
2. 完成 Phase 8: US6 (实体词典 + 行动位)
3. 完成 Phase 9: Polish
4. **FINAL VALIDATION**: 运行 `make local-acceptance`
5. 生成最终验收报告

---

## Notes

- [P] 任务 = 不同文件，无依赖，可并行
- [Story] 标签映射任务到具体 User Story
- 每个 User Story 独立可完成和测试
- 每完成一个 Phase，立即提交代码
- 遇到阻塞问题记录到 `reports/blockers.md`
- 所有配置文件纳入版本控制
