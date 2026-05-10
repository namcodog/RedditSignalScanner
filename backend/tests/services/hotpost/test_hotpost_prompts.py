from __future__ import annotations

from app.services.hotpost.card_content_generator import load_card_content_models
from app.services.hotpost.prompts import (
    PROMPT_MODULE_SCOPE,
    PROMPT_MODULE_STATUS,
    PROMPT_TEMPLATES,
)
from app.services.hotpost.report_llm import render_hotpost_prompt


def test_hotpost_prompt_templates_are_marked_legacy_search_report() -> None:
    assert PROMPT_MODULE_STATUS == "legacy_search_report"
    assert "HotpostService.search/report_llm" in PROMPT_MODULE_SCOPE
    assert "hotpost_v13_title_standalone" in PROMPT_MODULE_SCOPE
    assert set(PROMPT_TEMPLATES) == {"trending", "rant", "opportunity"}


def test_legacy_search_report_prompt_still_renders() -> None:
    prompt = render_hotpost_prompt(
        mode="trending",
        query="AI tools",
        time_filter="week",
        posts_data=[],
        comments_data=[],
    )

    assert "AI tools" in prompt
    assert "week" in prompt
    assert "帖子数据" in prompt


def test_daily_card_generation_uses_v13_profile_not_legacy_prompt_module() -> None:
    load_card_content_models.cache_clear()
    models = load_card_content_models()

    assert models["production_profile_id"] == "hotpost_v13_title_standalone"
    assert models["route_profiles"]["hotpost_v13_title_standalone"] == {
        "semantic_model": "google/gemini-3-flash-preview",
        "writer_model": "deepseek/deepseek-v4-pro",
        "enabled_by_default": False,
    }
