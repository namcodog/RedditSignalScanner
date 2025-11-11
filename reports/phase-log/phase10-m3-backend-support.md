# Phase10 — M3 后端支撑（完成）

日期: 2025-10-30

## 实施内容（仅后端）
- 导出与降级
  - 新增 Markdown 导出：`GET /api/report/{task_id}/download?format=md`。
  - PDF 失败时自动降级 JSON：返回头 `X-Export-Fallback: json` + `X-Export-Error`。
  - 代码：`backend/app/services/report_export_service.py`、`backend/app/api/routes/reports.py`。
- 分析页文案与可用性提示（API 提供，前端可调用渲染）
  - `GET /api/guidance/input` 返回 placeholder/tips/examples。
  - 代码：`backend/app/api/routes/guidance.py`、主路由挂载于 `backend/app/main.py`。
- LLM 汇总增强开关与审计字段（可选，默认关闭）
  - 环境变量：`ENABLE_LLM_SUMMARY`、`LLM_MODEL_NAME`（默认 disabled）。
  - 元数据字段：`metadata.llm_used/llm_model/llm_rounds`（仅开启时写入）。
  - 代码：`backend/app/core/config.py`、`backend/app/schemas/report_payload.py`、`backend/app/services/report_service.py`。
- 监控看板联动（沿用既有接口/命令）
  - API：`GET /api/metrics/daily`（已存在）。
  - Make：`make metrics-daily-snapshot`（已存在）。

## 测试
- 导出：`backend/tests/api/test_report_export_markdown_and_fallback.py`（MD 成功 + PDF→JSON 降级）。
- 指导文案：`backend/tests/api/test_guidance_input_api.py`（结构化返回）。
- 结果：以上测试均通过。

## 统一反馈四问
1) 发现的问题/根因
- PDF 导出在本地常因 WeasyPrint 未安装而失败；缺统一降级提示；没有 Markdown 轻量导出。
- 分析页“结构化输入指导”此前只在文档内，缺后端 API 提供标准文案。
- LLM 审计字段缺口，无法在报告元数据清晰标注“是否启用、使用模型、轮数”。

2) 是否已精确定位
- 是。对应代码与路由已补齐，并用测试覆盖关键路径。

3) 精确修复方法
- 新增 MD 导出 + PDF 降级为 JSON 并加响应头；
- 新增 `/api/guidance/input` 提供统一指导文案；
- 配置和元数据支持 LLM 开关与审计字段（不默认启用，不触及外部依赖）。

4) 下一步
- 若需要，将实体榜单扩展至“证据链≥2、评分与导出”，并提供 `make entities-dictionary-check`；
- 前端可在报告页显示降级提示条与文案卡片；看板联动沿用既有接口即可。

