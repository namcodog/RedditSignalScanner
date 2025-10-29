# Feature Specification: MVP 产品闭环补全

**Feature Branch**: `007-mvp-product-loop`  
**Created**: 2025-10-27  
**Status**: Active  
**Input**: 基于当前项目状态分析，优先完成"让用户用起来"的核心功能

## 背景与目标

### 当前状态
- ✅ 核心功能已实现：用户注册、产品分析、报告生成、SSE 实时通信
- ✅ 数据采集系统稳定：200 个社区池、18,260 条帖子、90% 缓存命中率
- ✅ 基础优化已完成：动态调度、补抓兜底、MinHash 去重、PDF 导出
- ⚠️ **产品闭环不完整**：用户看不到结构化洞察、无法验证证据、运营无法监控质量

### 优化目标
**把"从 Reddit 抓信号 → 去噪与结构化 → 生成可交易的洞察"做成本地稳固可用的产品闭环。**

### 版本规划
- **Week 1（本周）**: 洞察卡片 API + 前端、质量看板前端、本地验收
- **Week 2（下周）**: API 契约化、阈值校准、实体词典 v0、报告行动位

---

## User Scenarios & Testing

### User Story 1 - 洞察卡片展示与证据验证 (Priority: P0) ⚠️ FUNCTIONAL COMPLETE

**状态**: ⚠️ 功能完成，测试受阻（2025-10-28）
**实施者**: 其他团队成员
**阻塞问题**: `reports/blockers/phase3-recursion-error.md`

**描述**: 作为产品经理，我需要看到结构化的洞察卡片列表，每个洞察都有清晰的证据链，可以点击展开查看原帖，验证洞察的真实性。

**Why this priority**:
- 这是产品的核心价值展示，没有它用户只能看到一堆文字
- 没有证据链的洞察缺乏可信度，用户无法验证
- 这是 PMF（Product-Market Fit）验证的关键功能

**Independent Test**:
- 可以浏览洞察卡片列表（标题、摘要、置信度）
- 点击卡片可展开查看证据段落
- 每条证据都有原帖链接和时间戳
- 可在新标签页打开 Reddit 原帖

**Acceptance Scenarios**:

1. **Given** 分析任务已完成, **When** 访问报告页面, **Then** 展示洞察卡片列表（标题、摘要、置信度、时间窗）
2. **Given** 洞察卡片列表, **When** 点击某个卡片, **Then** 展开显示证据段落列表（原帖链接、摘录、时间、子版块）
3. **Given** 证据段落, **When** 点击原帖链接, **Then** 在新标签页打开 Reddit 原帖
4. **Given** 后端 API, **When** 调用 `GET /api/insights/{task_id}`, **Then** 返回固定 schema 的 JSON 数据

**实施成果**:
- 后端：`backend/app/schemas/insight.py`（Pydantic schema）
- 后端：`backend/app/services/insight_service.py`（Service 层封装）
- 后端：`backend/app/api/routes/insights.py`（GET /api/insights/{task_id}, GET /api/insights/card/{insight_id}）
- 前端：`frontend/src/types/insight.types.ts`（TypeScript 类型定义）
- 前端：`frontend/src/api/insights.ts`（API 客户端）
- 前端：`frontend/src/components/InsightCard.tsx`（洞察卡片组件）
- 前端：`frontend/src/components/EvidenceList.tsx`（证据列表组件）

**已知问题**:
- ⚠️ 单元测试因 SQLAlchemy 双向关系导致 RecursionError，已标记为 skip
- ✅ 功能实现完整，契约正确
- ⏳ 需要手动验收测试验证功能（见 blocker 文档）

---

### User Story 2 - 质量看板实时监控 (Priority: P0) ✅ COMPLETED

**状态**: ✅ 已完成（2025-10-27）
**实施者**: AI Assistant
**验收报告**: `reports/local-acceptance/us2-dashboard.md`

**描述**: 作为运营人员，我需要一个质量看板页面，可以实时查看缓存命中率、重复率、处理耗时等关键指标，确保系统健康运行。

**Why this priority**:
- 运营需要知道系统是否健康，否则是"盲飞"
- 数据质量直接影响洞察质量，必须可监控
- 后端指标计算已完成，只需前端展示

**Independent Test**:
- ✅ 可以访问 `/dashboard` 页面
- ✅ 展示缓存命中率、重复率、Precision@50 趋势图
- ✅ 可以选择日期范围查看历史数据（7/14/30 天）

**Acceptance Scenarios**:

1. ✅ **Given** 系统正在运行, **When** 访问 `/dashboard` 页面, **Then** 展示实时指标（缓存命中率、重复率、Precision@50、有效帖子数）
2. ✅ **Given** 质量看板页面, **When** 选择日期范围, **Then** 5 秒内刷新并展示趋势图
3. ✅ **Given** 后端 API, **When** 调用 `GET /api/metrics/daily`, **Then** 返回每日指标数据
4. ✅ **Given** 质量看板, **When** 指标异常（如缓存命中率 < 60%）, **Then** 高亮显示警告

**实施成果**:
- 后端：`backend/app/schemas/metrics.py`（Pydantic schema）
- 后端：`backend/app/services/metrics_service.py`（复用 red_line_checker 指标）
- 后端：`backend/app/api/routes/metrics.py`（GET /api/metrics/daily）
- 后端：`backend/tests/api/test_metrics.py`（3 个测试全部通过）
- 前端：`frontend/src/types/metrics.ts`（TypeScript 类型定义）
- 前端：`frontend/src/api/metrics.ts`（API 客户端）
- 前端：`frontend/src/components/MetricsChart.tsx`（recharts 图表组件）
- 前端：`frontend/src/pages/DashboardPage.tsx`（看板页面）
- 前端：`frontend/src/router/index.tsx`（新增 /dashboard 路由）

**技术亮点**:
- 使用 `response_model` 强制类型验证（符合 FastAPI 最佳实践）
- Pydantic schema 使用 `json_schema_extra` 提供示例数据
- 前端使用 recharts 专业图表库，自定义 Tooltip 高亮异常值
- 完整的 TypeScript 类型安全
- Service 层单元测试覆盖核心逻辑

---

### User Story 3 - API 契约强制执行 (Priority: P0) ✅ COMPLETE

**描述**: 作为前端工程师，我需要后端 API 有严格的类型定义，所有端点都启用 `response_model`，CI 中自动检测 breaking changes，避免前后端不一致导致的返工。

**Why this priority**:
- 当前部分端点缺少严格类型，容易出错
- API 变更时缺少自动检测，导致前端运行时报错
- 这是技术债务清理的关键，阻塞后续开发

**Independent Test**:
- 所有 API 端点都有明确的 `response_model`
- CI 中运行 `make test-contract` 自动检测 breaking changes
- 前端可以基于 OpenAPI schema 生成类型

**Acceptance Scenarios**:

1. ✅ **Given** 后端 API, **When** 启用严格 `response_model`, **Then** 所有端点都有明确的响应类型
2. ✅ **Given** 后端服务, **When** 访问 `/api/openapi.json`, **Then** 返回完整的 OpenAPI 3.0 文档
3. ✅ **Given** CI 流程, **When** 提交代码, **Then** 自动运行 `make test-contract` 检测 breaking changes
4. ✅ **Given** API 变更, **When** 修改响应字段, **Then** CI 失败并提示 breaking change

**验收报告**: `reports/local-acceptance/us3-api-contract.md`

---

### User Story 4 - 本地验收流程标准化 (Priority: P0)

**描述**: 作为开发者，我需要一个标准化的本地验收流程，确保所有服务（Redis、Celery、Backend、Frontend）能稳固启动，核心功能能正常运行。

**Why this priority**: 
- 当前缺少统一的验收流程，每次启动都要手动检查
- 新功能上线前必须确保本地环境稳定
- 这是"本地稳固正常跑起来"的基础

**Independent Test**: 
- 运行 `make dev-golden-path` 一键启动所有服务
- 运行 `make local-acceptance` 自动验收核心功能
- 所有验收测试通过，输出清晰的成功/失败报告

**Acceptance Scenarios**:

1. **Given** 本地环境, **When** 运行 `make dev-golden-path`, **Then** Redis、Celery、Backend、Frontend 全部启动成功
2. **Given** 服务已启动, **When** 运行 `make local-acceptance`, **Then** 自动测试注册、登录、分析、报告、导出功能
3. **Given** 验收测试, **When** 所有测试通过, **Then** 输出 `✅ 本地验收通过` 并生成报告到 `reports/local-acceptance/`
4. **Given** 验收测试, **When** 某个测试失败, **Then** 输出详细错误信息并保存快照

---

### User Story 5 - 阈值校准与数据质量提升 (Priority: P1)

**描述**: 作为数据科学家，我需要抽样 200 条帖子进行人工标注，网格搜索最优阈值，优化 Precision@50，确保洞察质量可用。

**Why this priority**: 
- 当前阈值未经校准，洞察质量不稳定
- 人工标注是数据质量优化的基础
- 这是从"能用"到"好用"的关键

**Independent Test**: 
- 完成 200 条帖子的人工标注（机会/非机会、强/中/弱）
- 网格搜索最优阈值，Precision@50 ≥ 0.6
- 阈值写入配置并记录到 `reports/threshold-calibration/`

**Acceptance Scenarios**:

1. **Given** 原始帖子数据, **When** 抽样 200 条, **Then** 生成标注模板到 `data/annotations/sample_200.csv`
2. **Given** 标注完成, **When** 运行 `python scripts/calibrate_threshold.py`, **Then** 网格搜索最优阈值并输出 Precision@50
3. **Given** 最优阈值, **When** 更新配置文件, **Then** 阈值写入 `config/scoring_rules.yaml` 并记录到 `reports/threshold-calibration/`
4. **Given** 新阈值, **When** 重新运行分析, **Then** Precision@50 ≥ 0.6

---

### User Story 6 - 实体词典 v0 与报告行动位 (Priority: P1)

**描述**: 作为产品经理，我需要报告中能识别关键实体（品牌、功能、痛点），并在报告中新增行动位（问题定义、建议动作、置信度、优先级），方便直接执行。

**Why this priority**: 
- 实体识别可以提升洞察的结构化程度
- 行动位让报告从"信息展示"变成"可执行建议"
- 这是产品差异化的关键

**Independent Test**: 
- 手写 50 个核心实体词（品牌、功能、痛点）
- 报告中能看到"提到了 Notion、Slack"
- 报告新增行动位字段（问题定义、建议动作、置信度、优先级）

**Acceptance Scenarios**:

1. **Given** 实体词典, **When** 手写 50 个核心词, **Then** 保存到 `config/entity_dictionary.yaml`
2. **Given** 分析引擎, **When** 集成实体词典, **Then** 在评分器中按槽位统计命中度
3. **Given** 报告结构, **When** 新增行动位字段, **Then** 包含问题定义、建议动作、置信度、优先级
4. **Given** 前端渲染, **When** 查看报告, **Then** 高亮显示实体和行动建议

---

### Edge Cases

- **数据不足**: 如果某个任务的帖子数 < 100，如何处理？→ 显示警告并建议扩大关键词范围
- **API 限流**: 如果 Reddit API 返回 429，如何重试？→ 已有降级逻辑，记录日志
- **缓存失效**: 如果 Redis 宕机，如何降级到数据库？→ 已有降级逻辑，需补充监控
- **洞察为空**: 如果分析结果没有洞察，如何展示？→ 显示"未发现明显机会，建议调整关键词"
- **证据链断裂**: 如果原帖被删除，如何处理？→ 显示"原帖已删除"并保留摘录

---

## Requirements

### Functional Requirements

- **FR-001**: 系统 MUST 提供 `GET /api/insights/{task_id}` 端点，返回结构化洞察列表
- **FR-002**: 洞察卡片 MUST 包含标题、摘要、置信度、时间窗、证据链
- **FR-003**: 证据段落 MUST 包含原帖链接、摘录、时间、子版块
- **FR-004**: 系统 MUST 提供 `GET /api/metrics/daily` 端点，返回每日质量指标
- **FR-005**: 质量看板 MUST 展示缓存命中率、重复率、处理耗时（P50/P95）
- **FR-006**: 所有 API 端点 MUST 启用严格 `response_model`
- **FR-007**: CI MUST 自动运行 `make test-contract` 检测 breaking changes
- **FR-008**: 系统 MUST 提供 `make local-acceptance` 命令，自动验收核心功能
- **FR-009**: 报告结构 MUST 新增行动位字段（问题定义、建议动作、置信度、优先级）
- **FR-010**: 分析引擎 MUST 集成实体词典，识别品牌、功能、痛点

### Key Entities

- **InsightCard**: 洞察卡片（标题、摘要、置信度、时间窗、证据链）
- **Evidence**: 证据段落（原帖链接、摘录、时间、子版块）
- **DailyMetrics**: 每日质量指标（缓存命中率、重复率、处理耗时）
- **ActionItem**: 行动位（问题定义、建议动作、置信度、优先级）
- **EntityDictionary**: 实体词典（品牌、功能、痛点）

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: 用户能在报告页面看到洞察卡片列表，点击展开查看证据（2 分钟内完成）
- **SC-002**: 运营能在质量看板查看实时指标，5 秒内刷新趋势图
- **SC-003**: CI 中自动检测 API breaking changes，失败时提示详细错误
- **SC-004**: 本地验收测试通过率 100%，所有核心功能正常运行
- **SC-005**: Precision@50 ≥ 0.6，洞察质量达到可用标准
- **SC-006**: 报告中能识别 50 个核心实体，行动位字段完整展示

