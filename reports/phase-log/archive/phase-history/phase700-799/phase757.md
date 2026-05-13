# Phase 757 - Ximo As Unified Card Output Model

## 判断

卡片输出模型统一切到 `xiaomi/mimo-v2-pro`。原因是 AB 样本里 ximo 对证据理解更稳，少夸张，适合作为 1.0 投资人演示阶段的主输出模型。

## 改动

- `backend/.env`
  - `HOTPOST_FAST_MODEL=xiaomi/mimo-v2-pro`
  - `HOTPOST_REASONING_MODEL=xiaomi/mimo-v2-pro` 保持不变。
- `backend/config/hotpost_quality.yaml`
  - `llm_routing.fast_model` 改为 `xiaomi/mimo-v2-pro`。
  - 清空 `fast_model_pack_overrides`，避免 paid-economics / upstream-winds 偷偷走 Gemini。
- `backend/config/prompt_assets/signal_compact_prompt.md`
  - 补充潜力快帖输出收敛规则：每个字段只讲一个判断，能一句说清就不写两句。

## 验证

- 配置自检显示：
  - `fast_model: xiaomi/mimo-v2-pro`
  - `reasoning_model: xiaomi/mimo-v2-pro`
  - `fast_model_pack_overrides: {}`
- `python -m py_compile app/services/hotpost/card_content_generator.py app/services/hotpost/card_content_prompts.py app/services/hotpost/card_content_llm_router.py`
- `pytest tests/services/hotpost/test_reddit_guide_prompt_assets.py tests/services/hotpost/test_card_content_generator.py::test_load_card_content_models_uses_ximo_fast_model_without_pack_overrides tests/services/hotpost/test_card_content_generator.py::test_signal_prompt_budget_keeps_role_readable tests/services/hotpost/test_card_content_generator.py::test_generate_card_content_applies_business_growth_scope_polish_without_touching_paid_econ tests/services/hotpost/test_card_content_generator.py::test_generate_card_content_applies_agent_builder_pack_rules -q --tb=short -p no:schemathesis`

结果：6 passed。

## 样本

同 3 张潜力快帖临时样本默认链路调用记录：

- `('xiaomi/mimo-v2-pro', 18.0)`
- `('xiaomi/mimo-v2-pro', 18.0)`
- `('xiaomi/mimo-v2-pro', 18.0)`

未写入 draft store，未发布。
