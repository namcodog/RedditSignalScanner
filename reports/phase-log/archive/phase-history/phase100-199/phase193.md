# Phase 193

## 目标
- 接入爆帖速递三套 Prompt（Trending/Rant/Opportunity），生成结构化 LLM 输出并暂存。

## 变更
- 新增 Prompt 模板常量：`backend/app/services/hotpost/prompts.py`
- 新增结构化报告生成器：`backend/app/services/hotpost/report_llm.py`
- 在搜索流程中调用结构化 LLM 报告，并写入 Redis：`backend/app/services/hotpost/service.py`
- 新增单测覆盖 Prompt 渲染/JSON 解析：`backend/tests/services/hotpost/test_hotpost_report_llm.py`

## 验证
- `PYTHONPATH=backend pytest backend/tests/services/hotpost/test_hotpost_report_llm.py -q`

## 结论
- 三套 Prompt 已接入，结构化 LLM 输出可生成并写入 Redis（hotpost:llm_report:{query_id}）。

## 影响范围
- 仅爆帖速递模块；API 返回结构暂未变化（后续步骤会对齐）。
