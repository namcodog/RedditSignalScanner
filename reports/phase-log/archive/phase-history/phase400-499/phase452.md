# Phase 452 - PayPal 证据链与颗粒度对齐

## 1. 发现了什么？

- 用户这轮把问题重新定义得很准确：不是只看链接有没有渲染，而是要看“标题、证据、完整正文是不是同一个真相源”。
- 本轮确认了两个真实漂移源：
  - `report_structured / canonical_report_json` 的 pain 顺序会漂离 `report.pain_points`，前端如果按数组下标挂证据，就会把错的 Reddit 原帖挂到错的痛点下。
  - fallback opportunities 还在机械取原始机会列表前两条，PayPal 这条 live 恰好会混入英文噪音机会，导致机会卡一度退化成模板话。

## 2. 是否需要修复？

- 需要，而且这轮已经修掉了。
- 不修的话，前端即使把 Reddit 链接做成可点击，也可能点开的是错证据；`A_full` 也会继续出现“痛点一套、机会一套、证据另一套”的漂移。

## 3. 精确修复方法

### 后端

- `backend/app/services/analysis/analysis_engine.py`
  - 英文痛点如果没被翻成人话，直接不准进入 pain payload。
- `backend/app/services/analysis/analysis_rendering.py`
  - analysis 阶段就先跑 `enforce_structured_report_contract()`，不再把脏 structured 直接存进 sources。
- `backend/app/services/report/report_assembly_workflow.py`
  - `/api/report` 出口前再次强制跑 structured contract，避免旧任务脏 structured 透传到前端。
- `backend/app/services/report/structured_report_fallback.py`
  - 机会标题不再退化成 `机会 1`。
  - 战场 fallback 改成“社区 + 麻烦 + 先验证什么”的具体表达。
  - structured pain points 改成 “base track 优先”，保证 canonical pain 和 raw evidence 同源。
  - structured opportunities 改成 “base track 优先”，避免 candidate drift 把 PayPal 第 1/2 张机会卡带偏。
  - fallback 机会筛选优先中文业务机会，跳过英文噪音机会。
- `backend/app/services/llm/report_prompts.py`
  - 继续收紧 marketplace / listing / 帖子碎片进入 pain / opportunity 的入口。

### 前端

- 新增 `frontend/src/lib/report-evidence.ts`
  - 做 pain evidence 语义对齐，不再按 index 盲挂。
- `frontend/src/pages/ReportPage.tsx`
  - 卡片页和完整报告都改成用对齐后的 evidence source。
- `frontend/src/pages/StandardReportPage.tsx`
  - 标准报告页同样改成用语义对齐 evidence。
- `frontend/src/pages/__tests__/ReportPage.test.tsx`
  - 新增“应该按痛点语义对齐证据链，而不是按数组位置硬绑定”回归测试。

## 4. 真实 live 结果

- 第 1 次复验：`3ff2a508-542a-44cb-a86a-a499e25e05a9`
  - 机会卡更准，但 pain / evidence 仍未完全同源。
- 第 2 次复验：`34252ccc-d5a6-4109-800d-f34429442780`
  - pain / evidence 已对齐，但机会卡被 fallback 拉回模板话。
- 第 3 次复验：`8c9ca2aa-c990-4354-9eb8-a2a4b9e4da7b`
  - pain / evidence 对齐稳定，但机会卡仍被英文噪音顺序误导。
- 第 4 次复验：`877ea8a4-6035-4a04-834c-75e5558eaf42`
  - 首轮直出 `A_full`
  - pain points 与 raw evidence 同源
  - 第 1/2 张机会卡重新收回：
    - `多平台收款插件配置助手`
    - `国际收款账户开通助手`

## 5. 验证

- `cd backend && ../.venv/bin/pytest tests/services/report/test_structured_report_fallback.py -q`
  - `13 passed`
- `cd backend && ../.venv/bin/pytest tests/services/report/test_report_assembly_workflow.py tests/services/analysis/test_analysis_engine.py -q -k 'report_assembly_workflow or build_source_examples or translate_pain_signal'`
  - `7 passed`
- `cd frontend && npm test -- src/pages/__tests__/ReportPage.test.tsx src/pages/__tests__/StandardReportPage.test.tsx`
  - `11 passed`
- `cd backend && ../.venv/bin/python scripts/acceptance/run_live_report_acceptance.py --product-description '帮跨境电商卖家看清 PayPal 的手续费、风控冻结和回款拖延，判断有没有值得切入的替代收款工具机会。' --topic-profile-id cross_border_payment_v1 --required-tier A_full`
  - `accepted=true`
  - `task_id=877ea8a4-6035-4a04-834c-75e5558eaf42`

## 6. 当前判断

- PayPal 这条 live 现在已经从“看起来像 Full A”回到“痛点、机会、证据同源”的状态。
- 但这还不是系统性完工；下一步该做的是把同一套 pain / opportunity contract 推到剩余 5 张标准快照，再做一轮首页样板人工验收。
