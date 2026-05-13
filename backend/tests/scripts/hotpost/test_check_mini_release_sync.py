from __future__ import annotations

import json
import pytest
import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "hotpost" / "check_mini_release_sync.py"
SPEC = importlib.util.spec_from_file_location("check_mini_release_sync", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
sync_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync_module)


def test_expected_feed_contract_comes_from_supply_yaml() -> None:
    assert sync_module._expected_feed_contract() == {"initial_page_size": 30, "max_page_size": 30}


def test_feed_contract_requires_both_page_sizes() -> None:
    assert sync_module._feed_contract({"feed_contract": {"initial_page_size": 30, "max_page_size": 30}}) == {
        "initial_page_size": 30,
        "max_page_size": 30,
    }
    assert sync_module._feed_contract({"feed_contract": {"initial_page_size": 30}}) is None
    assert sync_module._feed_contract({}) is None


def test_feed_contract_rejects_non_numeric_values() -> None:
    with pytest.raises(ValueError):
        sync_module._feed_contract({"feed_contract": {"initial_page_size": "bad", "max_page_size": 30}})


def test_hot_controversy_guard_requires_chart_and_meta() -> None:
    cards = [
        {
            "card_id": "card-hot-ok",
            "lane": "hot",
            "card_type": "validate",
            "controversy_chart": {"debate_focus": "焦点"},
            "controversy_meta": {"summary_status": "ok"},
        },
        {
            "card_id": "card-hot-missing",
            "lane": "hot",
            "card_type": "validate",
            "controversy_chart": None,
            "controversy_meta": None,
        },
        {
            "card_id": "card-breakdown",
            "lane": "breakdown",
            "card_type": "write",
            "controversy_chart": None,
            "controversy_meta": None,
        },
    ]

    violations = sync_module._hot_controversy_violations(cards)

    assert violations == [
        "card-hot-missing: hot validate card missing controversy_chart",
        "card-hot-missing: hot validate card missing controversy_meta",
    ]


def test_trend_audit_guard_requires_latest_release_match(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    trend_path = tmp_path / "mini-release-trend-audit-latest.json"
    trend_path.write_text(
        json.dumps(
            {
                "latest_release_id": "release-new",
                "latest_status": "watching",
                "stable_streak": 0,
                "remaining_new_releases": 5,
                "latest_remediation_focus": "inventory_only",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(sync_module, "TREND_AUDIT_PATH", trend_path)

    assert sync_module._trend_audit_violations(expected_release_id="release-new") == []
    assert sync_module._trend_audit_violations(expected_release_id="release-old") == [
        "trend audit release mismatch: expected release-old, got release-new",
    ]
