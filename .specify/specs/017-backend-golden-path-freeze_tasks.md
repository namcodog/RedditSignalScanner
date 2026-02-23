# Tasks: 冻结后端黄金路径（/api）& legacy 观察期（Spec 017）

> 约定：任务编号以 `R017-Txx` 表示，便于在 PR / Commit / phase-log 中引用。  
> 规则：**先写测试，再写实现**；所有结论以“代码证据 + 可量化指标”为准。

---

## Phase 0：盘点 & 契约冻结（不动业务）

### R017-T01 ✅ 黄金路径清单（代码证据版）
- **输出**：一份“黄金路径清单”（入口/handler/关键表/关键配置）
- **证据来源**：
  - FastAPI 挂载点：`backend/app/main.py:create_application`
  - v1 主路由聚合：`backend/app/api/v1/api.py:api_router`
  - 任务入口：`backend/app/api/v1/endpoints/analyze.py:create_analysis_task`
  - SSE：`backend/app/api/v1/endpoints/stream.py:stream_task_progress`
  - 状态：`backend/app/api/v1/endpoints/tasks.py:get_task_status`
  - 报告：`backend/app/api/v1/endpoints/reports.py`
  - 导出：`backend/app/api/v1/endpoints/export.py`
  - DB 模型：`backend/app/models/*`（Task/Analysis/Report/InsightCard/Evidence/PostRaw/PostHot/Comment 等）
  - 关键配置：`backend/app/core/config.py:Settings`、`backend/app/services/crawler_config.py:get_crawler_config`
- **验收**：
  - 清单里每一条都能指向“路径 + 符号名”
  - 写入 `reports/phase-log/phase20.md`（含 git commit hash + 是否 dirty）

### R017-T02 ✅ legacy 路由清单（可下线候选）
- **输出**：legacy 路由列表（路径前缀/handler/用途/是否必须保留）
- **证据来源**：
  - legacy 挂载点：`backend/app/main.py:create_application`（`legacy_router.include_router(...)`）
  - legacy routers：`backend/app/api/routes/*` + `backend/app/api/admin/*`
- **验收**：
  - 每个 legacy 路由标注：是否被前端/脚本/内部调用（以代码引用与测试覆盖为准）
  - 给出“观察期后可下线候选”清单（先不删除）

---

## Phase 1：门牌正确性（先修“说法”，不改主干行为）

### R017-T10 ✅ [Test] 黄金门牌契约测试（存在性 + 不指错路）
- **文件**：`backend/tests/api/test_golden_path_contract.py`
- **测试点**：
  1) 黄金路径端点在 app.routes 中存在（至少：`/api/analyze`、`/api/status/{task_id}`、`/api/analyze/stream/{task_id}`、`/api/report/{task_id}`、`/api/export/csv`）
  2) `GET /api/healthz` 返回体里的 “deprecated/use …” 不得指向不存在路径
  3) 根路径 `/` 返回的 endpoints 列表不应包含不存在的路径（如果保留该列表）
- **验收**：已通过（并新增“冻结路径不允许重复定义”的防回归用例）

### R017-T11 ✅ [Impl] 修正错误的 “deprecated/use …” 与根路径端点列表
- **文件**：`backend/app/main.py`
- **目标**：不改变真实路由，只修正“说法”，避免误导调用方与测试
- **回滚**：纯文案/列表变更，可随时回退

---

## Phase 2：legacy 观察期指标（让“旧路没人走”可证明）

### R017-T20 ✅ [Test] legacy vs golden 调用计数（开关可关）
- **测试点**：
  - 开启计数后，请求 `/api/*` 会写入 Redis 计数键
  - 能区分 “golden endpoints” vs “legacy endpoints”
  - 关闭计数后不写 Redis（避免线上风险）

### R017-T21 ✅ [Impl] 路由调用统计中间件
- **建议位置**：`backend/app/middleware/route_metrics.py`（或等价模块）
- **实现要点**：
  - 识别当前请求命中的 route（method + path template）
  - 按路由组写计数：`golden` / `legacy`
  - 写入 Redis（复用现有 redis 配置），并支持采样/开关

### R017-T22 ✅ [Impl] monitoring_task 出具“观察期看板字段”
- **文件**：`backend/app/tasks/monitoring_task.py`
- **输出字段**：
  - `golden_calls_last_minute`
  - `legacy_calls_last_minute`
  - 若 legacy 非 0：给出 top paths（最多 N 条）
- **验收**：指标能被 `/api/metrics/daily` 或 Redis dashboard 读取（以当前代码为准，选最短路径）

---

## Phase 3：数据库最小可追溯（先写不读）

### R017-T30 ✅ [Test] 分析主线写入 sources 最小血缘字段
- **文件**：`backend/tests/api/test_golden_business_flow.py`（等价覆盖：写库后的 `Analysis.sources` 断言）
- **验收**：生成 analysis 后，`Analysis.sources` 至少包含（字段名以实现为准）：
  - posts/comments 数量
  - communities 数量
  - cache_hit_rate（如有）
  - crawler 配置哈希/版本标识（如能取到）

### R017-T31 ✅ [Impl] 把最小血缘写入 `Analysis.sources`
- **文件候选**：`backend/app/tasks/analysis_task.py`、`backend/app/services/analysis_engine.py`
- **原则**：不引入新表，先用已有 `Analysis.sources` 承载，后续再升级到独立表

### R017-T40 ✅ [Test] 后端+DB 黄金业务闭环回归测试（非前端E2E）
- **文件**：`backend/tests/api/test_golden_business_flow.py`
- **覆盖链路**：token → `POST /api/analyze` → 写库（tasks/analyses/reports）→ `GET /api/status/{task_id}` → `GET /api/report/{task_id}`
- **验收**：不依赖外部 Reddit/LLM；测试可稳定证明“主线闭环不翻车”

---

## Phase N：验收与记录

### R017-T99 ✅ phase18/phase19 记录（以代码证据为准）
- **文件**：`reports/phase-log/phase18.md`
- **文件**：`reports/phase-log/phase19.md`
- **文件**：`reports/phase-log/phase20.md`
- **必须写清**：
  - 冻结的黄金路径契约（路径清单 + 证据）
  - legacy 清单与观察期标准
  - 运行测试命令与结果
