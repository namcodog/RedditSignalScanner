from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _item(lane: str, age_hours: float, *, idx: int) -> dict:
    now = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    event_at = now - timedelta(hours=age_hours)
    return {
        "plan_key": f"{lane}-{idx}",
        "lane": lane,
        "title": f"{lane}-{idx}",
        "topic_pack_id": "pack",
        "source_event_at": event_at.isoformat().replace("+00:00", "Z"),
    }


def test_freshness_gate_rewrites_when_hot_exceeds_max(monkeypatch) -> None:
    from app.services.hotpost import intake_freshness_gate as mod

    generated_at = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {
        "generated_at": generated_at,
        "publish_list": [
            *[_item("signal", 12, idx=i) for i in range(9)],
            *[_item("hot", 12 if i < 3 else 92, idx=i) for i in range(4)],
            *[_item("breakdown", 24, idx=i) for i in range(2)],
        ],
    }

    monkeypatch.setattr(
        mod,
        "_load_candidate_freshness_by_lane",
        lambda _reference: {
            "hot": {"total": 8, "target_fresh": 6, "acceptable_fresh": 8, "stale": 0, "target_fresh_ratio": 0.75},
            "signal": {"total": 20, "target_fresh": 18, "acceptable_fresh": 20, "stale": 0, "target_fresh_ratio": 0.9},
            "breakdown": {"total": 6, "target_fresh": 6, "acceptable_fresh": 6, "stale": 0, "target_fresh_ratio": 1.0},
        },
    )

    summary = mod.evaluate_publish_plan(payload, target_total=15)

    assert summary["decision"] == "rewrite"
    assert summary["rewrite_reasons"] == ["hot_over_age_limit"]
    assert summary["checks"]["hot_freshness_pass"] is False


def test_freshness_gate_publishes_when_all_lanes_are_fresh(monkeypatch) -> None:
    from app.services.hotpost import intake_freshness_gate as mod

    generated_at = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {
        "generated_at": generated_at,
        "publish_list": [
            *[_item("signal", 24, idx=i) for i in range(9)],
            *[_item("hot", 8, idx=i) for i in range(4)],
            *[_item("breakdown", 48, idx=i) for i in range(2)],
        ],
    }

    monkeypatch.setattr(
        mod,
        "_load_candidate_freshness_by_lane",
        lambda _reference: {
            "hot": {"total": 6, "target_fresh": 5, "acceptable_fresh": 6, "stale": 0, "target_fresh_ratio": 0.8333},
            "signal": {"total": 20, "target_fresh": 18, "acceptable_fresh": 20, "stale": 0, "target_fresh_ratio": 0.9},
            "breakdown": {"total": 6, "target_fresh": 6, "acceptable_fresh": 6, "stale": 0, "target_fresh_ratio": 1.0},
        },
    )

    summary = mod.evaluate_publish_plan(payload, target_total=15)

    assert summary["decision"] == "publish"
    assert summary["rewrite_reasons"] == []
    assert summary["fail_reasons"] == []
    assert summary["window_target_met"] is True


def test_freshness_gate_no_longer_fails_just_because_window_not_full(monkeypatch) -> None:
    from app.services.hotpost import intake_freshness_gate as mod

    generated_at = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {
        "generated_at": generated_at,
        "publish_list": [
            *[_item("signal", 24, idx=i) for i in range(4)],
            *[_item("hot", 8, idx=i) for i in range(2)],
        ],
        "topic_tree_governance": {"overall_decision": "rewrite"},
    }

    monkeypatch.setattr(
        mod,
        "_load_candidate_freshness_by_lane",
        lambda _reference: {
            "hot": {"total": 2, "target_fresh": 2, "acceptable_fresh": 2, "stale": 0, "target_fresh_ratio": 1.0},
            "signal": {"total": 4, "target_fresh": 4, "acceptable_fresh": 4, "stale": 0, "target_fresh_ratio": 1.0},
            "breakdown": {"total": 0, "target_fresh": 0, "acceptable_fresh": 0, "stale": 0, "target_fresh_ratio": 0.0},
        },
    )

    summary = mod.evaluate_publish_plan(payload, target_total=15)

    assert summary["decision"] == "publish"
    assert summary["fail_reasons"] == []
    assert summary["window_target_met"] is False
    assert summary["topic_tree_governance"]["overall_decision"] == "rewrite"


def test_freshness_gate_marks_yield_exhausted_when_publish_list_is_empty(monkeypatch) -> None:
    from app.services.hotpost import intake_freshness_gate as mod

    generated_at = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {
        "generated_at": generated_at,
        "publish_list": [],
    }

    monkeypatch.setattr(mod, "_load_candidate_freshness_by_lane", lambda _reference: {})

    summary = mod.evaluate_publish_plan(payload, target_total=15)

    assert summary["decision"] == "publish"
    assert summary["yield_exhausted"] is True
    assert summary["actual_total"] == 0
    assert summary["fail_reasons"] == []
    assert summary["rewrite_reasons"] == []
    assert summary["stale_ratio"] == 0.0


def test_named_topic_escalation_only_uses_actual_hot_gap() -> None:
    from app.services.hotpost.intake_freshness_gate import should_escalate_named_topic_collect

    assert (
        should_escalate_named_topic_collect(
            decision="rewrite",
            rewrite_reasons=["hot_over_age_limit"],
            fail_reasons=[],
            lane_counts={"hot": 2, "signal": 3},
            candidate_freshness_by_lane={"hot": {"acceptable_fresh": 1}},
        )
        is True
    )
    assert (
        should_escalate_named_topic_collect(
            decision="rewrite",
            rewrite_reasons=["signal_target_window_underfilled"],
            fail_reasons=[],
            lane_counts={"hot": 0, "signal": 3},
            candidate_freshness_by_lane={"hot": {"acceptable_fresh": 0}},
        )
        is False
    )


def test_freshness_gate_recommended_plan_command_uses_runtime_target_total(monkeypatch) -> None:
    from app.services.hotpost import intake_freshness_gate as mod

    generated_at = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {
        "generated_at": generated_at,
        "scope": "business-growth-ops",
        "publish_list": [
            *[_item("signal", 24, idx=i) for i in range(4)],
            _item("hot", 8, idx=0),
            _item("hot", 96, idx=1),
        ],
    }

    monkeypatch.setattr(
        mod,
        "_load_candidate_freshness_by_lane",
        lambda _reference: {
            "hot": {"total": 2, "target_fresh": 1, "acceptable_fresh": 1, "stale": 1, "target_fresh_ratio": 0.5},
            "signal": {"total": 4, "target_fresh": 4, "acceptable_fresh": 4, "stale": 0, "target_fresh_ratio": 1.0},
        },
    )

    summary = mod.evaluate_publish_plan(payload, target_total=10)

    assert summary["decision"] == "rewrite"
    assert any("--limit 10 --scope business-growth-ops" in command for command in summary["recommended_actions"])
