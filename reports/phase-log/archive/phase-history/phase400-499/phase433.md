# Phase 433 - canonical_report_json 主链闭环

## 本轮目标

把 `Phase 36` 里刚写死的 Full A 合同，真正落成运行时主链：

- 后端正式输出 `canonical_report_json`
- 前端卡片页只消费这份 canonical report
- 前端不再本地拼一套 fallback 报告
- 测试与构建都按这条新合同验收

## 发现了什么

1. 之前“单一报告真相源”只在 SOP 里成立，运行时还没站住。
2. `ReportPage` 仍然保留 `buildFallbackStructuredReport()`，会在后端缺结构时本地拼 `decision_cards / market_health / battlefields / pain_points / drivers / opportunities`。
3. 这会直接破坏我们刚统一的合同：
   - 卡片视图并不完全来自 `canonical_report_json`
   - 页面会把后端合同缺口掩盖掉
   - 用户看到的是“前端脑补后的报告”，不是系统正式交付

## 是否需要修复

需要，而且必须先修。

如果这层不收掉，后面即使接 LLM 生成 Full A 长报告，也仍然会存在：

- JSON 一套真相
- 前端卡片一套真相
- HTML/Markdown 再一套真相

那产品会继续漂。

## 精确修复方法

### 1. 后端 payload 显式暴露 canonical report

- 在 `backend/app/schemas/report_payload.py` 新增 `canonical_report_json`
- 在 `backend/app/services/report/report_payload_builder.py` 里把 `analysis.sources.report_structured` 挂到这个字段

这一步的目的不是重复存一份数据，而是把“交付真相源”从隐式约定变成正式接口合同。

### 2. 前端只认 canonical_report_json

- `frontend/src/types/report/response.ts` 和 `frontend/src/types/report/schema.ts` 正式加入 `canonical_report_json`
- `frontend/src/pages/ReportPage.tsx` 改成只消费 `canonical_report_json`
- 删除本地 `buildFallbackStructuredReport()`
- 如果缺失，统一抛出 `Missing canonical_report_json`，交给产品缺口态处理

### 3. 测试整体抬到新合同

- 更新后端 payload 测试
- 更新前端合同测试
- 更新 `ReportPage` 页面测试
- 更新 `ReportFlow.integration` 流转测试
- 新增断言：`canonical_report_json` 缺失时，必须暴露统一缺口，而不是前端偷偷补结构

## 验证结果

### 后端

- `cd backend && pytest tests/services/report/test_report_payload_builder.py -q`
  - `1 passed`
- `cd backend && pytest tests/services/report/test_report_assembly_workflow.py tests/services/report/test_report_service_market_mode.py tests/api/test_analyze.py -q`
  - `21 passed`

### 前端

- `cd frontend && npm test -- src/tests/contract/report-api.contract.test.ts src/tests/contract/report-schema.contract.test.ts src/pages/__tests__/ReportPage.test.tsx`
  - `11 passed`
- `cd frontend && npm test -- src/pages/__tests__/ReportFlow.integration.test.tsx src/pages/__tests__/ReportPage.test.tsx src/tests/contract/report-api.contract.test.ts src/tests/contract/report-schema.contract.test.ts`
  - `12 passed`
- `cd frontend && npm run build`
  - 通过

## 当前结果

这轮完成后，系统第一次真正满足了下面这条硬合同：

- 报告卡片页不再自己补报告
- 后端显式交付 `canonical_report_json`
- 页面缺 canonical report 时会说真话，不再假装“还能拼一份”

换句话说，这一步不是“页面看起来更好看了”，而是：

**`canonical_report_json` 已经从文档合同，变成了系统运行时的真实唯一交付源。**

## 下一步系统计划

进入 `Phase 38`：

- 把 `canonical_report_json -> Full A narrative report(markdown/html)` 接成正式主链
- 让完整长报告也真正同源于 canonical report
- 然后再处理 `topic_profile` 的 canonical snapshot 展示轨

## 这次执行的价值

这轮最大的价值，是把“不要漂移”从一句要求，变成了代码级硬约束。

之前系统还能偷偷靠前端补洞维持表面完整；现在不行了。

这意味着后续每一层报告表达，只能围绕同一份 canonical report 往上长，不会再长出第二套语义。
