# Phase 1 集成记录（市场洞察 V2）

时间：2025-11-13 进度点：1.10（并行集成）

- 发现/根因：
  - 后端缺少 GTMActionPlanner 与 MarketReportBuilder 实现；`report_service.py` 仅生成执行摘要，未接入市场报告模式；Phase 1 并行产物（Persona/Quote/Saturation）无编排。
- 定位：
  - 集成点位于 `backend/app/services/report_service.py:get_report()`；在 Controlled 生成后插入 Market 模式渲染选择；模板路径 `backend/config/report_templates/market_insight_v1.md`。
- 精确修复：
  - 新增 `backend/app/services/reporting/gtm_planner.py`（模板回退，3相位行动）。
  - 新增 `backend/app/services/reporting/market_report.py`（上下文构建+并行 quick 提取：persona/quote/saturation）。
  - 新增模板 `backend/config/report_templates/market_insight_v1.md`。
  - `config.py` 增加 `enable_market_report`（默认关闭）。
  - 在 `report_service.py` 中：并行运行 quick 画像/引言/饱和度 → 生成 GTM → 组装上下文 → 渲染 Market 模板（可回退）。
- 下一步：
  - Phase 2：完善 GTM 计划细化（活动频率、合规检查）、引入 MarketingCopy（可选LLM）。
  - Phase 3：补充完整报告模板、导出与前端集成，完善覆盖率测试。
- 修复效果/达成结果：
  - 引入 Market 模式且保持向后兼容；新增 3 组测试覆盖核心行为；并行执行耗时可控（纯本地规则），预计后续引入 LLM 仍可降级运行。

## 产出
- 代码：GTMActionPlanner、MarketReportBuilder、Market 模板、服务集成开关。
- 测试：
  - `backend/tests/services/report/test_gtm_planner.py`
  - `backend/tests/services/report/test_market_report_builder.py`
  - `backend/tests/services/test_report_service_market_mode.py`

## 验收与自检（≤12 秒）
- 并行集成验收：
  - 正常分支：`pytest backend/tests/services/test_report_service_phase1_integration.py::test_phase1_parallel_integration_collects_results -q` → PASSED（~9.3s）。
  - 异常回退：`pytest backend/tests/services/test_report_service_phase1_integration.py::test_phase1_parallel_integration_degrades_on_exception -q` → PASSED（~7.5s）。
- 结构/导入链检查：通过。
- 默认关闭开关（`ENABLE_MARKET_REPORT=false`），保持向后兼容：通过。
