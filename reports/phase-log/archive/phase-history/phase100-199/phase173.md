# Phase 173 - v9 报告对齐与 report_html 优先级修复

## 目标
- 确保完整报告输出与 UI 展示口径一致（v9 为主，controlled_md 仅兜底）。
- 修复 report_html 在有真实报告时被 controlled_md 覆盖的问题。

## 变更摘要
- 新增 v9 prompt 接入：`backend/app/services/llm/report_prompts.py` 增加 `REPORT_SYSTEM_PROMPT_V9` 与 `build_complete_report_v9`。
- 主链路改用 v9：`backend/app/services/analysis_engine.py` 的 `_render_report_with_llm` 改为调用 `build_complete_report_v9`。
- report_html 优先级修复：`backend/app/services/report_service.py` 优先使用 `analysis.report.html_content`，仅当为空时才使用 controlled_md/T1 Market 兜底；同时将 Markdown 自动转换为 HTML（可读性更好）。
- 新增测试：验证 report_html 不再被 controlled_md 覆盖，并在缺失时能回退。

## 影响范围
- 完整报告展示（UI“完整报告”卡片）
- 报告导出（PDF/HTML）

## 测试
- `pytest backend/tests/services/test_report_service.py -k "report_html" -q`

## 产出
- `reports/v9_prompt_check_0c3bccf5-dd2c-4ca1-96ec-c3035cc21eac.md`
- `reports/v9_prompt_check_5d5991a1-1617-4513-80e3-69b6408ff517.md`

## 备注
- 验收库按规则为 dev（`reddit_signal_scanner_dev`）。

## 验收数据对齐
- 将 v9 报告写回 dev 库 `reports.html_content`（并刷新 generated_at）：
  - task_id: 0c3bccf5-dd2c-4ca1-96ec-c3035cc21eac
  - task_id: 5d5991a1-1617-4513-80e3-69b6408ff517

## 结构化报告对齐
- 新增 v9 结构化 JSON prompt，替换 report_structured 生成入口。
- 回填 dev 库两个验收任务的 report_structured（v9 规则）。
