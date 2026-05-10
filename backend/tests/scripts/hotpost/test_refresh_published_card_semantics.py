from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "hotpost" / "refresh_published_card_semantics.py"
SPEC = importlib.util.spec_from_file_location("refresh_published_card_semantics_script", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
refresh_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refresh_module)


def test_dry_run_can_write_exact_apply_plan(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original = _published_card("card-1")

    monkeypatch.setattr(refresh_module, "load_published_cards", lambda: [original])
    monkeypatch.setattr(refresh_module, "merge_published_cards", lambda cards: 0)
    monkeypatch.setattr(
        refresh_module,
        "refresh_published_card_semantics",
        _async_return(
            {
                **original,
                "title": "新版标题",
                "summary_line": "新版摘要",
                "detail": {
                    **original["detail"],
                    "why_test_now": "新版证据判断",
                },
            }
        ),
    )

    plan_path = tmp_path / "semantic-refresh-plan.json"
    args = refresh_module.parse_args(["--card-id", "card-1", "--output-plan", str(plan_path), "--json"])

    result = asyncio.run(refresh_module.run(args))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    assert result["mode"] == "dry_run"
    assert result["merged"] == 0
    assert result["output_plan"] == str(plan_path)
    assert plan["plan_version"] == 1
    assert plan["kind"] == "published_card_semantic_refresh"
    assert plan["selected"] == 1
    assert plan["cards"][0]["card_id"] == "card-1"
    assert plan["cards"][0]["refreshed_card"]["title"] == "新版标题"
    assert plan["cards"][0]["changed"]["title"]["after"] == "新版标题"


def test_apply_plan_merges_exact_payload_without_regenerating(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    refreshed = {
        **_published_card("card-2"),
        "title": "按计划写回的标题",
        "summary_line": "按计划写回的摘要",
    }
    plan_path = tmp_path / "semantic-refresh-plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "plan_version": 1,
                "kind": "published_card_semantic_refresh",
                "created_at": "2026-04-11T01:30:00Z",
                "selected": 1,
                "cards": [
                    {
                        "card_id": "card-2",
                        "lane": "signal",
                        "card_type": "validate",
                        "changed": {"title": {"before": "旧标题", "after": "按计划写回的标题"}},
                        "refreshed_card": refreshed,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    merged_cards: list[dict] = []

    monkeypatch.setattr(refresh_module, "load_published_cards", _boom("apply-plan should not read published cards"))
    monkeypatch.setattr(
        refresh_module,
        "refresh_published_card_semantics",
        _async_raise("apply-plan should not call LLM refresh"),
    )
    monkeypatch.setattr(refresh_module, "merge_published_cards", lambda cards: merged_cards.extend(cards) or len(cards))

    args = refresh_module.parse_args(["--apply-plan", str(plan_path), "--json"])
    result = asyncio.run(refresh_module.run(args))

    assert result["mode"] == "apply_plan"
    assert result["selected"] == 1
    assert result["merged"] == 1
    assert merged_cards == [refreshed]


def test_apply_plan_rejects_live_selectors(tmp_path: Path) -> None:
    plan_path = tmp_path / "semantic-refresh-plan.json"
    plan_path.write_text("{}", encoding="utf-8")
    args = refresh_module.parse_args(["--apply-plan", str(plan_path), "--lane", "signal"])

    with pytest.raises(ValueError, match="--apply-plan cannot be combined"):
        asyncio.run(refresh_module.run(args))


def test_workers_must_be_positive() -> None:
    args = refresh_module.parse_args(["--card-id", "card-1", "--workers", "0"])

    with pytest.raises(ValueError, match="--workers must be greater than 0"):
        asyncio.run(refresh_module.run(args))


def test_refresh_cards_keeps_selection_order_under_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    cards = [_published_card("card-1"), _published_card("card-2"), _published_card("card-3")]

    async def _fake_refresh(item: dict) -> dict:
        delays = {"card-1": 0.03, "card-2": 0.01, "card-3": 0.02}
        await asyncio.sleep(delays[item["card_id"]])
        return {**item, "title": f"refreshed-{item['card_id']}"}

    monkeypatch.setattr(refresh_module, "refresh_published_card_semantics", _fake_refresh)

    refreshed = asyncio.run(refresh_module._refresh_cards(cards, workers=3))

    assert [item["card_id"] for item in refreshed] == ["card-1", "card-2", "card-3"]
    assert [item["title"] for item in refreshed] == [
        "refreshed-card-1",
        "refreshed-card-2",
        "refreshed-card-3",
    ]


def _published_card(card_id: str) -> dict:
    return {
        "card_id": card_id,
        "signal_id": f"sig-{card_id}",
        "card_type": "validate",
        "lane": "signal",
        "category_id": "validate",
        "title": "旧标题",
        "summary_line": "旧摘要",
        "audience": "旧读者",
        "why_now": "旧为什么现在看",
        "preview_quote": {"text": "quote one", "community": "r/test", "permalink": "https://reddit.test/q1"},
        "quotes": [{"text": "quote one", "community": "r/test", "permalink": "https://reddit.test/q1"}],
        "detail": {
            "pain_point": "旧痛点",
            "target_user_and_scene": "旧场景",
            "why_test_now": "旧证据判断",
            "continue_signal": "旧继续观察",
            "stop_signal": "旧停止条件",
        },
    }


def _async_return(result: dict):
    async def _runner(_: dict) -> dict:
        return result

    return _runner


def _async_raise(message: str):
    async def _runner(_: dict) -> dict:
        raise AssertionError(message)

    return _runner


def _boom(message: str):
    def _runner():
        raise AssertionError(message)

    return _runner
