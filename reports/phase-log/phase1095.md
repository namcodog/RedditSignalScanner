# phase1095 - CI-R mypy 历史债清理

这轮目的：先清掉 CI-R 验收链被 mypy 暴露出的历史类型债，避免推荐预览停在“功能测试过，但类型门没过”。

当前状态变化：修复 `card_storage_layout.py` 的 JSON 读写类型收窄、`keywords.py` 的 YAML group 类型收窄、`post_semantic_label.py / comment.py / semantic_observation.py` 的 SQLAlchemy 注解问题。

验收结果：目标 mypy 已通过 `7` 个相关文件；推荐预览 CLI 仍为 `acceptance_passed=true / ready_count=30 / tags=3 / recommendations=30`；相关测试已通过。

边界更新：`test_hotpost_prompts.py` 已改成 legacy 搜索报告模块验收，不再拿 V13 出卡合同误验旧 `PROMPT_TEMPLATES`；当前出卡链路仍由 `card_content_generator + hotpost_v13_title_standalone` 覆盖。
