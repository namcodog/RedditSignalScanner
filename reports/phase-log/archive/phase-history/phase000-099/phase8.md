# Phase 8 - 实体词典 & 行动位强化

## 概要
- 引入 `EntityMatcher` 服务，基于 `config/entity_dictionary.yaml` 统计品牌/功能/痛点命中情况。
- `analysis_engine` 输出 `entity_summary`，并将 `action_items` 一并写入 insights，解决 report service 回退生成的问题。
- `ReportContent`/`ReportPage` 新增“关键实体”视图，前端通过 `EntityHighlights` 组件高亮展示。
- 导出工具扩展：CSV 追加 `entities.csv`，文本导出列出每类实体统计。

## 关联任务
- T065-T067 实体匹配服务与单测
- T068-T071 报告行动位/前端展示强化

## 代码要点
- 新增 `backend/app/services/analysis/entity_matcher.py` 与单元测试。
- `InsightsPayload`、`ReportContent`、前端类型同步扩展 `entity_summary` 字段。
- 前端 `ReportPage` 新增实体标签页并复用翻译资源。
- Makefile/脚本无变更；导出函数完善多格式输出。

## 测试
- `pytest tests/services/test_entity_matcher.py tests/api/test_reports.py tests/services/test_report_export_service.py`
- `npx vitest run src/pages/__tests__/ReportPage.test.tsx src/services/__tests__/analyze.api.test.ts src/utils/__tests__/export.test.ts src/tests/contract/report-schema.contract.test.ts src/tests/contract/report-api.contract.test.ts src/pages/__tests__/ReportFlow.integration.test.tsx`

## 差异与风险
- 实体词典匹配采用简单大小写/子串策略，后续可考虑引入形态化或多语言支持。
- CSV/Text 导出格式扩展后文件数量增加，需要在文档中提醒使用者。
