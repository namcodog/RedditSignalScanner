# Phase 158 - LLM 配置清理（单段生效）

## 目标
- 将 LLM 配置收敛为单段（OpenRouter + Grok）
- 其他供应商配置保留为候选注释

## 变更
- `backend/.env`
  - 移除重复 OpenAI 段落的生效配置
  - 保留 OpenRouter 生效段：`OPENAI_BASE=https://openrouter.ai/api/v1` + `LLM_MODEL_NAME=x-ai/grok-4.1-fast`
  - OpenAI/其它模型改为候选注释

## 结果
- 默认使用 OpenRouter + Grok
- 未要求时不会改动模型与 base
