# Phase 1045 - Hotpost V13 breakdown 覆盖补齐

## 这轮达到的目的
补齐 V13 正式出卡链路里的 breakdown 漏点；争议图不并入 V13 writer，继续保持独立 Gemini 争议压缩器。

## 当前状态变化
`generate_card_content()` 自动升级 breakdown 和 `refresh_breakdown_content()` 现在在 production profile 开启时使用 `hotpost_v13_title_standalone.writer_model`，即 `xiaomi/mimo-v2.5-pro`；未开启 profile 时仍回到原 `reasoning_model`。

## 还没完成什么
hot 争议图仍使用 `google/gemini-2.5-flash-lite`，这是当前保留的独立发布前组件；如果后续 Gemini 503 成为稳定阻塞，再单独做可观测的降级或重试治理。

## 下一步做什么
日常新出卡按 V13 链路继续；若再遇到 hot 争议图失败，先记录失败率和错误类型，再决定是否改模型或加重试。

## 验证
`SKIP_DB_RESET=1 PYTHONPATH=backend pytest backend/tests/services/hotpost/test_card_content_llm_router.py backend/tests/services/hotpost/test_card_content_generator.py backend/tests/services/hotpost/test_hot_controversy_llm.py backend/tests/scripts/evals/test_hotpost_three_tab_prompt_ab_v13.py backend/tests/scripts/evals/test_hotpost_v13_shadow_new_samples.py backend/tests/scripts/hotpost/test_v13_published_shadow_refresh.py -q`：`116 passed`。
