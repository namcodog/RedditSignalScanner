# Reddit Signal Scanner - API 接口文档（给前端/产品）

**更新日期**：2026-01-19  
**主门牌**：`/api`（前端统一用这个）  
**影子门牌**：`/api/v1`（只覆盖 v1 模块：analysis/stream/tasks/reports/export/decision-units；auth/admin/metrics/insights/guidance/diag 仅 `/api`）  
**真相源**：运行中的 `GET /openapi.json`（字段细节以它为准）

> 这份文档说人话：告诉前端“怎么接最稳、哪些情况别当 bug”。  
> 如果你发现这份文档和 `openapi.json` 不一致，以 `openapi.json` 为准。

---

## 0) 前端必看（注意事项，别踩坑）

1. **报告不是永远“满配”**  
   有些话题天生料少，系统会给你 `C_scouting`（勘探版）或者直接 `blocked`。这不是报错，是“诚实输出”。

2. **报告正文默认由 LLM 生成**  
   LLM 读取 **insights 主线 + facts_v2 证据切片** 生成报告；若门禁为 C/X，只返回解释与下一步动作。开发环境未配置 LLM 时会回退模板（仅调试用）。

3. **别只盯 `/api/report/{task_id}`，一定要配套看 sources 账本**  
   `GET /api/tasks/{task_id}/sources` 才是“为什么是这个结果”的说明书（tier、缺口、下一步动作都在里面）。

4. **SSE 需要带 Token**  
   原生 `EventSource` 不能带 header，前端请用 `fetch-event-source`（仓库前端已使用）或其它支持 header 的方案。

5. **返回格式有两套，前端要兼容**  
   - 多数业务接口：直接返回对象（比如 `/api/analyze`、`/api/report/...`、`/api/decision-units`）。  
   - 多数 admin 接口：返回包裹型 `{ "code": 0, "data": {...}, "trace_id": "..." }`。  
   - 例外（admin 直返）：`/api/admin/tasks/{task_id}/ledger`、`/api/admin/metrics/*`、`/api/admin/facts/*`。

6. **主业务链路的“合同”**  
   - 不允许 500（尤其是 RLS/GUC 相关）。  
   - 料不够要能解释（`blocked_reason` / `next_action` / `sources` 账本）。  
   - 前端把 `blocked_reason` 当“状态”，别当“报错弹窗”。

7. **前端 baseURL 建议**  
   - 本地默认：`http://localhost:8006/api`（前端已用 `VITE_API_BASE_URL` 支持配置）  
   - 接口路径统一写相对 `/api/...`，不要硬编码 `/api/v1/...`

---

## 1) 黄金链路（前端最先接这 6 个就能开工）

1. 登录拿 token：`POST /api/auth/login`
2. 创建任务：`POST /api/analyze` → 拿到 `task_id` + `sse_endpoint`
3. 进度：  
   - SSE：`GET /api/analyze/stream/{task_id}`（推荐）  
   - 轮询兜底：`GET /api/status/{task_id}`
4. 报告：`GET /api/report/{task_id}`
5. 解释“为什么”：`GET /api/tasks/{task_id}/sources`（拿 tier + 缺口 + 建议动作）
6.（可选）DecisionUnit：  
   - 列表：`GET /api/decision-units`  
   - 详情：`GET /api/decision-units/{decision_unit_id}`  
   - 反馈：`POST /api/decision-units/{decision_unit_id}/feedback`

---

## 2) Tier / Blocked（前端怎么展示才“不撒谎”）

这些信息主要来自 `GET /api/tasks/{task_id}/sources`（都在返回的 `sources` 字段里）：

- `sources.report_tier`：
  - `A_full`：完整版  
  - `B_trimmed`：缩水版（痛点/方案少，但不乱编）  
  - `C_scouting`：勘探版（只说明“目前看到的结构”，不下定论）  
  - `X_blocked`：直接拦截（不生成报告）
- `sources.facts_v2_quality.flags`：为什么降级/拦截（比如 `pains_low` / `solutions_low` / `topic_mismatch` 等）
- `GET /api/status/{task_id}` 里的 `blocked_reason / next_action`：给用户看的“一句话解释”

**前端最稳的做法**：  
报告页顶部固定展示：`tier + flags + next_action`，让用户一眼明白“这份报告能不能当结论用”。

---

## 3) 报告结构标准（LLM 输出）
报告正文必须按以下顺序输出：
1. 顶部信息（标题 + 简述）
2. 决策卡片（需求趋势 / P/S Ratio / 高潜力社群 / 明确机会点）
3. 概览（市场健康度：竞争饱和度 + P/S 解读）
4. 核心战场推荐（分社区画像：画像/痛点/策略）
5. 用户痛点（3 个）
6. Top 购买驱动力（2–3 条）
7. 商业机会卡（2 张）

说明：结论必须来自算法（insights + facts_slice），LLM 只负责表达。

补充：`GET /api/report/{task_id}` 的关键字段口径（前端直接用）
- `report.pain_points[].title/text`：后端补齐，title 为短标题，text 为完整描述
- `report.opportunities[].title/text`：同上
- `report.action_items[].title/category`：title 用于卡片标题，category 默认 `strategy`
- `report.purchase_drivers`：来自 `insights.top_drivers`
- `report.market_health`：包含 `saturation_level / saturation_score / ps_ratio / ps_ratio_assessment`
  - `ps_ratio` 取值口径：`facts_slice.ps_ratio` 优先，缺失则回退 `sources.ps_ratio`

---

## 4) 返回格式（两套，别搞混）

### 4.1 直返型（大多数业务接口）

例：`POST /api/analyze` 返回就是一个对象（没有 `code/data` 外壳）。

### 4.2 包裹型（多是 admin 接口）

例：`GET /api/admin/dashboard/stats`

```json
{
  "code": 0,
  "data": { "total_users": 3, "total_tasks": 3 },
  "trace_id": "59559c0f8e2d4205a1e483ecebda0393"
}
```

---

## 4) 接口总表（只列 `/api`，不列 `/api/v1` 别名）

统计口径：以运行时 `GET /openapi.json` 为准（已过滤 `/api/v1`）。

| 模块 | 接口数 | 认证 | 说明 |
|---|---:|---|---|
| auth | 3 | 无/JWT | 注册/登录/当前用户 |
| analysis | 1 | JWT | 创建分析任务 |
| stream | 1 | JWT | SSE 进度流 |
| tasks | 4 | 无/JWT | 状态/诊断/队列统计/sources 账本 |
| reports | 7 | JWT | LLM 报告 + 导出 |
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
| `POST` | `/api/admin/communities/tier-suggestions/emit-decision-units` | Admin JWT | 把调级建议翻译成 ops DecisionUnits（带证据链） |
| `DELETE` | `/api/admin/communities/{name}` | Admin JWT | 禁用社区 |
| `GET` | `/api/admin/communities/{name}/tier-audit-logs` | Admin JWT | 查看社区 Tier 调整历史 |
| `GET` | `/api/admin/dashboard/stats` | Admin JWT | Admin dashboard aggregate metrics |
| `GET` | `/api/admin/facts/snapshots/{snapshot_id}` | Admin JWT | 获取指定 facts_v2 审计快照 |
| `GET` | `/api/admin/facts/tasks/{task_id}/latest` | Admin JWT | 获取任务最新 facts_v2 审计包 |
| `GET` | `/api/admin/metrics/contract-health` | Admin JWT | 合同健康度（Phase106-2） |
| `GET` | `/api/admin/metrics/routes` | Admin JWT | 路由调用统计（golden vs legacy） |
| `GET` | `/api/admin/metrics/semantic` | Admin JWT | 语义库运行指标 |
| `GET` | `/api/admin/semantic-candidates` | Admin JWT | List semantic candidates |
| `GET` | `/api/admin/semantic-candidates/statistics` | Admin JWT | Semantic candidate statistics |
| `POST` | `/api/admin/semantic-candidates/{candidate_id}/approve` | Admin JWT | Approve semantic candidate |
| `POST` | `/api/admin/semantic-candidates/{candidate_id}/reject` | Admin JWT | Reject semantic candidate |
| `GET` | `/api/admin/tasks/recent` | Admin JWT | Recent tasks overview |
| `GET` | `/api/admin/tasks/{task_id}/ledger` | Admin JWT | Admin 任务复盘（sources 账本 + facts_v2 审计包索引） |
| `GET` | `/api/admin/users/active` | Admin JWT | Active users ranked by recent tasks |

### analysis（1）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `POST` | `/api/analyze` | JWT | Create analysis task |

### auth（3）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `POST` | `/api/auth/login` | 无 | Authenticate existing user and receive an access token |
| `GET` | `/api/auth/me` | JWT | Get current authenticated user |
| `POST` | `/api/auth/register` | 无 | Create a new account and receive an access token |

### beta（1）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `POST` | `/api/beta/feedback` | JWT | Submit Beta Feedback |

### decision-units（3）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `GET` | `/api/decision-units` | JWT | 获取 DecisionUnits 列表（平台级主合同） |
| `GET` | `/api/decision-units/{decision_unit_id}` | JWT | 获取 DecisionUnit 详情（含证据链） |
| `POST` | `/api/decision-units/{decision_unit_id}/feedback` | JWT | 提交 DecisionUnit 反馈（append-only） |

### diagnostics（1）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `GET` | `/api/diag/runtime` | JWT | 运行时诊断信息 |

### export（1）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `POST` | `/api/export/csv` | JWT | 导出分析报告 CSV |

### guidance（1）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `GET` | `/api/guidance/input` | 无 | 结构化输入指导与示例 |

### health（1）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `GET` | `/api/healthz` | 无 | Health Check Alias |

### insights（2）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `GET` | `/api/insights/card/{insight_id}` | JWT | 获取单个洞察卡片 |
| `GET` | `/api/insights/{task_id}` | JWT | 获取指定任务的洞察卡片列表 |

### metrics（2）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `GET` | `/api/metrics` | 无 | Get Quality Metrics |
| `GET` | `/api/metrics/daily` | 无 | Get Daily Quality Metrics |

### reports（7）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `GET` | `/api/report/{task_id}` | JWT | Fetch LLM-generated report (scouting/blocked returns explanation only) |
| `GET` | `/api/report/{task_id}/communities` | JWT | Fetch full community list used in report |
| `GET` | `/api/report/{task_id}/communities/download` | JWT | Download communities list as CSV (top or all) |
| `GET` | `/api/report/{task_id}/communities/export` | JWT | Export communities list (top or all) |
| `GET` | `/api/report/{task_id}/download` | JWT | Download report in specified format |
| `GET` | `/api/report/{task_id}/entities` | JWT | Export recognised entities (flattened) |
| `GET` | `/api/report/{task_id}/entities/download` | JWT | Download recognised entities as CSV |

### root（1）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `GET` | `/` | 无 | Root |

### stream（1）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `GET` | `/api/analyze/stream/{task_id}` | JWT | Task streaming progress (SSE) |

### tasks（4）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| `GET` | `/api/status/{task_id}` | JWT | 获取任务状态（缓存优先） |
| `GET` | `/api/tasks/diag` | 无 | 运行时配置诊断 |
| `GET` | `/api/tasks/stats` | JWT | 获取任务队列统计信息 |
| `GET` | `/api/tasks/{task_id}/sources` | JWT | 获取任务 sources 账本（用于复盘/演练） |

---

## 5) 关键接口示例（前端照着接就行）

### 5.1 创建任务（`POST /api/analyze`）

请求体（最少只要 `product_description`）：

```json
{
  "product_description": "面向 Shopify 卖家的广告优化与转化率提升工具",
  "mode": "operations",
  "audit_level": "gold",
  "topic_profile_id": "shopify_ads_conversion_v1"
}
```

说明（大白话）：
- `mode`：`market_insight`（偏买家声音） / `operations`（偏卖家/运营声音）。不传也行，系统会尽量自动选。  
- `audit_level`：通常不用前端写死，调试才会用到。  
- `topic_profile_id`：你要“锁死赛道”才传，不传就是走默认策略。

### 5.2 获取 sources 账本（`GET /api/tasks/{task_id}/sources`）

返回结构长这样（重点在 `sources` 字段里）：

```json
{
  "task_id": "5e4ac12c-df88-4597-b45d-74faa1a42e00",
  "status": "completed",
  "sources": {
    "report_tier": "C_scouting",
    "facts_v2_quality": {
      "tier": "C_scouting",
      "flags": ["pains_low", "brand_pain_low", "solutions_low"]
    }
  }
}
```

### 5.3 DecisionUnit 反馈（`POST /api/decision-units/{id}/feedback`）

请求体：

```json
{
  "label": "valuable",
  "note": "这条建议很有用"
}
```

`label` 只能是：`correct` / `incorrect` / `mismatch` / `valuable` / `worthless`。  
你不传 `evidence_id` 也可以，后端会自动绑定一条 top evidence（但前端建议优先传，复盘更清晰）。

---

## 6) 健康检查 / 诊断（本地联调用）

- `GET /api/healthz`：健康检查（200 就算活着）
- `GET /api/tasks/diag`：运行时配置诊断（偏运维）
- `GET /api/diag/runtime`：运行时诊断信息（需要 Admin JWT）
**注意**：admin 并非全包裹  
- 直返：`/api/admin/tasks/{task_id}/ledger`、`/api/admin/metrics/*`、`/api/admin/facts/*`  
- 包裹：`/api/admin/communities/*`、`/api/admin/dashboard/stats`、`/api/admin/tasks/recent`、`/api/admin/users/active`、`/api/admin/beta/feedback`、`/api/admin/semantic-candidates*`
