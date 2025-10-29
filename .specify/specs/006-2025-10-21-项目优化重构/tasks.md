# Tasks: Reddit Signal Scanner 项目优化重构

**Input**: Design documents from `.specify/specs/006-2025-10-21-项目优化重构/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Organization**: Tasks are grouped by milestone (M0, M1, M2) and user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: M0 - 技术债务清理与基础设施（1 周）

**Purpose**: 清理技术债务、建立质量监控体系、上线最小可用产品

**⚠️ CRITICAL**: 这是所有后续优化的基础，必须优先完成

---

### User Story 1 - 技术债务清理与基础设施优化 (Priority: P0)

**Goal**: 清理仓库、优化 CI、建立质量看板

**Independent Test**: 仓库体积下降 ≥ 50%，CI 安装时长下降 ≥ 40%，质量看板可访问

#### Day 1-2: 仓库清理与 CI 优化

- [ ] T001 [P] [US1] 创建仓库清理脚本 `backend/scripts/cleanup_repo.sh`
  - 移除 `node_modules/` 和 `venv/` 目录
  - 清理 `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`
  - 输出清理前后的仓库体积对比

- [ ] T002 [P] [US1] 更新 `.gitignore` 文件
  - 添加 `node_modules/`, `venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`
  - 添加 `*.pyc`, `*.pyo`, `*.pyd`, `.Python`
  - 添加 `reports/failed_e2e/`（E2E 失败快照目录）

- [ ] T003 [US1] 配置 GitHub Actions 依赖缓存
  - 修改 `.github/workflows/ci.yml`
  - 添加 Python 依赖缓存（使用 `actions/cache@v3`）
  - 添加 Node.js 依赖缓存（使用 `actions/cache@v3`）
  - 验证：CI 安装时长从 5 分钟降至 3 分钟以内

- [ ] T004 [US1] 执行仓库清理并提交
  - 运行 `backend/scripts/cleanup_repo.sh`
  - 提交清理后的仓库（`git add .gitignore && git commit -m "chore: 清理依赖目录并更新 .gitignore"`）
  - 验证：`git log --stat` 不再出现 `node_modules/` 和 `venv/`

**Checkpoint**: 仓库清理完成，CI 优化完成

---

#### Day 3-4: 最小质量看板 v0

- [ ] T005 [P] [US1] 创建质量指标数据模型 `backend/app/models/metrics.py`
  - 定义 `QualityMetrics` 模型（date, collection_success_rate, deduplication_rate, processing_time_p50, processing_time_p95）
  - 添加数据库迁移脚本

- [ ] T006 [P] [US1] 创建指标采集服务 `backend/app/services/metrics/collector.py`
  - 实现 `collect_metrics()` 方法（从数据库统计采集成功率、重复率、处理耗时）
  - 实现 `save_metrics()` 方法（保存到 `reports/daily_metrics.jsonl`）
  - 添加单元测试 `backend/tests/unit/test_metrics_collector.py`

- [ ] T007 [US1] 创建质量指标 API `backend/app/api/endpoints/metrics.py`
  - 实现 `GET /api/metrics` 端点（支持 `start_date`, `end_date`, `metrics` 参数）
  - 使用严格 `response_model`（`List[QualityMetrics]`）
  - 添加集成测试 `backend/tests/integration/test_metrics_api.py`

- [ ] T008 [P] [US1] 创建质量看板前端组件 `frontend/src/components/MetricsDashboard.tsx`
  - 展示三项指标：采集成功率、重复率、处理耗时（P50/P95）
  - 支持日期范围选择
  - 使用 Recharts 绘制趋势图

- [ ] T009 [US1] 创建质量看板页面 `frontend/src/pages/MetricsPage.tsx`
  - 集成 `MetricsDashboard` 组件
  - 添加路由 `/metrics`
  - 验证：可访问 `/metrics` 页面，展示实时指标

**Checkpoint**: 质量看板 v0 上线，可查看三项核心指标

---

### User Story 2 - 洞察卡片与证据展示 (Priority: P0)

**Goal**: 上线洞察卡片 v0，支持证据折叠展开

**Independent Test**: 可浏览洞察卡片，点击展开证据段落

#### Day 5-6: 洞察卡片 v0

- [ ] T010 [P] [US2] 创建洞察卡片数据模型 `backend/app/models/insight.py`
  - 定义 `InsightCard` 模型（id, title, summary, confidence, time_window, subreddits, evidences）
  - 定义 `Evidence` 模型（id, post_url, excerpt, timestamp, subreddit, score）
  - 添加数据库迁移脚本

- [ ] T011 [P] [US2] 创建洞察卡片 API Schema `backend/app/api/schemas/insights.py`
  - 定义 `InsightCardResponse` Schema
  - 定义 `EvidenceResponse` Schema
  - 使用 Pydantic 严格类型检查

- [ ] T012 [US2] 创建洞察卡片 API `backend/app/api/endpoints/insights.py`
  - 实现 `GET /api/insights` 端点（支持 `task_id`, `entity_filter` 参数）
  - 使用严格 `response_model`（`List[InsightCardResponse]`）
  - 添加集成测试 `backend/tests/integration/test_insights_api.py`

- [ ] T013 [P] [US2] 创建洞察卡片前端组件 `frontend/src/components/InsightCard.tsx`
  - 展示标题、摘要、置信度、时间窗、子版块
  - 支持点击展开/折叠证据段落
  - 使用 Tailwind CSS 样式

- [ ] T014 [P] [US2] 创建证据面板组件 `frontend/src/components/EvidencePanel.tsx`
  - 展示证据段落列表（原帖链接、摘录、时间、子版块）
  - 点击原帖链接在新标签页打开
  - 支持分页（每页 10 条）

- [ ] T015 [US2] 创建洞察列表页面 `frontend/src/pages/InsightsPage.tsx`
  - 集成 `InsightCard` 和 `EvidencePanel` 组件
  - 添加路由 `/insights`
  - 验证：可浏览洞察卡片，点击展开证据

**Checkpoint**: 洞察卡片 v0 上线，证据链可展示

---

### User Story 3 - E2E 测试收敛与稳定性提升 (Priority: P0)

**Goal**: E2E 测试在 5 分钟内完成，失败快照自动保存

**Independent Test**: `make test-e2e` ≤ 5 分钟，失败快照保存到 `reports/failed_e2e/`

#### Day 7: E2E 收敛

- [ ] T016 [US3] 优化 E2E 测试套件 `backend/tests/e2e/test_critical_path.py`
  - 只保留 3 条关键路径：
    1. 注册 → 登录 → 输入产品描述 → 提交分析 → 查看报告
    2. 导出 CSV
    3. 错误处理（无效输入、API 失败）
  - 移除非关键路径测试

- [ ] T017 [US3] 配置 E2E 失败快照保存
  - 修改 Playwright 配置 `frontend/playwright.config.ts`
  - 设置 `screenshot: 'only-on-failure'`
  - 设置 `trace: 'retain-on-failure'`
  - 设置输出目录 `outputDir: '../reports/failed_e2e/{timestamp}/'`

- [ ] T018 [US3] 更新 Makefile E2E 命令
  - 修改 `make test-e2e` 命令
  - 添加超时限制（5 分钟）
  - 添加失败快照清理命令 `make clean-e2e-snapshots`

- [ ] T019 [US3] 验证 E2E 测试性能
  - 运行 `make test-e2e`
  - 验证：完成时间 ≤ 5 分钟
  - 验证：失败快照保存到 `reports/failed_e2e/`

**Checkpoint**: E2E 测试收敛完成，性能达标

---

### User Story 4 - CSV 导出功能 (Priority: P0)

**Goal**: 支持 CSV 导出，用户可下载分析报告

**Independent Test**: 点击"导出 CSV"按钮可下载文件，可在 Excel 中打开

#### Day 7: CSV 导出

- [ ] T020 [P] [US4] 创建 CSV 导出服务 `backend/app/services/export/csv_exporter.py`
  - 实现 `export_to_csv(task_id: UUID) -> str` 方法
  - 生成 CSV 文件（列：标题、摘要、置信度、时间窗、子版块、证据数量）
  - 添加单元测试 `backend/tests/unit/test_csv_exporter.py`

- [ ] T021 [US4] 创建导出 API `backend/app/api/endpoints/export.py`
  - 实现 `POST /api/export/csv` 端点
  - 返回 CSV 文件（`Content-Type: text/csv`）
  - 添加集成测试 `backend/tests/integration/test_export_api.py`

- [ ] T022 [P] [US4] 创建导出按钮组件 `frontend/src/components/ExportButton.tsx`
  - 支持 CSV 导出
  - 点击后下载文件（文件名：`report_{task_id}.csv`）
  - 添加加载状态和错误提示

- [ ] T023 [US4] 集成导出按钮到报告页面
  - 修改 `frontend/src/pages/ReportPage.tsx`
  - 添加"导出 CSV"按钮
  - 验证：可下载 CSV 文件，可在 Excel 中打开

**Checkpoint**: CSV 导出功能上线

---

## Phase 2: M1 - 产品闭环与质量提升（1 个月）

**Purpose**: 完善产品闭环（导出功能）、优化数据质量（去重二级化）、提升开发效率（API 契约化）、降低运营成本（缓存策略）

---

### User Story 6 - API 契约化与类型安全 (Priority: P1)

**Goal**: 后端 API 严格类型化，前端自动生成 SDK

**Independent Test**: 前端无手写类型，字段拼写错误在编译期失败

#### Week 2: API 契约化

- [ ] T024 [P] [US6] 后端启用严格 `response_model`
  - 检查所有 API 端点，确保使用 `response_model`
  - 修改 `backend/app/api/endpoints/*.py`
  - 运行 `mypy --strict` 验证类型安全

- [ ] T025 [P] [US6] 生成 OpenAPI 文档
  - 配置 FastAPI 自动生成 OpenAPI 文档
  - 访问 `/openapi.json` 验证文档完整性
  - 添加 API 文档页面（`/docs`）

- [ ] T026 [US6] 前端生成 API 类型
  - 安装 `openapi-typescript`（`npm install -D openapi-typescript`）
  - 添加脚本 `npm run generate-api-types`
  - 生成 `frontend/src/api/types.ts`

- [ ] T027 [US6] 前端使用生成的类型
  - 修改 `frontend/src/api/client.ts`
  - 使用生成的类型替换手写类型
  - 验证：TypeScript 编译通过，字段拼写错误在编译期失败

**Checkpoint**: API 契约化完成，类型安全提升

---

### User Story 7 - 成本优化与缓存策略 (Priority: P1)

**Goal**: 降低单条洞察成本 ≥ 30%，缓存命中率 ≥ 60%

**Independent Test**: 单条洞察成本下降 ≥ 30%，质量不退化

#### Week 2: 成本优化

- [ ] T028 [P] [US7] 创建 Embedding 缓存服务 `backend/app/services/cache/embedding_cache.py`
  - 实现 `get_embedding(text: str) -> List[float]` 方法（先查缓存，未命中再调用 API）
  - 使用 Redis Hash 存储（key: `embedding:{hash(text)}`, value: embedding vector）
  - 设置 TTL = 30 天
  - 添加单元测试 `backend/tests/unit/test_embedding_cache.py`

- [ ] T029 [P] [US7] 创建 LLM 调用缓存服务 `backend/app/services/cache/llm_cache.py`
  - 实现 `get_llm_response(prompt: str) -> str` 方法（先查缓存，未命中再调用 API）
  - 使用 Redis String 存储（key: `llm:{hash(prompt)}`, value: response）
  - 设置 TTL = 7 天
  - 添加单元测试 `backend/tests/unit/test_llm_cache.py`

- [ ] T030 [US7] 集成缓存到分析引擎
  - 修改 `backend/app/services/analysis_engine.py`
  - 使用 `embedding_cache.get_embedding()` 替换直接 API 调用
  - 使用 `llm_cache.get_llm_response()` 替换直接 API 调用

- [ ] T031 [US7] 添加成本跟踪
  - 修改 `backend/app/services/metrics/collector.py`
  - 添加 `cost_per_insight` 指标（API 调用次数 × 单价）
  - 验证：单条洞察成本下降 ≥ 30%

**Checkpoint**: 成本优化完成，缓存命中率 ≥ 60%

---

### User Story 8 - 导出能力完整版（PPT / Notion） (Priority: P1)

**Goal**: 支持 PPT 和 Notion 导出

**Independent Test**: 可导出 PPT 和 Notion，PPT 模板可用于评审会

#### Week 3: 导出完整版

- [ ] T032 [P] [US8] 创建 PPT 导出服务 `backend/app/services/export/ppt_exporter.py`
  - 安装 `python-pptx`（`pip install python-pptx`）
  - 实现 `export_to_ppt(task_id: UUID) -> bytes` 方法
  - 设计 PPT 模板（标题页、要点页、证据页）
  - 添加单元测试 `backend/tests/unit/test_ppt_exporter.py`

- [ ] T033 [P] [US8] 创建 Notion 导出服务 `backend/app/services/export/notion_exporter.py`
  - 安装 `notion-client`（`pip install notion-client`）
  - 实现 `export_to_notion(task_id: UUID, database_id: str) -> str` 方法
  - 配置 Notion API 集成（获取 API Token）
  - 添加单元测试 `backend/tests/unit/test_notion_exporter.py`

- [ ] T034 [US8] 扩展导出 API
  - 修改 `backend/app/api/endpoints/export.py`
  - 添加 `POST /api/export/ppt` 端点
  - 添加 `POST /api/export/notion` 端点
  - 添加集成测试

- [ ] T035 [US8] 扩展导出按钮组件
  - 修改 `frontend/src/components/ExportButton.tsx`
  - 添加"导出 PPT"和"导出到 Notion"按钮
  - 验证：可导出 PPT 和 Notion

**Checkpoint**: 导出完整版上线

---

### User Story 5 - 去重二级化（文本近似 + 主题聚合） (Priority: P1)

**Goal**: 重复率下降 ≥ 30%，主题簇纯度 ≥ 0.75

**Independent Test**: 重复率指标下降 ≥ 30%，人工抽检 50 条主题簇

#### Week 4: 去重二级化

- [ ] T036 [P] [US5] 创建 MinHash 去重服务 `backend/app/services/deduplication/minhash.py`
  - 安装 `datasketch`（`pip install datasketch`）
  - 实现 `deduplicate_minhash(posts: List[Dict]) -> List[Dict]` 方法
  - 设置相似度阈值 = 0.8
  - 添加单元测试 `backend/tests/unit/test_minhash.py`

- [ ] T037 [P] [US5] 创建 SimHash 去重服务 `backend/app/services/deduplication/simhash.py`
  - 安装 `simhash`（`pip install simhash`）
  - 实现 `deduplicate_simhash(posts: List[Dict]) -> List[Dict]` 方法
  - 设置汉明距离阈值 = 3
  - 添加单元测试 `backend/tests/unit/test_simhash.py`

- [ ] T038 [US5] 创建主题聚类服务 `backend/app/services/deduplication/clustering.py`
  - 安装 `scikit-learn`（`pip install scikit-learn`）
  - 实现 `cluster_topics(posts: List[Dict]) -> List[List[Dict]]` 方法
  - 使用 HDBSCAN 或 KMeans + 轮廓系数评估
  - 添加单元测试 `backend/tests/unit/test_clustering.py`

- [ ] T039 [US5] 集成去重二级化到分析引擎
  - 修改 `backend/app/services/analysis_engine.py`
  - 在现有去重基础上添加 MinHash/SimHash 去重
  - 再添加主题聚类
  - 验证：重复率下降 ≥ 30%

- [ ] T040 [US5] 人工抽检主题簇纯度
  - 随机抽取 50 条主题簇
  - 计算纯度（同一簇内相似度）
  - 验证：纯度 ≥ 0.75

**Checkpoint**: 去重二级化完成，数据质量提升

---

### User Story 9 - NER v1（实体抽取） (Priority: P1)

**Goal**: F1 ≥ 0.75，实体在卡片中高亮渲染

**Independent Test**: 标注集上 F1 ≥ 0.75，支持按实体筛选

#### Week 5: NER v1

- [ ] T041 [P] [US9] 创建实体数据模型 `backend/app/models/entity.py`
  - 定义 `Entity` 模型（id, type, value, confidence, source_post_id）
  - 定义 `EntityType` 枚举（品牌、功能、痛点、价格、平台、场景）
  - 添加数据库迁移脚本

- [ ] T042 [P] [US9] 创建 NER 规则/词典 `backend/app/services/ner/rules.py`
  - 定义品牌词典（Notion, Evernote, Trello, etc.）
  - 定义功能词典（note-taking, task management, collaboration, etc.）
  - 定义痛点模式（正则表达式）
  - 定义价格模式（正则表达式）

- [ ] T043 [US9] 创建 NER 实体抽取服务 `backend/app/services/ner/extractor.py`
  - 实现 `extract_entities(text: str) -> List[Entity]` 方法
  - 使用规则/词典方法
  - 添加单元测试 `backend/tests/unit/test_ner_extractor.py`

- [ ] T044 [US9] 准备标注集并评估 F1
  - 准备 200 条标注数据（使用合成数据 + 少量人工标注）
  - 评估 F1 分数
  - 验证：F1 ≥ 0.75

- [ ] T045 [US9] 集成 NER 到分析引擎
  - 修改 `backend/app/services/analysis_engine.py`
  - 在信号提取后添加 NER 实体抽取
  - 保存实体到数据库

- [ ] T046 [P] [US9] 前端实体高亮渲染
  - 修改 `frontend/src/components/EvidencePanel.tsx`
  - 实体以高亮标签渲染（如 `<span class="entity-brand">Notion</span>`）
  - 添加实体筛选器

**Checkpoint**: NER v1 上线，实体可抽取和筛选

---

### User Story 10 - 质量看板 v1（可配置） (Priority: P1)

**Goal**: 支持可配置指标和时间窗，每日报表自动产出

**Independent Test**: 可选择指标和时间窗，每日报表自动生成

#### Week 4-5: 质量看板 v1

- [ ] T047 [P] [US10] 扩展质量指标数据模型
  - 修改 `backend/app/models/metrics.py`
  - 添加字段：language_distribution, topic_drift, entity_recall, cost_per_insight

- [ ] T048 [P] [US10] 扩展指标采集服务
  - 修改 `backend/app/services/metrics/collector.py`
  - 实现语言占比统计
  - 实现主题漂移计算（JS 散度）
  - 实现实体召回率计算

- [ ] T049 [US10] 创建报表生成服务 `backend/app/services/metrics/reporter.py`
  - 实现 `generate_daily_report()` 方法（保存到 `reports/daily_metrics.jsonl`）
  - 实现 `generate_weekly_summary()` 方法（保存到 `reports/weekly_summary.md`）
  - 配置 Celery Beat 定时任务（每天凌晨执行）

- [ ] T050 [P] [US10] 扩展质量看板前端组件
  - 修改 `frontend/src/components/MetricsDashboard.tsx`
  - 添加指标选择器（语言占比、主题漂移、实体召回、成本）
  - 添加时间窗选择器（日/周/月）
  - 添加导出按钮（PNG/SVG）

- [ ] T051 [US10] 验证质量看板 v1
  - 访问 `/metrics` 页面
  - 选择不同指标和时间窗
  - 验证：2 秒内完成渲染
  - 验证：每日报表自动生成

**Checkpoint**: 质量看板 v1 上线

---

## Phase 3: M2 - 高级功能与优化（1 季度）

**Purpose**: 趋势分析、竞品雷达、主动学习闭环

---

### User Story 11 - 趋势分析 v1 (Priority: P2)

**Goal**: 识别新兴主题，生成强度曲线

**Independent Test**: 趋势卡片包含主题名、增长率、峰值时间、代表证据

#### Month 2: 趋势分析

- [ ] T052 [P] [US11] 调研时序聚类算法
  - 调研 EARS（Early Aberration Reporting System）
  - 调研阈值 + 滑窗方法
  - 选择最适合的算法

- [ ] T053 [P] [US11] 创建趋势分析服务 `backend/app/services/trend_analysis.py`
  - 实现 `detect_emerging_topics(posts: List[Dict]) -> List[Trend]` 方法
  - 计算增长率、峰值时间
  - 添加单元测试

- [ ] T054 [US11] 创建趋势卡片 API
  - 实现 `GET /api/trends` 端点
  - 返回趋势卡片列表

- [ ] T055 [P] [US11] 创建趋势卡片前端组件
  - 创建 `frontend/src/components/TrendCard.tsx`
  - 展示主题名、增长率、峰值时间、代表证据
  - 绘制强度曲线（使用 Recharts）

- [ ] T056 [US11] 验证趋势分析
  - 识别新兴主题（增长率 > 50%）
  - 与历史对比可视化

**Checkpoint**: 趋势分析 v1 上线

---

### User Story 12 - 竞品雷达 (Priority: P2)

**Goal**: 生成竞品雷达图，支持多社区对比

**Independent Test**: 任选四品牌生成雷达图，可导出到 PPT

#### Month 3: 竞品雷达

- [ ] T057 [P] [US12] 创建竞品雷达服务 `backend/app/services/competitor_radar.py`
  - 实现 `generate_radar(brands: List[str]) -> Dict` 方法
  - 围绕品牌/功能/口碑/价格生成数据
  - 添加单元测试

- [ ] T058 [US12] 创建竞品雷达 API
  - 实现 `GET /api/competitor-radar` 端点
  - 支持多社区对比

- [ ] T059 [P] [US12] 创建竞品雷达前端组件
  - 创建 `frontend/src/components/CompetitorRadar.tsx`
  - 使用 Recharts 绘制雷达图
  - 支持品牌选择

- [ ] T060 [US12] 验证竞品雷达
  - 任选四品牌生成雷达图
  - 导出到 PPT（图表可编辑）

**Checkpoint**: 竞品雷达上线

---

## Dependencies & Execution Order

### Phase Dependencies

- **M0 (Phase 1)**: No dependencies - can start immediately
- **M1 (Phase 2)**: Depends on M0 completion
- **M2 (Phase 3)**: Depends on M1 completion (especially NER v1)

### User Story Dependencies

- **US1 (技术债务清理)**: No dependencies - MUST start first
- **US2 (洞察卡片)**: Depends on US1 (质量看板)
- **US3 (E2E 收敛)**: Can run in parallel with US1-US2
- **US4 (CSV 导出)**: Depends on US2 (洞察卡片 API)
- **US5 (去重二级化)**: Depends on M0 completion
- **US6 (API 契约化)**: Can run in parallel with US7
- **US7 (成本优化)**: Can run in parallel with US6
- **US8 (导出完整版)**: Depends on US4 (CSV 导出)
- **US9 (NER v1)**: Depends on US5 (去重二级化)
- **US10 (质量看板 v1)**: Depends on US1 (质量看板 v0)
- **US11 (趋势分析)**: Depends on US9 (NER v1)
- **US12 (竞品雷达)**: Depends on US9 (NER v1)

### Parallel Opportunities

- **M0**: T001-T002 (仓库清理), T005-T006 (指标采集), T008 (前端组件), T010-T011 (数据模型), T013-T014 (前端组件), T020 (CSV 导出), T022 (导出按钮)
- **M1**: T024-T025 (API 契约), T028-T029 (缓存服务), T032-T033 (导出服务), T036-T037 (去重服务), T041-T042 (NER 规则), T046 (前端渲染), T047-T048 (指标扩展), T050 (前端组件)
- **M2**: T052-T053 (趋势分析), T055 (前端组件), T057 (竞品雷达), T059 (前端组件)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

