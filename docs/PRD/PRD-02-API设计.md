# PRD-02: API设计规范（后端现状对齐版）

## 0. 对齐口径（唯一标准）
- **运行时真相**：`GET /openapi.json`
- **文档基线**：`docs/API-REFERENCE.md`（已同步到本 PRD）
- **主门牌**：`/api`（`/api/v1` 仅覆盖 v1 模块：analysis/stream/tasks/reports/export/decision-units）

## 1. 问题陈述

### 1.1 背景
系统采用“任务创建 → 异步执行 → SSE 推送 → 报告拉取”的模式，避免长请求超时，并允许前端实时展示进度。

### 1.2 目标
- **核心四端点**完成一条分析闭环。
- **SSE 实时推送**作为主通道，轮询为兜底。
- **缓存优先**的任务状态查询（DB + 缓存一致）。
- **扩展导出接口**：CSV/JSON/Markdown/PDF。
- **可追溯账本**：`/api/tasks/{task_id}/sources`。
- **LLM 必经**：报告由 LLM 输出（insights 主线 + facts_v2 证据切片，开发未配置 LLM 时仅调试回退模板）。
- **平台级中间产物**：`/api/decision-units` + 反馈。
- **Admin 运维**：社区池/导入/调级/指标/账本。

### 1.3 非目标
- 不做 WebSocket 全双工。
- 不做复杂的批量任务管理。
- 不在 API 层暴露内部任务细节（只保留必要字段）。

---

## 2. 核心端点（实际已落地）

**统一入口**：`/api` 为主入口；`/api/v1` 仅覆盖 v1 模块（analysis/stream/tasks/reports/export/decision-units）。

### 2.1 创建任务
`POST /api/analyze`

**请求体**（实际字段）:
```json
{
  "product_description": "AI 笔记应用，帮助研究者自动组织想法",
  "mode": "market_insight",
  "audit_level": "lab",
  "topic_profile_id": "ecommerce_business"
}
```

**响应**:
```json
{
  "task_id": "uuid",
  "status": "pending",
  "created_at": "2025-12-25T10:30:00Z",
  "estimated_completion": "2025-12-25T10:35:00Z",
  "sse_endpoint": "/api/analyze/stream/{task_id}"
}
```

### 2.2 SSE 实时进度
`GET /api/analyze/stream/{task_id}`

**事件类型**：`connected` / `progress` / `completed` / `error` / `heartbeat` / `close`

**示例**:
```
event: connected
data: {"task_id":"..."}

event: progress
data: {"task_id":"...","status":"processing","progress":50,"message":"Task processing"}

event: completed
data: {"task_id":"...","status":"completed","progress":100}
```

### 2.3 任务状态（缓存优先）
`GET /api/status/{task_id}`

**响应字段**（摘要）:
- `status`, `progress`, `message`, `error`
- `retry_count`, `failure_category`, `last_retry_at`, `dead_letter_at`
- `sse_endpoint`

### 2.4 拉取报告
`GET /api/report/{task_id}`

**核心结构**：
- `report_html`（LLM 生成的报告 HTML）
- `report`（结构化结果，基于 insights + facts_slice）
- `metadata`（置信度/缓存命中率/处理耗时）
- `overview`（Top 社区/覆盖量）
- `stats`（基础统计）

**report 结构补充（前端直用字段）**：
- `report.pain_points[].title/text`：短标题 + 完整描述（后端补齐）
- `report.opportunities[].title/text`：短标题 + 完整描述（后端补齐）
- `report.action_items[].title/category`：标题用于卡片，`category` 默认 `strategy`
- `report.purchase_drivers`：购买驱动力（来源 `insights.top_drivers`）
- `report.market_health`：`saturation_level / saturation_score / ps_ratio / ps_ratio_assessment`
  - `ps_ratio` 口径：`facts_slice.ps_ratio` 优先，缺失时回退 `sources.ps_ratio`
- `sources.knowledge_graph`：固定结构化骨架（社区→痛点→证据→场景/驱动力），UI 可直接读取

**口径说明**：
- 当 `sources.report_tier` 为 `C_scouting/X_blocked` 时，仅返回勘探/拦截说明，不输出完整报告正文。
- 报告是否可用以 `/api/tasks/{task_id}/sources` 为准。
- 报告正文结构以 `docs/PRD/PRD-SYSTEM.md` 的“报告结构标准”为唯一准则。
- `sources.hybrid_posts_used`：混合检索补充的帖子数（用于调参/排障）。

---

## 3. 扩展接口（已落地）

- `GET /api/tasks/{task_id}/sources`（报告 tier/flags 账本）
- `GET /api/report/{task_id}/download`（PDF/Markdown/JSON）
- `GET /api/report/{task_id}/communities`（完整社区明细）
- `GET /api/report/{task_id}/communities/export`（导出社区清单）
- `GET /api/report/{task_id}/entities`（实体聚合）
- `GET /api/report/{task_id}/entities/download`（实体导出）
- `POST /api/export/csv`（导出 CSV，body: `{ "task_id": "..." }`）
- `GET /api/tasks/stats`（Celery 队列统计）
- `GET /api/tasks/diag`（运行时诊断）
- `GET /api/decision-units` / `GET /api/decision-units/{id}` / `POST /api/decision-units/{id}/feedback`
- `GET /api/metrics` / `GET /api/metrics/daily`
- `GET /api/diag/runtime`
- `POST /api/beta/feedback`
- `GET /api/guidance/input`

---

## 4. 鉴权与错误口径
- **鉴权**：Bearer Token（JWT），`/api/auth/*` 获取。
- **常见错误**：
  - 401：token 无效/过期
  - 403：任务不属于当前用户
  - 404：任务/报告不存在
  - 409：任务未完成或导出冲突
  - 429：报告/导出频率限制

## 4.1 返回格式（两套并存）
- **直返型**：多数业务接口（`/api/analyze`、`/api/report/...`、`/api/decision-units`）。  
  **admin 直返**：`/api/admin/tasks/{task_id}/ledger`、`/api/admin/metrics/*`、`/api/admin/facts/*`。
- **包裹型**：多数 admin 接口，返回 `{ code, data, trace_id }`。  
  主要是：`/api/admin/communities/*`、`/api/admin/dashboard/stats`、`/api/admin/tasks/recent`、`/api/admin/users/active`、`/api/admin/beta/feedback`、`/api/admin/semantic-candidates*`。

## 5. 接口总表（全量对齐）

统计口径：以运行时 `GET /openapi.json` 为准（已过滤 `/api/v1` 别名）。

| 模块 | 接口数 | 认证 | 说明 |
|---|---:|---|---|
| auth | 3 | 无/JWT | 注册/登录/当前用户 |
| analysis | 1 | JWT | 创建分析任务 |
| stream | 1 | JWT | SSE 进度流 |
| tasks | 4 | 无/JWT | 状态/诊断/队列统计/sources 账本 |
| reports | 7 | JWT | 报告 + 导出 |
| insights | 2 | JWT | 洞察卡（旧卡片，不含 DecisionUnit） |
| decision-units | 3 | JWT | DecisionUnit 列表/详情/反馈 |
| beta | 1 | JWT | Beta 反馈 |
| guidance | 1 | 无 | 输入指导 |
| metrics | 2 | 无 | 指标（公开） |
| diagnostics | 1 | JWT | 运行时诊断 |
| health | 1 | 无 | 健康检查 |
| admin | 30 | Admin JWT | 管理后台/社区池/审计/运营 |
| root | 1 | 无 | 根路由 |
| **合计** | **59** | - | - |

### admin（30）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `GET` | `/api/admin/beta/feedback` | Admin JWT | List beta feedback |
| `POST` | `/api/admin/communities/apply-suggestions` | Admin JWT | 应用调级建议 |
| `POST` | `/api/admin/communities/approve` | Admin JWT | 批准社区 |
| `PATCH` | `/api/admin/communities/batch` | Admin JWT | 批量更新社区配置 |
| `GET` | `/api/admin/communities/discovered` | Admin JWT | 查看待审核社区 |
| `POST` | `/api/admin/communities/import` | Admin JWT | 上传并导入社区信息 |
| `GET` | `/api/admin/communities/import-history` | Admin JWT | 查询社区导入历史 |
| `GET` | `/api/admin/communities/pool` | Admin JWT | 查看社区池（增强版） |
| `POST` | `/api/admin/communities/reject` | Admin JWT | 拒绝社区 |
| `POST` | `/api/admin/communities/rollback` | Admin JWT | 回滚社区 Tier 变更 |
| `POST` | `/api/admin/communities/suggest-tier-adjustments` | Admin JWT | 生成社区 Tier 调级建议 |
| `GET` | `/api/admin/communities/summary` | Admin JWT | 获取社区验收列表 |
| `GET` | `/api/admin/communities/template` | Admin JWT | 下载社区导入 Excel 模板 |
| `GET` | `/api/admin/communities/tier-suggestions` | Admin JWT | 查看社区调级建议列表 |
| `POST` | `/api/admin/communities/tier-suggestions/emit-decision-units` | Admin JWT | 把调级建议翻译成 ops DecisionUnits |
| `DELETE` | `/api/admin/communities/{name}` | Admin JWT | 禁用社区 |
| `GET` | `/api/admin/communities/{name}/tier-audit-logs` | Admin JWT | 查看社区 Tier 调整历史 |
| `GET` | `/api/admin/dashboard/stats` | Admin JWT | Admin dashboard aggregate metrics |
| `GET` | `/api/admin/facts/snapshots/{snapshot_id}` | Admin JWT | 获取指定 facts_v2 审计快照 |
| `GET` | `/api/admin/facts/tasks/{task_id}/latest` | Admin JWT | 获取任务最新 facts_v2 审计包 |
| `GET` | `/api/admin/metrics/contract-health` | Admin JWT | 合同健康度 |
| `GET` | `/api/admin/metrics/routes` | Admin JWT | 路由调用统计 |
| `GET` | `/api/admin/metrics/semantic` | Admin JWT | 语义库运行指标 |
| `GET` | `/api/admin/semantic-candidates` | Admin JWT | List semantic candidates |
| `GET` | `/api/admin/semantic-candidates/statistics` | Admin JWT | Semantic candidate statistics |
| `POST` | `/api/admin/semantic-candidates/{candidate_id}/approve` | Admin JWT | Approve semantic candidate |
| `POST` | `/api/admin/semantic-candidates/{candidate_id}/reject` | Admin JWT | Reject semantic candidate |
| `GET` | `/api/admin/tasks/recent` | Admin JWT | Recent tasks overview |
| `GET` | `/api/admin/tasks/{task_id}/ledger` | Admin JWT | Admin 任务复盘（sources 账本 + facts_v2 索引） |
| `GET` | `/api/admin/users/active` | Admin JWT | Active users ranked by recent tasks |

---

**文档状态**：已按统一口径更新（LLM 报告必经）。
