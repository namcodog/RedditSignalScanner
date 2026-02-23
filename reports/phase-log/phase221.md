# Phase 221

## 目标
- 按用户反馈优化爆帖速递体验与输出质量：OpenRouter 认证、搜索覆盖、痛点分类、fallback 深度、用户原话、竞品兜底。

## 完成内容
- LLM Key 优先级统一：新增 `resolve_llm_api_key`，OpenRouter base 优先使用 OPENROUTER_API_KEY，服务与预检统一调用。
- 默认时间范围扩大：Trending 默认 time_filter 调整为 all。
- Subreddits 上限放宽：由 5 → 10。
- 痛点分类优化：按匹配次数选择最强类别，新增 quality/instructions/shipping/compatibility 等细分标签词库。
- Fallback 结论增强：补充高频信号词、情绪分布、主要社区。
- user_voice 补强：优先使用 evidence_posts.body_preview，避免空洞/不完整。
- 竞品兜底：新增正则提取竞品名称的 fallback（LLM 为空时生效）。

## 测试
- `pytest backend/tests/services/hotpost/test_hotpost_rules.py -q`
- `pytest backend/tests/services/hotpost/test_hotpost_schema.py -q`
- `pytest backend/tests/services/hotpost/test_hotpost_summary.py -q`
- `pytest backend/tests/services/hotpost/test_hotpost_time_filter.py -q`
- `pytest backend/tests/services/hotpost/test_hotpost_detail_builder.py -q`
- `pytest backend/tests/services/hotpost/test_hotpost_enrichment.py -q`
- `pytest backend/tests/services/llm/test_openai_client.py -q`

## 结论
- Phase 221 完成，体验优化与输出增强已落地。
