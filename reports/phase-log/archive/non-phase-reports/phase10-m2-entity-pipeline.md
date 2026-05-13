# Phase10 — M2 实体识别流水线与导出（完成）

日期: 2025-10-30

## 实施内容
- 新增流水线：`backend/app/services/analysis/entity_pipeline.py`
  - 支持从 `backend/config/entity_dictionary/*.yml` 合并加载多域词典（默认 `default.yml`）。
  - 提供 `summarize(insights)` 输出，兼容现有 `entity_summary` 结构。
- 接入分析引擎：`backend/app/services/analysis_engine.py`
  - 优先用新流水线生成 `entity_summary`，失败时回退到旧 `EntityMatcher`。
- 新增数据与配置：
  - `backend/config/entity_dictionary/default.yml`（brands/features/pain_points 基础词典）。
- 新增导出接口（JSON/CSV）：`backend/app/api/routes/reports.py`
  - `GET /api/report/{task_id}/entities` → `EntityExportResponse`（拍平成 name/category/mentions）。
  - `GET /api/report/{task_id}/entities/download` → CSV。
  - 若报告内 `entity_summary` 为空，则在路由端按 insights 现算填充，保证鲁棒性。
- 报告结构增强：
  - `ReportContent.entity_leaderboard` 列表（拍平的实体榜单，后端按 mentions 排序，最多 20 项）。
- 门禁扩展：`backend/scripts/content_acceptance.py`
  - 新增“实体覆盖度”断言（总实体数 ≥ 3 计合格，计入评分）。
- Makefile 便捷命令：`make report-entities TASK_ID=...` 将实体导出为 JSON 存档。

## 测试
- 单元测试：
  - `backend/tests/services/test_entity_pipeline.py`（词典命中与汇总）。
- API 测试：
  - `backend/tests/api/test_report_entities_export.py`（JSON 与 CSV 导出、鉴权）。
- 运行片段：
  - `pytest backend/tests/services/test_entity_pipeline.py -q` 通过。
  - `pytest backend/tests/api/test_report_entities_export.py -q` 通过。

## 统一反馈四问
1) 发现的问题/根因
- 之前仅有 `entity_dictionary.yaml`，缺多域词典与汇总骨架；
- 报告若未在引擎阶段写入 `entity_summary`，导出接口会拿不到实体。

2) 是否已精确定位
- 是。已在路由层增加“现算”兜底，且引擎默认走新流水线。

3) 精确修复方法
- 新增 `entity_pipeline.py` + 词典目录；分析引擎用新流水线产出；
- 新增导出端点；门禁加入实体覆盖度；Makefile 增便捷导出。

4) 下一步
- M2 后续切片：
  - 实体榜单（带证据≥2、评分与导出）；
  - 词典分域模板（crypto/ai/saas 等），加 `make entities-dictionary-check`；
  - 将实体榜单纳入前端展示与下载。

## 验收对照（Spec 009 · M2）
- 实体识别流水线/接入 analysis_engine：✅
- 实体覆盖门禁：✅（content-acceptance 已扩展）
- CSV 导出：✅（/entities/download）
- 单元/集成测试：✅
