# Feature Specification: Reddit Signal Scanner 项目优化重构

**Feature Branch**: `006-project-optimization-refactor`  
**Created**: 2025-10-21  
**Status**: Draft  
**Input**: 基于项目工程规划文档和技术评估建议的综合优化方案

## 背景与目标

### 当前状态
- ✅ 核心功能已实现：用户注册、产品分析、报告生成、SSE 实时通信
- ✅ 数据采集系统运行正常：200 个社区池、18,260 条帖子、90% 缓存命中率
- ⚠️ 存在技术债务：依赖目录入库、缺少质量看板、去重算法待优化
- ⚠️ 产品闭环不完整：缺少导出功能、NER 实体抽取、趋势分析

### 优化目标
**把"从 Reddit 抓信号 → 去噪与结构化 → 生成可交易的洞察"做成稳定流水线，并形成可交付的洞察卡片与导出能力。**

### 版本规划
- **M0（1 周）**: 清理技术债务、上线最小质量看板、洞察卡片 v0
- **M1（1 个月）**: NER v1、导出能力、API 契约化、成本优化
- **M2（1 季度）**: 趋势分析、竞品雷达、主动学习闭环

---

## User Scenarios & Testing

### User Story 1 - 技术债务清理与基础设施优化 (Priority: P0)

**描述**: 作为开发团队，我需要清理仓库中的技术债务，建立基础的质量监控体系，确保项目可持续发展。

**Why this priority**: 
- 依赖目录入库导致仓库体积膨胀（严重影响 CI/CD 效率）
- 缺少质量看板导致"盲飞"（无法量化数据质量和系统性能）
- 这些是阻塞后续优化的基础设施问题

**Independent Test**: 
- 仓库体积下降 ≥ 50%
- CI 安装时长下降 ≥ 40%
- 质量看板可访问并展示实时指标

**Acceptance Scenarios**:

1. **Given** 仓库包含 `node_modules/` 和 `venv/` 目录, **When** 执行清理脚本, **Then** 这些目录被移除且 `.gitignore` 已更新
2. **Given** CI 流程需要安装依赖, **When** 使用依赖缓存, **Then** 安装时长从 5 分钟降至 3 分钟以内
3. **Given** 系统正在运行, **When** 访问 `/metrics` 端点, **Then** 返回采集成功率、重复率、处理耗时（P50/P95）
4. **Given** 前端质量看板页面, **When** 选择日期范围, **Then** 5 分钟内指标刷新并展示趋势图

---

### User Story 2 - 洞察卡片与证据展示 (Priority: P0)

**描述**: 作为产品经理，我需要看到结构化的洞察卡片，每个洞察都有清晰的证据链，可以点击展开查看原帖。

**Why this priority**: 
- 这是产品的核心价值展示
- 没有证据链的洞察缺乏可信度
- 用户需要能够验证洞察的真实性

**Independent Test**: 
- 可以浏览洞察卡片列表
- 点击卡片可展开查看证据段落
- 每条证据都有原帖链接和时间戳

**Acceptance Scenarios**:

1. **Given** 分析任务已完成, **When** 访问报告页面, **Then** 展示洞察卡片列表（标题、摘要、置信度、时间窗）
2. **Given** 洞察卡片列表, **When** 点击某个卡片, **Then** 展开显示证据段落列表（原帖链接、摘录、时间、子版块）
3. **Given** 证据段落, **When** 点击原帖链接, **Then** 在新标签页打开 Reddit 原帖
4. **Given** 后端 API, **When** 调用 `GET /insights`, **Then** 返回固定 schema 的 JSON 数据

---

### User Story 3 - E2E 测试收敛与稳定性提升 (Priority: P0)

**描述**: 作为 QA 工程师，我需要一个快速、稳定的 E2E 测试套件，只覆盖关键路径，失败时自动保存快照。

**Why this priority**: 
- 当前 E2E 测试过多过慢（超过 10 分钟）
- 测试失败时缺少快照，难以排查
- 影响开发效率和 CI/CD 流程

**Independent Test**: 
- `make test-e2e` 在 5 分钟内完成
- 失败快照自动保存到 `reports/failed_e2e/`
- 只保留 3 条关键路径测试

**Acceptance Scenarios**:

1. **Given** E2E 测试套件, **When** 执行 `make test-e2e`, **Then** 在 5 分钟内完成所有测试
2. **Given** E2E 测试失败, **When** 测试结束, **Then** 失败快照自动保存到 `reports/failed_e2e/{timestamp}/`
3. **Given** E2E 测试套件, **When** 查看测试列表, **Then** 只包含 3 条关键路径：注册→分析→报告、导出、错误处理

---

### User Story 4 - CSV 导出功能 (Priority: P0)

**描述**: 作为产品经理，我需要能够将分析报告导出为 CSV 文件，方便在 Excel 中进一步分析。

**Why this priority**: 
- 用户能导出数据才能真正使用产品（产品闭环的关键）
- CSV 是最简单、最通用的导出格式
- 这是 PMF（Product-Market Fit）的关键功能

**Independent Test**: 
- 点击"导出 CSV"按钮可下载文件
- CSV 文件包含所有洞察字段
- 可在 Excel 中正常打开

**Acceptance Scenarios**:

1. **Given** 报告页面, **When** 点击"导出 CSV"按钮, **Then** 下载 `report_{task_id}.csv` 文件
2. **Given** CSV 文件, **When** 在 Excel 中打开, **Then** 包含列：标题、摘要、置信度、时间窗、子版块、证据数量
3. **Given** CSV 文件, **When** 查看内容, **Then** 所有字段与前端卡片一一对应

---

### User Story 5 - 去重二级化（文本近似 + 主题聚合） (Priority: P1)

**描述**: 作为数据工程师，我需要优化去重算法，使用 MinHash/SimHash 进行文本近似匹配，再用主题聚类进一步去重。

**Why this priority**: 
- 当前去重算法只基于精确匹配，重复率仍然较高
- 用户看到重复内容会降低信任度
- 这是数据质量优化的关键

**Independent Test**: 
- 重复率指标下降 ≥ 30%
- 人工抽检 50 条主题簇，纯度 ≥ 0.75

**Acceptance Scenarios**:

1. **Given** 原始帖子数据, **When** 执行去重流程, **Then** 重复率从当前值下降 ≥ 30%
2. **Given** 去重后的主题簇, **When** 人工抽检 50 条, **Then** 纯度（同一簇内相似度）≥ 0.75
3. **Given** 质量看板, **When** 查看重复率指标, **Then** 显示去重前后对比

---

### User Story 6 - API 契约化与类型安全 (Priority: P1)

**描述**: 作为前端工程师，我需要后端 API 有严格的类型定义，前端可以自动生成 SDK，避免手写接口类型。

**Why this priority**: 
- 手写接口类型容易出错（字段拼写错误、类型不匹配）
- API 契约化可以在编译期发现错误
- 提升开发效率和代码质量

**Independent Test**: 
- 后端启用严格 `response_model`
- 生成 OpenAPI 文档
- 前端使用 `openapi-typescript` 生成 SDK

**Acceptance Scenarios**:

1. **Given** 后端 API, **When** 启用严格 `response_model`, **Then** 所有端点都有明确的响应类型
2. **Given** 后端服务, **When** 访问 `/openapi.json`, **Then** 返回完整的 OpenAPI 3.0 文档
3. **Given** OpenAPI 文档, **When** 运行 `npm run generate-api-types`, **Then** 生成 `frontend/src/api/types.ts`
4. **Given** 前端代码, **When** 使用错误的字段名, **Then** TypeScript 编译失败并提示错误

---

### User Story 7 - 成本优化与缓存策略 (Priority: P1)

**描述**: 作为技术负责人，我需要优化模型调用成本，引入 Embedding 和生成式调用缓存，降低单条洞察成本 ≥ 30%。

**Why this priority**: 
- 如果等到季度末才优化成本，可能已经烧了不少钱
- 缓存策略可以显著降低 API 调用次数
- 成本控制是创业团队的生存关键

**Independent Test**: 
- 单条洞察成本下降 ≥ 30%
- 缓存命中率 ≥ 60%
- 质量不退化（F1 分数保持或提升）

**Acceptance Scenarios**:

1. **Given** 模型调用, **When** 引入 Embedding 缓存, **Then** 重复请求命中率 ≥ 60%
2. **Given** 生成式调用, **When** 引入响应缓存, **Then** 相同输入直接返回缓存结果
3. **Given** 质量看板, **When** 查看成本指标, **Then** 单条洞察成本下降 ≥ 30%
4. **Given** 分析结果, **When** 对比缓存前后, **Then** F1 分数保持或提升（质量不退化）

---

### User Story 8 - 导出能力完整版（PPT / Notion） (Priority: P1)

**描述**: 作为产品经理，我需要能够将分析报告导出为 PPT 和 Notion，方便在评审会和团队协作中使用。

**Why this priority**: 
- PPT 导出可以直接用于评审会
- Notion 导出可以方便团队协作
- 这是产品闭环的重要补充

**Independent Test**: 
- 点击"导出 PPT"按钮可下载 PPTX 文件
- 点击"导出到 Notion"按钮可同步到 Notion 数据库
- PPT 模板可被评审会直接使用

**Acceptance Scenarios**:

1. **Given** 报告页面, **When** 点击"导出 PPT"按钮, **Then** 下载 `report_{task_id}.pptx` 文件
2. **Given** PPT 文件, **When** 在 PowerPoint 中打开, **Then** 包含标题页、要点页、证据页
3. **Given** 报告页面, **When** 点击"导出到 Notion"按钮, **Then** 数据同步到 Notion 数据库
4. **Given** Notion 数据库, **When** 查看内容, **Then** 所有字段与前端卡片一一对应

---

### User Story 9 - NER v1（实体抽取） (Priority: P1)

**描述**: 作为数据科学家，我需要从帖子中抽取实体（品牌、功能、痛点、价格、平台、场景），并在卡片中以高亮标签渲染。

**Why this priority**: 
- 实体抽取可以提升洞察的结构化程度
- 用户可以按实体筛选洞察
- 这是后续竞品雷达、趋势分析的基础

**Independent Test**: 
- 标注集上 F1 ≥ 0.75
- 实体在卡片中以高亮标签渲染
- 支持按实体筛选

**Acceptance Scenarios**:

1. **Given** 帖子文本, **When** 执行 NER 抽取, **Then** 识别出品牌、功能、痛点、价格、平台、场景
2. **Given** 标注集（200 条）, **When** 评估 NER 模型, **Then** F1 分数 ≥ 0.75
3. **Given** 洞察卡片, **When** 查看证据段落, **Then** 实体以高亮标签渲染（如 `<品牌>Notion</品牌>`）
4. **Given** 洞察列表, **When** 选择实体筛选器, **Then** 只显示包含该实体的洞察

---

### User Story 10 - 质量看板 v1（可配置） (Priority: P1)

**描述**: 作为运营人员，我需要一个可配置的质量看板，可以选择指标和时间窗，查看语言占比、主题漂移、实体召回、成本等指标。

**Why this priority**: 
- v0 只有基础指标，需要扩展
- 可配置性可以满足不同角色的需求
- 每日报表自动产出可以提升运营效率

**Independent Test**: 
- 前端可选择指标和时间窗
- 每日报表自动产出并存档
- 指标包含语言占比、主题漂移、实体召回、成本

**Acceptance Scenarios**:

1. **Given** 质量看板页面, **When** 选择指标（语言占比、主题漂移、实体召回、成本）, **Then** 展示对应的趋势图
2. **Given** 质量看板页面, **When** 选择时间窗（日/周/月）, **Then** 2 秒内完成渲染
3. **Given** 系统运行, **When** 每天凌晨, **Then** 自动生成 `reports/daily_metrics.jsonl` 和 `reports/weekly_summary.md`
4. **Given** 质量看板, **When** 点击"导出"按钮, **Then** 下载 PNG/SVG 格式的图表

---

### User Story 11 - 趋势分析 v1 (Priority: P2)

**描述**: 作为产品经理，我需要看到新兴主题的趋势分析，包括主题名、增长率、峰值时间、代表证据。

**Why this priority**: 
- 趋势分析可以帮助发现新兴机会
- 这是高级功能，不阻塞主路径
- 需要时序聚类和突发检测算法

**Independent Test**: 
- 趋势卡片包含主题名、增长率、峰值时间、代表证据
- 与历史对比可视化

**Acceptance Scenarios**:

1. **Given** 时序数据, **When** 执行趋势分析, **Then** 识别出新兴主题（增长率 > 50%）
2. **Given** 趋势卡片, **When** 查看内容, **Then** 包含主题名、增长率、峰值时间、代表证据
3. **Given** 趋势图表, **When** 查看可视化, **Then** 展示强度曲线和历史对比

---

### User Story 12 - 竞品雷达 (Priority: P2)

**描述**: 作为产品经理，我需要看到竞品雷达图，围绕品牌/功能/口碑/价格生成可视化，支持多社区对比。

**Why this priority**: 
- 竞品分析是产品决策的重要依据
- 雷达图可以直观展示竞品优劣势
- 依赖 NER v1 的实体抽取

**Independent Test**: 
- 任选四品牌生成雷达图
- 导出到 PPT 的图表可编辑

**Acceptance Scenarios**:

1. **Given** 竞品数据, **When** 选择四个品牌, **Then** 生成雷达图（品牌/功能/口碑/价格）
2. **Given** 雷达图, **When** 导出到 PPT, **Then** 图表可编辑（非图片）
3. **Given** 雷达图, **When** 选择不同社区, **Then** 支持多社区对比

---

### Edge Cases

- **数据不足**: 如果某个社区帖子数 < 10，如何处理？
- **API 限流**: 如果 Reddit API 返回 429，如何重试？
- **缓存失效**: 如果 Redis 宕机，如何降级到数据库？
- **导出失败**: 如果 PPT 生成失败，如何提示用户？
- **NER 误标**: 如果实体识别错误率 > 25%，如何处理？

---

## Requirements

### Functional Requirements

#### P0 功能需求

- **FR-001**: 系统必须移除 `node_modules/` 和 `venv/` 目录，并更新 `.gitignore`
- **FR-002**: 系统必须提供 `/metrics` 端点，返回采集成功率、重复率、处理耗时（P50/P95）
- **FR-003**: 系统必须提供洞察卡片 API（`GET /insights`），返回固定 schema
- **FR-004**: 前端必须支持洞察卡片展示，点击可展开证据段落
- **FR-005**: 系统必须支持 CSV 导出功能
- **FR-006**: E2E 测试必须在 5 分钟内完成，失败快照自动保存

#### P1 功能需求

- **FR-007**: 系统必须实现去重二级化（MinHash/SimHash + 主题聚类）
- **FR-008**: 后端必须启用严格 `response_model`，生成 OpenAPI 文档
- **FR-009**: 前端必须使用 `openapi-typescript` 生成 SDK
- **FR-010**: 系统必须引入 Embedding 和生成式调用缓存
- **FR-011**: 系统必须支持 PPT 和 Notion 导出
- **FR-012**: 系统必须实现 NER v1（品牌、功能、痛点、价格、平台、场景）
- **FR-013**: 质量看板必须支持可配置指标和时间窗

#### P2 功能需求

- **FR-014**: 系统必须实现趋势分析 v1（新兴主题 + 强度曲线）
- **FR-015**: 系统必须实现竞品雷达（品牌/功能/口碑/价格）

### Key Entities

- **洞察卡片（Insight Card）**: 标题、摘要、置信度、时间窗、子版块、证据段落列表
- **证据段落（Evidence）**: 原帖链接、摘录、时间、子版块
- **质量指标（Metrics）**: 采集成功率、重复率、处理耗时、语言占比、主题漂移、实体召回、成本
- **实体（Entity）**: 品牌、功能、痛点、价格、平台、场景
- **趋势（Trend）**: 主题名、增长率、峰值时间、代表证据
- **竞品雷达（Competitor Radar）**: 品牌、功能、口碑、价格

---

## Success Criteria

### Measurable Outcomes

#### M0（1 周）成功标准

- **SC-001**: 仓库体积下降 ≥ 50%，CI 安装时长下降 ≥ 40%
- **SC-002**: 质量看板可访问，展示采集成功率、重复率、处理耗时
- **SC-003**: 洞察卡片可浏览，点击可展开证据段落
- **SC-004**: E2E 测试在 5 分钟内完成
- **SC-005**: CSV 导出功能可用

#### M1（1 个月）成功标准

- **SC-006**: 重复率下降 ≥ 30%，主题簇纯度 ≥ 0.75
- **SC-007**: 前端无手写接口类型，字段拼写错误在编译期失败
- **SC-008**: 单条洞察成本下降 ≥ 30%，缓存命中率 ≥ 60%
- **SC-009**: PPT 和 Notion 导出功能可用
- **SC-010**: NER F1 ≥ 0.75，实体在卡片中高亮渲染
- **SC-011**: 质量看板支持可配置指标和时间窗

#### M2（1 季度）成功标准

- **SC-012**: 趋势分析可识别新兴主题（增长率 > 50%）
- **SC-013**: 竞品雷达可生成可视化，支持多社区对比

### 高层 OKR

- **O1 数据质量**: 重复率 ≤ 8%，采集成功率 ≥ 98%，证据可读性评分 ≥ 4/5
- **O2 洞察价值**: 洞察审阅通过率 ≥ 70%，Top10 机会卡片每周可被复用于评审会
- **O3 成本与效率**: 单条洞察成本下降 30%，P95 端到端耗时 ≤ 5 分钟

