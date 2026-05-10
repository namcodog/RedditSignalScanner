from __future__ import annotations

import json
from pathlib import Path

from backend.scripts.evals.run_hotpost_three_tab_prompt_ab_v1 import (
    LANE_ORDER,
    build_plain_language_overlay,
    load_project_env,
    load_sample_cards,
    render_markdown_report,
    _should_retry_generation_error,
    _with_retry_instruction,
)


def _write_card(cards_dir: Path, card_id: str, *, lane: str, card_type: str = "validate") -> None:
    cards_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "card_id": card_id,
        "card_type": card_type,
        "lane": lane,
        "title": f"{lane} title",
        "summary_line": f"{lane} summary",
        "audience": f"{lane} audience",
        "why_now": f"{lane} why now",
        "source_scope_id": "ai-automation",
        "source_scope_name": "AI 与自动化",
        "top_community": "r/test",
        "thread_count": 1,
        "community_count": 1,
        "signal_level": "sustained",
        "why_now_reason": "recurring_7d",
        "intent_tags": ["趋势变化"],
        "detail": (
            {
                "thesis": "thesis",
                "writing_angle_or_perspective": "angle",
                "tension_point_or_why_it_matters": "tension",
                "title_hooks": ["hook"],
                "quote_pack": ["quote｜翻译｜r/test"],
            }
            if card_type == "write"
            else {
                "flashpoint": "flash",
                "fight_line": "fight",
                "why_test_now": "why test",
                "continue_signal": "continue",
                "stop_signal": "stop",
            }
            if lane == "hot"
            else {
                "pain_point": "pain",
                "target_user_and_scene": "scene",
                "why_test_now": "why test",
                "min_test_action": "去看原始讨论",
                "continue_signal": "continue",
                "stop_signal": "stop",
            }
        ),
        "quotes": [
            {
                "text": "This is a concrete quote.",
                "community": "r/test",
                "permalink": f"https://reddit.test/{card_id}/1",
            },
            {
                "text": "This is another concrete quote.",
                "community": "r/test",
                "permalink": f"https://reddit.test/{card_id}/2",
            },
        ],
    }
    (cards_dir / f"{card_id}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_load_sample_cards_uses_latest_release_and_prefers_write_breakdown(tmp_path: Path) -> None:
    releases_dir = tmp_path / "releases"
    release_id = "release-test"
    cards_dir = releases_dir / release_id / "cards"
    releases_dir.mkdir(parents=True, exist_ok=True)
    (releases_dir / "latest.json").write_text(json.dumps({"release_id": release_id}), encoding="utf-8")

    _write_card(cards_dir, "signal-1", lane="signal")
    _write_card(cards_dir, "hot-1", lane="hot")
    _write_card(cards_dir, "breakdown-validate-ignored", lane="breakdown")
    _write_card(cards_dir, "breakdown-write-1", lane="breakdown", card_type="write")

    samples = load_sample_cards(releases_dir=releases_dir, limit_per_lane=1)

    assert list(samples) == list(LANE_ORDER)
    assert samples["signal"][0]["card_id"] == "signal-1"
    assert samples["hot"][0]["card_id"] == "hot-1"
    assert samples["breakdown"][0]["card_id"] == "breakdown-write-1"


def test_plain_language_overlay_keeps_structure_boundary() -> None:
    overlay = build_plain_language_overlay()

    assert "不新增字段" in overlay
    assert "不改字段名" in overlay
    assert "不改 JSON 结构" in overlay
    assert "普通用户" in overlay
    assert "报告腔" in overlay


def test_load_project_env_prefers_project_openrouter_config(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "OPENAI_BASE=https://openrouter.ai/api/v1",
                "OPENROUTER_API_KEY=project-openrouter-key",
                "GEMINI_API_KEY=project-gemini-key",
                "HOTPOST_REASONING_MODEL=deepseek/deepseek-v4-pro",
                "SOME_OTHER_KEY=project-value",
            ]
        ),
        encoding="utf-8",
    )
    environ = {
        "OPENAI_BASE": "https://api.openai.com/v1",
        "OPENROUTER_API_KEY": "stale-openrouter-key",
        "GEMINI_API_KEY": "stale-gemini-key",
        "HOTPOST_REASONING_MODEL": "old-model",
        "SOME_OTHER_KEY": "keep-real-shell-value",
    }

    load_project_env(env_path, environ)

    assert environ["OPENAI_BASE"] == "https://openrouter.ai/api/v1"
    assert environ["OPENROUTER_API_KEY"] == "project-openrouter-key"
    assert environ["GEMINI_API_KEY"] == "project-gemini-key"
    assert environ["HOTPOST_REASONING_MODEL"] == "deepseek/deepseek-v4-pro"
    assert environ["SOME_OTHER_KEY"] == "keep-real-shell-value"


def test_render_markdown_report_is_lane_grouped() -> None:
    rows = [
        {
            "lane": "signal",
            "card_id": "signal-1",
            "baseline": {"title": "旧标题", "summary_line": "旧摘要"},
            "variant": {"title": "新标题", "summary_line": "新摘要"},
        },
        {
            "lane": "hot",
            "card_id": "hot-1",
            "baseline": {"title": "旧热点", "flashpoint": "旧火点"},
            "variant": {"title": "新热点", "flashpoint": "新火点"},
        },
    ]

    report = render_markdown_report(rows)

    assert "# Hotpost 三 Tab Prompt A/B 小样本报告" in report
    assert "## signal" in report
    assert "## hot" in report
    assert "signal-1" in report
    assert "旧标题" in report
    assert "新标题" in report


def test_retry_instruction_feeds_validation_error_back_to_model() -> None:
    messages = [{"role": "system", "content": "base"}, {"role": "user", "content": "payload"}]
    error = ValueError("audience contains banned pattern: 特别是那些")

    retry_messages = _with_retry_instruction(messages, error)

    assert retry_messages[0]["content"].startswith("base")
    assert "上一次输出没有通过字段校验" in retry_messages[0]["content"]
    assert "特别是那些" in retry_messages[0]["content"]
    assert retry_messages[1] == messages[1]
    assert _should_retry_generation_error(error)
    assert _should_retry_generation_error(ValueError("thesis is empty"))
    assert not _should_retry_generation_error(ValueError("unrelated failure"))
