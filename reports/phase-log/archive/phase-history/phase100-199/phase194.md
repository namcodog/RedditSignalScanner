# Phase 194

## 目标
- 对齐 Hotpost API 返回结构，确保与三套 Prompt 输出字段一致。

## 变更
- 扩展 Hotpost schema：新增 topics/competitor_mentions/migration_intent/top_quotes/unmet_needs/existing_tools/user_segments/market_opportunity 等结构化字段，放宽 PainPoint 结构以兼容 LLM 产出。
  - `backend/app/schemas/hotpost.py`
  - `backend/app/schemas/__init__.py`
- 新增 LLM 报告合并器，并在响应中应用：
  - `backend/app/services/hotpost/report_llm.py`
  - `backend/app/services/hotpost/service.py`
- 新增单测：
  - `backend/tests/services/hotpost/test_hotpost_report_merge.py`

## 验证
- `PYTHONPATH=backend pytest backend/tests/services/hotpost/test_hotpost_report_llm.py backend/tests/services/hotpost/test_hotpost_report_merge.py -q`

## 结论
- API 响应可直接承载三套 Prompt 的结构化字段，LLM 输出已可映射到响应结构。

## 影响范围
- 仅爆帖速递模块响应结构。
