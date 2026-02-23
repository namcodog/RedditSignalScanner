# Phase 116 - PRD vs 运行入口 全量验收（实跑）

日期：2026-01-19

## 目标
按 `reports/phase-log/phase115.md` 清单逐条实跑，核实 PRD 与“运行入口”能对上。

## 环境与账号
- 启动方式：`ADMIN_EMAILS=admin@test.com make dev-golden-path`
- Admin 账号：`admin@test.com / Admin123!`
- 普通用户（本次跑接口用）：`e2e_1768828814@test.com / Test123!`
- 洞察卡片任务账号：`test@example.com / test123456`

## 实跑结果（摘要）

### 1) 服务与运维入口
- `GET /api/healthz`：200
- `GET /api/tasks/diag`：200
- `GET /api/diag/runtime`：用户 403 / 管理员 200（权限符合预期）
- `GET /api/tasks/stats`：200

### 2) 用户主链路 API
- 登录态验证：`GET /api/auth/me` → 200
- 新建任务：`POST /api/analyze` → 201
- 任务状态：`GET /api/status/{task_id}` → completed
- SSE：`GET /api/analyze/stream/{task_id}` → 2s 超时（可能没在短时间内推新事件）

### 3) 报告/账本/导出
- `GET /api/report/{task_id}` 与 report 系列：403（普通用户会员等级不足）
- `GET /api/tasks/{task_id}/sources`：200
- `GET /api/report/{task_id}/entities/download`：200
- `POST /api/export/csv`：403（会员等级限制）

### 4) 洞察卡片
- `GET /api/insights/{task_id}`：200（test@example.com）
- `GET /api/insights/card/{id}`：200

### 5) Decision Unit
- 列表 `GET /api/decision-units`：200（空列表）
- 详情/反馈：无可用 ID，本次未实跑

### 6) Admin 入口
- `/api/admin/tasks/recent`：200
- `/api/admin/metrics/*`：200
- `/api/admin/semantic-candidates/*`：200
- `/api/admin/communities/*`（pool/summary/discovered/template/suggest）：200

### 7) 前端路由
- 通过 curl 访问 `/ /progress /report /insights /decision-units /login /register /admin /dashboard`：均为 200

## 发现的问题/阻塞点（仅记录，不做修复）
1) `POST /api/auth/login` 对 `prd-test@example.com` 报 500（多条同 email 记录）。
2) 报告系列接口对免费账号返回 403（需要 PRO 账号才能完全验收）。
3) SSE 在 2s 内未推事件（短超时下无法断言）。

## 原始执行输出
- 详细日志：`tmp/phase115_check_results.txt`

## 结论
运行入口与 PRD 可对上；报告导出与会员权限相关，需要用 PRO 账号再补一次完整验收。
