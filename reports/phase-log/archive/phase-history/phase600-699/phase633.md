# Phase 633 - 审计层补齐与 fresh 报告导出

## 时间
- 2026-04-03

## 发现
- fresh `AI_Workflow` live 已通过，但 `analyses.sources.analysis_audit` 在新任务上缺失。
- 旧通过任务仍保留 `analysis_audit`，说明这不是历史数据口径问题，而是审计字段没有被持续保活。

## 修复
- 新增共享审计摘要模块：
  - `backend/app/services/analysis/analysis_audit_summary.py`
- `analysis_finalization_support.py` 改为复用共享 builder
- `report_repository.persist_report_structured(...)` 现在会保证：
  - `report_structured` 持久化时，如果 `analysis_audit` 缺失，则按当前 sources 正式重建
- `analysis_payload_loader.py` / `schemas/analysis.py` 现在正式承认 `analysis_audit`，不再把它当未知字段丢弃

## 验证
- 定向测试：
  - `pytest tests/services/report/test_analysis_payload_loader.py tests/services/report/test_report_repository.py tests/services/analysis/test_analysis_finalization_support.py tests/services/report/test_report_request_support.py -q`
  - `19 passed`
- fresh task 审计修复：
  - `task_id = 27c1dbd2-e562-4840-9522-9e98946db8d0`
  - `has_analysis_audit = true`
  - `audit_reason_code = passed`

## 报告导出
- fresh `AI_Workflow` 报告 markdown 已导出：
  - `/Users/hujia/Desktop/RedditSignalScanner/LATEST_AI_WORKFLOW_REPORT_2026-04-03.md`

## 当前判断
- 主链双模型分层已在 fresh live 过线
- 审计层现在也补齐了
- 剩下不是链路缺失，而是报告内容质量仍可继续打磨
