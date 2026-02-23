# Phase 108 - 前端 API 对齐核查（基于 API-REFERENCE）

日期：2026-01-19

## 核查范围
- 结构文档：`README.md`、`docs/2025-10-10-文档阅读指南.md`（分角色阅读路径）
- 对照文档：`docs/API-REFERENCE.md`
- 前端代码：`frontend/src/api/*`、`frontend/src/services/*`、`frontend/src/pages/*`

## 已接入的前端接口（现状）
- 登录与认证：`/api/auth/register`、`/api/auth/login`、`/api/auth/me`
- 黄金链路（主业务）：`/api/analyze`、`/api/status/{task_id}`、`/api/analyze/stream/{task_id}`、`/api/report/{task_id}`
- 报告补充：`/api/report/{task_id}/communities`
- 洞察卡：`/api/insights/{task_id}`、`/api/insights/card/{insight_id}`
- Beta 反馈：`/api/beta/feedback`（包裹型返回已兼容）
- 质量指标：`/api/metrics`（admin 服务内使用）
- 诊断与队列：`/api/diag/runtime`、`/api/tasks/diag`、`/api/tasks/stats`
- Admin 基本功能：社区池/导入/调级/任务复盘/看板/用户等（`/api/admin/...` 多数已接）

## 对照 API-REFERENCE 的差异与风险
1) **sources 账本未接入**  
   - 文档要求：报告页要看 `/api/tasks/{task_id}/sources`（tier/flags/next_action）。  
   - 现状：用户侧页面未调用该接口；仅进度页展示 `blocked_reason/next_action`（来自 `/api/status/{task_id}`）。

2) **metrics 日报路径可能双 `/api`**  
   - `frontend/src/api/metrics.ts` 使用 `'/api/metrics/daily'`，但 `apiClient` 已以 `/api` 为 baseURL，实际请求可能变成 `/api/api/metrics/daily`。

3) **报告 PDF 导出未走统一 baseURL/Token**  
   - `frontend/src/pages/ReportPage.tsx` 直接 `fetch('/api/report/...')`，且 token 读取 `localStorage.getItem('token')`；  
   - 与 `apiClient` 的 `VITE_API_BASE_URL` 与 `auth_token` 机制不一致，切换环境或独立前后端部署时风险更高。

4) **DecisionUnit 未接入前端**  
   - 文档已给 `/api/decision-units` 系列接口，但前端暂无 API/页面入口。

5) **AnalyzeRequest 可选参数未暴露**  
   - 文档提到 `mode / audit_level / topic_profile_id` 可选，但 `AnalyzeRequest` 仅有 `product_description`，前端无传参入口（功能缺口，非阻断）。

## 结论（当前前端状态）
前端已覆盖黄金链路与多数 admin 接口；主要缺口集中在 **sources 账本** 与 **DecisionUnit** 的接入，以及少量 **路径/鉴权一致性** 问题（metrics 与 report 导出）。
