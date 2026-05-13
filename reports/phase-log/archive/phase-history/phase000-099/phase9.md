# Phase 9 - 文档 & 出口完善

## 今日交付
- README 增补「最新更新」与 `make local-acceptance` 命令说明。
- `docs/API-REFERENCE.md` 更新 `/api/report/{task_id}` 响应示例，加入 `entity_summary` 字段说明。
- 运行格式化：`isort` + `black`（针对新增/修改的 Python 文件）。
- 前端类型检查：`npm run type-check` ✅。
- 后端/前端复核：`pytest` 聚焦新增单元（entity matcher、report）、`npx vitest run` 针对报告/导出/契约测试。
- `make test-all` 尝试执行，后端 e2e 需真实依赖，现有环境缺省导致多项 e2e/服务测试失败（见下）。

## 测试记录
- ✅ `pytest tests/services/test_entity_matcher.py tests/api/test_reports.py tests/services/test_report_export_service.py`
- ✅ `npx vitest run src/pages/__tests__/ReportPage.test.tsx src/services/__tests__/analyze.api.test.ts src/utils/__tests__/export.test.ts src/tests/contract/report-schema.contract.test.ts src/tests/contract/report-api.contract.test.ts src/pages/__tests__/ReportFlow.integration.test.tsx`
- ⚠️ `make test-all`
  - 339 passed, 5 skipped, 10 failed（均为依赖完整运行环境的 e2e / 服务可靠性用例，如 `test_complete_user_journey_success`、`test_fault_injection.py::test_pipeline_tolerates_slow_database`）。
  - 失败原因：本地未启动 Celery/Redis/外部依赖，属既有环境限制，未发现新增逻辑导致的断言回归。

## 后续建议
1. 在可用的集成环境（含 Celery + Redis + Reddit 模拟数据）重跑 `make test-all`，确认全链路无回归。
2. 若继续扩展 Phase10，可考虑将实体摘要写入缓存命中监控，提升仪表板可视化。
