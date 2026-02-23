# Phase 147 - 战场排序修复 + LLM 提示词迁移

日期：2026-01-22

## 目标
- 修复战场画像排序单测失败。
- 将 T1 报告提示词迁移到主链路可用位置，并接入 LLM 报告生成。

## 变更
- `backend/app/services/analysis/insights_enrichment.py`：
  - 战场排序改为 pain_hits 优先、mentions 次级。
- `backend/app/services/llm/report_prompts.py`：
  - 迁移 `REPORT_SYSTEM_PROMPT_V2` 与分段 prompt 构建函数。
- `backend/app/services/analysis_engine.py`：
  - 新增 `_render_report_with_llm`，按 `enable_llm_summary` + `openai_api_key` 触发。
  - 非 C/X 报告优先走 LLM，失败回落本地模板。

## 测试
- `pytest backend/tests/services/test_facts_slice.py backend/tests/services/test_insights_enrichment.py`

## 结果
- 5/5 单测通过。
