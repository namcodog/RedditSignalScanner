from app.services.llm.report_prompts import (
    REPORT_SYSTEM_PROMPT_V9_JSON,
    build_report_structured_prompt_v9,
)


def test_v9_json_system_prompt_has_plain_language_addendum() -> None:
    assert "通俗补全" in REPORT_SYSTEM_PROMPT_V9_JSON


def test_v9_json_user_prompt_has_plain_language_addendum() -> None:
    messages = build_report_structured_prompt_v9("测试产品", "facts")
    user_content = messages[1]["content"]
    assert "通俗补全" in user_content
