from __future__ import annotations

from scripts.acceptance.run_warzone_live_matrix import (
    DEFAULT_WARZONE_CASES,
    _pick_titles,
)


def test_default_warzone_cases_count_is_eight() -> None:
    assert len(DEFAULT_WARZONE_CASES) == 8


def test_pick_titles_supports_dict_and_text_items() -> None:
    values = [
        {"title": "标题一"},
        {"description": "描述二"},
        "文本三",
        {"title": ""},
    ]
    assert _pick_titles(values) == ["标题一", "描述二", "文本三"]
