# Phase 174 - 单次 LLM JSON 主链路 + 证据链接补齐 + Makefile 稳定启动

## 目标
- 主链路只调用一次 LLM（生成结构化 JSON），报告 HTML 由 JSON 转出。
- 证据溯源链接可点击（example_posts.url 统一补齐）。
- 固化后端稳定重启流程到 Makefile。

## 变更摘要
- 主链路去除 Markdown LLM：`backend/app/services/analysis_engine.py`
  - 取消 `_render_report_with_llm` 调用，`llm_used/llm_rounds` 以结构化 JSON 为准。
- JSON → Markdown → HTML：`backend/app/services/report_service.py`
  - 结构化 JSON 优先生成完整报告 HTML，确保 UI 与 JSON 口径一致。
- 证据链接补齐：`backend/app/services/report_service.py`
  - 对 `insights.pain_points[].example_posts` 的 `url/permalink` 统一规范化为绝对链接。
- Makefile 稳定启动：`Makefile`
  - 新增 `dev-backend-start/stop/restart/logs`，默认加载 `backend/.env`。

## 影响范围
- 用户端报告展示（完整报告 + 卡片结构）
- 痛点证据溯源链接
- 本地后端启动/重启流程

## 测试
- `pytest backend/tests/services/test_report_service_market_mode.py -k "report_service_prefers_structured_report_for_html" -q`
- `pytest backend/tests/services/test_report_service.py -k "normalizes_example_post_urls" -q`

## 产出
- `reports/v9json_check_0c3bccf5-dd2c-4ca1-96ec-c3035cc21eac.json`
- `reports/v9json_check_5d5991a1-1617-4513-80e3-69b6408ff517.json`

## 备注
- 验收库：dev（`reddit_signal_scanner_dev`）。
