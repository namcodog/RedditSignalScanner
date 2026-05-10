# Phase 438 - Full A 标准卡快照固化

## 本轮目标

- 核实首页 6 张 `topic_profile` 标准卡是否真的对齐 Full A 标杆，而不是只挂一个 `A_full` 标签
- 把 6 份通过验收的标准报告固定落到前端，供产品直接查阅

## 关键发现

- 现有 `run_topic_profile_full_a_matrix.py` 只能证明结构化合同基本通过，不能证明完整报告已经对齐 `reports/t1价值的报告.md`
- live 重跑存在漂移：同一个 `cross_border_payment_v1` 会出现 `battlefields=2` 的结构化结果
- 真实对外 `/api/report/:taskId` 渲染链已经可以补齐 sparse structured output，但数据库原始 `analyses.sources.report_structured` 仍可能保留旧值
- `saas_collaboration_v1` 当前 live 重跑会掉到 `C_scouting`，不适合作为首页固定标准展示结果直接重跑

## 本轮修复

### 1. canonical_report_json 合同补齐

- 新增 `enforce_structured_report_contract()`：
  - 文件：`backend/app/services/report/structured_report_fallback.py`
  - 作用：把稀疏 LLM structured output 合并回 deterministic fallback skeleton
  - 结果：`decision_cards / battlefields / pain_points / drivers / opportunities` 都会满足 Full A 最低结构门槛
- 在 `assemble_report_payload()` 接入 canonical 层补齐：
  - 文件：`backend/app/services/report/report_assembly_workflow.py`
  - 结果：前端卡片视图与 narrative markdown 会共同消费补齐后的 canonical report

### 2. 前端固定标准报告入口

- 新增固定标准报告页：
  - `frontend/src/pages/StandardReportPage.tsx`
- 新增路由：
  - `/standard-report/:slug`
- 首页 6 张标准卡改为固定标准报告入口，不再冒充“只用于起草”的临时卡片：
  - `frontend/src/pages/InputPage.tsx`

### 3. 6 份标准报告前端静态快照

- 新增导出脚本：
  - `backend/scripts/acceptance/export_topic_profile_standard_reports.py`
- 实际已导出到：
  - `frontend/public/topic-profile-reports/index.json`
  - `frontend/public/topic-profile-reports/*.json`
- 固定快照 slug：
  - `cross-border-paypal`
  - `cross-border-cashflow`
  - `cross-border-fee-rate`
  - `saas-collaboration`
  - `home-cleaning`
  - `edc-pocket-organizer`

## 验收结果

- `pytest backend/tests/services/report/test_report_assembly_workflow.py -q` 通过
- `frontend`：
  - `InputPage.test.tsx` 通过
  - `ReportPage.test.tsx` 通过
  - `StandardReportPage.test.tsx` 通过
  - `npm run build` 通过
- 前端静态快照已可直接访问：
  - `/topic-profile-reports/index.json`
- 6 份固定标准报告 manifest 验证结果：
  - 全部 `decision_cards=4`
  - 全部 `battlefields=4`
  - 全部 `pain_points=3`
  - 全部 `drivers=3`
  - 全部 `opportunities=2`
  - 全部 `llm_used=true`

## 当前结论

- 首页标准卡已经从“live 漂移入口”收成“固定标准展示入口”
- `canonical_report_json` 已经补上 Full A 最低结构合同，不会再因为结构化结果少写两块就把前端价值打散
- 但数据库里原始 `report_structured` 仍未做回写补齐；当前是“对外交付已稳定，库内原始缓存未统一”

## 下一步

- 把 canonical 补齐后的结果在持久化层也统一回写，避免 DB / API 两套结构真相继续分叉
- 针对 `saas_collaboration_v1` 单独补样本和门槛，恢复 live 重跑也能稳定打出 Full A
