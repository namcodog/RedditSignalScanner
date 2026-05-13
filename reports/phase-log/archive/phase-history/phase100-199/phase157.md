# Phase 157 - LLM 接入核查（Grok / OpenRouter）

## 目标
- 核查 LLM API 是否已接入与可用
- 确认 Grok 模型口径

## 核查结果
- `backend/.env` 已配置：
  - `OPENAI_API_KEY` 已设置（已脱敏）
  - `OPENAI_BASE=https://openrouter.ai/api/v1`
  - `LLM_MODEL_NAME=x-ai/grok-4.1-fast`
  - `ENABLE_LLM_SUMMARY=true`
- `backend/app/services/llm/clients/openai_client.py` 使用 `OPENAI_BASE` 作为 `base_url`，符合 OpenRouter 接入要求。
- `.env` 加载优先级：shell > 根目录 `.env` > `backend/.env`（`backend/.env` 可覆盖 root 的占位值）。

## 结论
- LLM 接入已就绪，无需额外改动代码。
- 运行时请确保使用 `backend/.env`（或显式导出环境变量）。

## 变更
- 无代码改动。
