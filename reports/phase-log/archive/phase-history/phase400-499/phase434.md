# Phase 434 - 完整报告同源化（第一半）

## 本轮目标

把完整报告这条链，先从“只有 HTML 快照”推进到“有正式 markdown 文档源”，并且保证它和当前 canonical/controlled 主链同源。

这一步不直接声称“Full A narrative report 已完成”，只先做最小正确闭环：

- payload 正式返回 `report_markdown`
- markdown 导出优先使用正式文档源
- 前端完整报告入口在 HTML 缺失时也能打开正式 markdown 文档

## 发现了什么

1. `Phase 37` 之后，卡片页已经切到 `canonical_report_json`，但完整报告仍然主要表现为一个 `report_html` 快照。
2. 这意味着“完整报告”在系统里还不算正式对象，更像一个渲染结果。
3. 如果后面要接 LLM Full A narrative report，没有正式 `report_markdown` 字段，整条链会继续模糊：
   - 后端生成过什么
   - 导出导的是什么
   - 前端打开的完整报告到底是不是同一份东西

## 是否需要修复

需要。

这不是锦上添花，而是完整报告链从“结果快照”升级为“正式文档对象”的前置步骤。

## 精确修复方法

### 1. payload 正式带 `report_markdown`

- `backend/app/schemas/report_payload.py` 新增 `report_markdown`
- `render_bundle` 同时携带 `report_markdown + report_html`
- `report_assembly_workflow` 把 `structured_markdown` 接进 render bundle
- `report_payload_builder` 正式把 `report_markdown` 写进 payload

### 2. 导出优先吃正式文档源

- `ReportExportService.generate_markdown()` 先看 `report.report_markdown`
- 只有在没有正式 markdown 时，才退回旧的 lightweight markdown fallback

### 3. 前端完整报告入口补齐 markdown 兜底

- `ReportPage` 现在会把 `report_markdown` 也带进本地完整报告入口
- 如果 `report_html` 缺失，但 `report_markdown` 还在，仍然能打开完整文档视图

## 验证结果

### 后端

- `cd backend && pytest tests/services/report/test_render_bundle.py tests/services/report/test_report_payload_builder.py tests/services/report/test_report_export_service.py tests/services/report/test_report_assembly_workflow.py tests/services/report/test_report_service_market_mode.py tests/api/test_report_export_markdown_and_fallback.py -q`
  - `19 passed`

### 前端

- `cd frontend && npm test -- src/tests/contract/report-api.contract.test.ts src/tests/contract/report-schema.contract.test.ts src/pages/__tests__/ReportPage.test.tsx src/pages/__tests__/ReportFlow.integration.test.tsx`
  - `12 passed`
- `cd frontend && npm run build`
  - 通过

## 当前结果

完整报告已经不只是一个 `report_html` 快照了。

现在系统正式具备了：

- `canonical_report_json`
- `report_markdown`
- `report_html`

三者在主链里的关系也更清楚了：

- `canonical_report_json` 是交付真相源
- `report_markdown / report_html` 是这份真相源往文档视图的产物

## 还没完成的部分

这轮只完成了 `Phase 38` 的第一半。

还没完成的是最关键那一步：

- **用 LLM 基于 `canonical_report_json` 生成对齐 `t1价值的报告.md` 的 Full A narrative report**

当前 `report_markdown` 还主要来自结构化 renderer / controlled markdown，不是最终的 Full A 语义报告。

## 下一步系统计划

继续 `Phase 38` 后半段：

1. 梳理现有 LLM/market markdown 路径与 `canonical_report_json` 的脱节点
2. 新建或复用一条 `canonical_report_json -> Full A narrative markdown` 的正式 workflow
3. 再补：
   - 后端 narrative 合同测试
   - 前端完整报告视图同源验收
   - `topic_profile` 标准展示轨的最终接线

## 这次执行的价值

这轮的价值，是把“完整报告”从一个不透明的渲染结果，推进成了一个正式可追踪的文档对象。

这样后面接 LLM Full A narrative report 时，就不是在旧模板链上打补丁，而是在已经明确的文档主链上继续往前走。
