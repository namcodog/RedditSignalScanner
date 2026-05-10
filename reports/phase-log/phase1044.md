# Phase 1044 - Hotpost V13 正式出卡全覆盖验收

## 这轮达到的目的
确认并补齐 V13 不只停在 eval/shadow：正式 `generate_card_content()` 现在默认走 `hotpost_v13_title_standalone`，并在字段校验前执行 V13 title 问题检测与 title-only repair。

## 当前状态变化
新增生产模块 `card_content_title_v13.py` 承接 V13 标题独立性规则；正式出卡链路变为 `deepseek/deepseek-v4-flash` 语义 brief -> `xiaomi/mimo-v2.5-pro` 写卡 -> 命中问题时同模型只修 title -> 原有字段校验与 readout。

## 还没完成什么
已发布卡的 V13 shadow / apply-plan 仍是独立人工审批链，不会因为日常新出卡默认 V13 而自动覆盖历史 release。

## 下一步做什么
下一轮日常新出卡可按正式链路使用 V13；如果要刷新历史已发布卡，继续走 shadow review packet -> human approval -> apply-plan。

## 验证
`SKIP_DB_RESET=1 PYTHONPATH=backend pytest backend/tests/services/hotpost/test_card_content_llm_router.py backend/tests/services/hotpost/test_card_content_generator.py backend/tests/services/hotpost/test_hot_controversy_llm.py backend/tests/scripts/evals/test_hotpost_three_tab_prompt_ab_v13.py backend/tests/scripts/evals/test_hotpost_v13_shadow_new_samples.py backend/tests/scripts/hotpost/test_v13_published_shadow_refresh.py -q`：`114 passed`。
