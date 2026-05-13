from __future__ import annotations

import pytest


pytestmark = pytest.mark.asyncio


async def test_run_quota_aware_collect_stops_after_three_dry_cycles(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.hotpost import quota_aware_collect_runner as mod

    class _Scope:
        def __init__(self, source_scope_id: str) -> None:
            self.source_scope_id = source_scope_id

    states = [
        {"publishable_total": 1},
        {"publishable_total": 2},
        {"publishable_total": 2},
        {"publishable_total": 2},
        {"publishable_total": 2},
    ]

    monkeypatch.setattr(mod, "get_supply_collect_profile", lambda mode: {"max_candidates_per_scope": 8, "dry_cycle": 3})
    monkeypatch.setattr(mod, "list_source_scopes", lambda: [_Scope("business-growth-ops")])
    async def _fake_collect(*args, **kwargs):
        return {
            "items": [],
            "phase_summaries": [{"phase": "discover"}, {"phase": "enrich"}, {"phase": "backfill"}],
            "collect_stats": {"primary_post_requests": 2, "comment_assist_hits": 1},
            "shortlist_size": 0,
            "secondary_discover_assist_enabled": False,
        }

    monkeypatch.setattr(mod, "collect_scope_candidates_with_summary", _fake_collect)
    monkeypatch.setattr(mod, "measure_publishable_gain", lambda source_scope_id=None: states.pop(0))

    summary = await mod.run_quota_aware_collect(scope=None, mode="safe")

    assert summary["winner"] == "discover_first_comment_late_adaptive_pacing_sociavault_assist_v3"
    assert summary["phase_order"] == ["discover", "enrich", "backfill"]
    assert summary["dry_cycle_limit"] == 3
    assert len(summary["cycles"]) == 4
    assert summary["cycles"][-1]["dry_cycles"] == 3
    assert summary["collect_stats_total"]["primary_post_requests"] == 8
    assert summary["providers"]["post_discovery"] == "reddit_api_primary"
    assert summary["stopped_by"] == "yield_exhaustion"


async def test_run_quota_aware_collect_waits_longer_between_dry_cycles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import quota_aware_collect_runner as mod

    class _Scope:
        def __init__(self, source_scope_id: str) -> None:
            self.source_scope_id = source_scope_id

    states = [
        {"publishable_total": 1},
        {"publishable_total": 1},
        {"publishable_total": 1},
        {"publishable_total": 1},
    ]
    sleeps: list[float] = []

    async def _fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    async def _fake_collect(*args, **kwargs):
        return {
            "items": [],
            "phase_summaries": [{"phase": "discover"}, {"phase": "enrich"}, {"phase": "backfill"}],
            "collect_stats": {},
            "shortlist_size": 0,
            "secondary_discover_assist_enabled": False,
        }

    monkeypatch.setattr(
        mod,
        "get_supply_collect_profile",
        lambda mode: {"max_candidates_per_scope": 8, "dry_cycle": 3, "low_quota_cooldown_seconds": 20},
    )
    monkeypatch.setattr(mod, "list_source_scopes", lambda: [_Scope("business-growth-ops")])
    monkeypatch.setattr(mod, "collect_scope_candidates_with_summary", _fake_collect)
    monkeypatch.setattr(mod, "measure_publishable_gain", lambda source_scope_id=None: states.pop(0))
    monkeypatch.setattr(mod.asyncio, "sleep", _fake_sleep)

    summary = await mod.run_quota_aware_collect(scope="business-growth-ops", mode="safe")

    assert [row["sleep_seconds_before_next_cycle"] for row in summary["cycles"]] == [20.0, 40.0, 0.0]
    assert sleeps == [20.0, 40.0]


async def test_run_quota_aware_collect_enables_secondary_discover_assist_after_two_dry_cycles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.hotpost import quota_aware_collect_runner as mod

    class _Scope:
        def __init__(self, source_scope_id: str) -> None:
            self.source_scope_id = source_scope_id

    states = [
        {"publishable_total": 1},
        {"publishable_total": 1},
        {"publishable_total": 1},
        {"publishable_total": 1},
    ]
    seen_assist_flags: list[bool] = []

    async def _fake_sleep(seconds: float) -> None:
        return None

    async def _fake_collect(*args, **kwargs):
        seen_assist_flags.append(bool(kwargs.get("enable_secondary_discover_assist")))
        return {
            "items": [],
            "phase_summaries": [
                {
                    "phase": "discover",
                    "spec_count": 4,
                    "collect_stats": {"primary_post_requests": 2, "fallback_post_requests": 0},
                },
                {"phase": "enrich", "spec_count": 0, "collect_stats": {}},
                {"phase": "backfill", "spec_count": 0, "collect_stats": {}},
            ],
            "collect_stats": {"primary_post_requests": 2},
            "shortlist_size": 0,
            "secondary_discover_assist_enabled": bool(kwargs.get("enable_secondary_discover_assist")),
        }

    monkeypatch.setattr(
        mod,
        "get_supply_collect_profile",
        lambda mode: {"max_candidates_per_scope": 8, "dry_cycle": 3, "low_quota_cooldown_seconds": 20},
    )
    monkeypatch.setattr(mod, "list_source_scopes", lambda: [_Scope("business-growth-ops")])
    monkeypatch.setattr(mod, "collect_scope_candidates_with_summary", _fake_collect)
    monkeypatch.setattr(mod, "measure_publishable_gain", lambda source_scope_id=None: states.pop(0))
    monkeypatch.setattr(mod.asyncio, "sleep", _fake_sleep)

    summary = await mod.run_quota_aware_collect(scope="business-growth-ops", mode="safe")

    assert seen_assist_flags == [False, False, True]
    assert summary["cycles"][1]["next_cycle_secondary_discover_assist_scopes"] == ["business-growth-ops"]
    assert summary["cycles"][2]["scope_summaries"]["business-growth-ops"]["secondary_discover_assist_enabled"] is True
