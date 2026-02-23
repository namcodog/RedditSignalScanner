# PRD-07: Admin 后台设计（控制塔优先 · 现状对齐版）

**更新日期**：2026-01-21  
**适用范围**：Admin 运维与运营闭环  
**对齐口径**：`docs/API-REFERENCE.md`、`docs/PRD/PRD-10-Admin社区管理Excel导入.md`、`reports/phase-log/phase106.md`、`reports/phase-log/phase107.md`

> 统一口径：以 `docs/API-REFERENCE.md` 为唯一接口合同；若 PRD 与 API 口径冲突，以 API 为准并先补文档。

---

## 1. 背景与目标

**北极星一句话**：Admin = 控制塔（可控运行）+ 操作台（快速运营），优先级 **70/30**。  
目的不是做花哨大屏，而是让系统**可运营、可复盘、可纠偏**。

- 可控运行：成本/失败率/降级拦截可解释、可追溯、可回滚  
- 快速运营：发现社区能闭环进池，不靠查库/改配置  

---

## 2. 范围与非目标

**范围（P0 必须闭环）**
- 候选社区审核闭环：发现 → 审核 → 入池  
- 社区池管理：可查/可筛/可调/可禁用/可回滚  
- 任务复盘与健康观测：2 分钟内定位“为什么这样”  

**非目标（P0 不做）**
- 不做在线调参台/复杂 BI  
- 不做多租户混看  
- 不做 Admin 内一键重跑/补量按钮  

---

## 3. 角色与权限（P0 口径）

- **Admin Only**：`/api/admin/*` 仅管理员可访问  
- **判定方式**：`is_superuser` 或 `ADMIN_EMAILS` 白名单  
- **审计要求**：关键变更必须可追溯（谁、何时、改了什么、原因、可回滚）

> P1 才考虑分权（Viewer/Operator/Approver），P0 保持极简权限模型。

---

## 4. 功能分层（P0 / P1 / P2）

### P0（必须全打通）
**P0-1 候选社区审核闭环**  
目标：发现社区能在 Admin 内完成审核入池  
接口：
- `GET /api/admin/communities/discovered`
- `POST /api/admin/communities/approve`
- `POST /api/admin/communities/reject`

**P0-2 社区池管理（方向盘）**  
目标：池子可查、可筛、可批量调整、可禁用、可回滚  
接口：
- `GET /api/admin/communities/pool`
- `PATCH /api/admin/communities/batch`
- `DELETE /api/admin/communities/{name}`
- `GET /api/admin/communities/{name}/tier-audit-logs`
- `POST /api/admin/communities/rollback`

**P0-3 任务复盘与健康观测**  
目标：拿到 task_id，2 分钟内复盘原因  
接口：
- `GET /api/admin/tasks/recent`
- `GET /api/admin/tasks/{task_id}/ledger`
- `GET /api/admin/metrics/contract-health`
- `GET /api/admin/dashboard/stats`（只读概览）

### P1（建议尽快补）
- **Excel 导入与导入历史**  
  `GET /api/admin/communities/template`  
  `POST /api/admin/communities/import`  
  `GET /api/admin/communities/import-history`
- **调级建议与应用**  
  `POST /api/admin/communities/suggest-tier-adjustments`  
  `GET /api/admin/communities/tier-suggestions`  
  `POST /api/admin/communities/apply-suggestions`  
  `POST /api/admin/communities/tier-suggestions/emit-decision-units`
- **语义候选审核**  
  `GET /api/admin/semantic-candidates`  
  `GET /api/admin/semantic-candidates/statistics`  
  `POST /api/admin/semantic-candidates/{candidate_id}/approve|reject`
- **Beta 反馈查看**  
  `GET /api/admin/beta/feedback`
- **路由/语义指标**  
  `GET /api/admin/metrics/routes`  
  `GET /api/admin/metrics/semantic`

### P2（有价值但易膨胀，需克制）
- Run Profile 在线切换（发现/补量策略写入）  
- Admin 内触发重跑/补量  
- 站外告警（Slack/飞书）  
- 全量 RBAC  

---

## 5. 核心流程（P0 必须闭环）

### 5.1 候选社区审核
1) 列表查看 `discovered`  
2) 查看证据帖子（Top N）  
3) approve / reject（必须填写原因）  
4) 通过后在社区池中可见

### 5.2 社区池管理
1) 过滤池子（tier/状态/标签）  
2) 单条或批量调整（tier/priority/is_active）  
3) 禁用/回滚必须二次确认  
4) tier_audit_logs 可追溯

### 5.3 任务复盘与健康观测
1) recent tasks 定位问题任务  
2) ledger 查看 sources 账本 + facts 审计索引  
3) contract-health 判断系统是否变贵/变吵/变不诚实

---

## 6. 页面结构与接口映射（P0 重点）

> 返回格式提示：Admin 接口有包裹型与直返型并存，详见 `docs/API-REFERENCE.md`。  
> 直返：`/api/admin/tasks/{task_id}/ledger`、`/api/admin/metrics/*`、`/api/admin/facts/*`。

### 6.1 Dashboard（控制塔总览）
**目标**：一眼判断系统是否“变贵/变吵/变不诚实”  
**关键字段**：
- tier 分布（A/B/C/X）
- blocked_reason TopN / next_action TopN
- 合同健康指标（失败率、p95、补量频次）
**筛选**：时间窗口、mode、audit_level  
**接口**：`/api/admin/dashboard/stats`、`/api/admin/metrics/contract-health`

### 6.2 Discovered Candidates（候选社区审核）
**目标**：发现 → 证据 → 审核 → 入池  
**关键字段**：
- name + status
- last_discovered_at / discovered_count
- 证据摘要（evidence_score / score / comments / probe_source）
**筛选**：status、tags、关键词命中、最低 evidence_score  
**接口**：`/api/admin/communities/discovered`、`/approve`、`/reject`

### 6.3 Community Pool（社区池管理）
**目标**：池子是方向盘  
**关键字段**：
- name + tier
- priority + is_active + health_status
- semantic_quality_score（或等价价值指标）
**筛选**：tier、is_active、blacklist、category、name 搜索  
**接口**：`/api/admin/communities/pool`、`/batch`、`/{name}`、`/{name}/tier-audit-logs`、`/rollback`

### 6.4 Tasks & Ledger（任务复盘）
**目标**：2 分钟内定位原因  
**关键字段**：
- task_id + created_at + user_id
- status + report_tier
- blocked_reason + next_action / failure_category
**筛选**：status、tier、failure_category、时间范围、user_id  
**接口**：`/api/admin/tasks/recent`、`/api/admin/tasks/{task_id}/ledger`

### 6.5 Governance（治理，P1 起）
**Tab A：Tier Suggestions**  
接口：`/api/admin/communities/tier-suggestions`、`/apply-suggestions`、`/rollback`  
**Tab B：Semantic Candidates**  
接口：`/api/admin/semantic-candidates`、`/statistics`、`/approve|reject`  
**Tab C：Beta Feedback**  
接口：`/api/admin/beta/feedback`

---

## 7. 数据口径（SSOT）

> Admin 不直连数据库，接口为真相；此处仅标注对照表，便于排障追溯。

- 候选审核：`discovered_communities` + `evidence_posts`  
- 社区池：`community_pool` + `tier_audit_logs`  
- 任务复盘：`tasks` + `facts_snapshots` + `facts_quality_audit` + sources 账本  
- 合同健康：`contract_health` 聚合口径

---

## 8. 运行与安全（危险操作清单）

**高危（必须二次确认 + 输入校验）**
- `DELETE /api/admin/communities/{name}`（禁用）
- `POST /api/admin/communities/rollback`（回滚）
- `POST /api/admin/communities/apply-suggestions`（批量调级）

**中危（二次确认 + 展示变更 diff）**
- `PATCH /api/admin/communities/batch`
- `POST /api/admin/communities/import`

**只读模式（P1）**
- `ADMIN_READ_ONLY=1` 时所有写接口返回 403，并在前端提示维护中

---

## 9. 反馈与通知（P0 口径）

- 操作成功：toast + 行内状态刷新  
- 操作失败：弹窗展示 message + 关键参数 + 可复制请求信息  
- Dashboard 顶部红黄牌（只读）：  
  - pending 候选堆积超阈值  
  - blocked_rate / failure_rate 异常  

---

## 10. 验收标准（P0 必测）

**成功标准（可量化）**
1) 候选审核闭环无需查库：discovered → approve/reject → pool 可见  
2) 任务复盘 2 分钟内完成：ledger 里能明确 tier/blocked/next_action  
3) 关键变更可追溯/可回滚：tier_audit_logs + rollback 生效

**必测场景**
- 登录与权限：无 token / 过期 token / 非管理员被拒  
- 候选审核：查看证据 → approve → pool 可见；reject → 状态变更 + 原因记录  
- 社区池：批量调整 → audit 记录可见 → rollback 恢复  
- 任务复盘：recent tasks → ledger 展示 sources 账本 + facts 索引  

---

## 11. 交付顺序（仅用现有接口）

**Step 0**：Admin 路由、鉴权守卫、API Client 统一封装  
**Step 1**：候选社区审核页（P0-1）  
**Step 2**：社区池管理页（P0-2）  
**Step 3**：任务复盘与健康观测页（P0-3）  
**Step 4**：治理页（P1）  

---

## 12. 追溯与引用

- 接口合同：`docs/API-REFERENCE.md`  
- Excel 导入：`docs/prd/PRD-10-Admin社区管理Excel导入.md`  
- 执行记录：`reports/phase-log/phase106.md`、`reports/phase-log/phase107.md`  
- Admin 测试：`docs/prd/PRD-08-端到端测试规范.md`
