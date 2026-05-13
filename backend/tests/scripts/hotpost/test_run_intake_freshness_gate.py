from __future__ import annotations

import asyncio
from pathlib import Path

from app.scripts_support.env_loader import load_backend_env


def test_run_intake_freshness_gate_collects_all_scope_by_default(tmp_path: Path, monkeypatch) -> None:
    load_backend_env()
    import scripts.hotpost.run_intake_freshness_gate as mod

    sync_calls: list[str] = []
    collect_calls: list[tuple[str, str | None]] = []

    monkeypatch.setattr(mod, "sync_topic_metadata", lambda: sync_calls.append("sync") or {"changed": 0})
    monkeypatch.setattr(
        mod,
        "_run_daily_collect",
        lambda mode, scope: collect_calls.append((mode, scope)) or asyncio.sleep(0, result={"all": 2}),
    )
    monkeypatch.setattr(mod, "_run_named_topic_collect", lambda mode: asyncio.sleep(0, result={"watch_count": 0, "candidate_count": 0}))
    monkeypatch.setattr(
        mod,
        "build_offline_publish_plan",
        lambda limit, scope=None: {
            "generated_at": "2026-04-13T12:05:00Z",
            "scope": scope,
            "publish_list": [{"lane": "signal"}] * 9 + [{"lane": "hot"}] * 4 + [{"lane": "breakdown"}] * 2,
            "topic_tree_governance": {"overall_decision": "publish"},
        },
    )
    monkeypatch.setattr(
        mod,
        "evaluate_publish_plan",
        lambda payload, target_total: {"decision": "publish", "lane_targets": {"hot": 4}, "candidate_freshness_by_lane": {"hot": {"target_fresh": 4}}},
    )

    args = type(
        "Args",
        (),
        {
            "limit": 15,
            "scope": None,
            "all_scope": False,
            "output_plan": tmp_path / "plan.json",
            "summary_json": None,
            "collect_mode": "safe",
            "no_collect": False,
            "no_named_topics": False,
        },
    )()

    summary = asyncio.run(mod._run(args))

    assert collect_calls == [("safe", None)]
    assert summary["scope"] is None
    assert summary["initial"]["decision"] == "publish"
    assert summary["final"]["decision"] == "publish"
    assert summary["triggered_actions"] == ["daily_collect"]
    assert [item["step"] for item in summary["sync_runs"]] == ["post_collect_sync"]
    assert len(sync_calls) == 1


def test_run_intake_freshness_gate_scope_flag_still_allows_local_repair(tmp_path: Path, monkeypatch) -> None:
    load_backend_env()
    import scripts.hotpost.run_intake_freshness_gate as mod

    collect_calls: list[tuple[str, str | None]] = []

    monkeypatch.setattr(mod, "sync_topic_metadata", lambda: {"changed": 0})
    monkeypatch.setattr(
        mod,
        "_run_daily_collect",
        lambda mode, scope: collect_calls.append((mode, scope)) or asyncio.sleep(0, result={"business-growth-ops": 3}),
    )
    monkeypatch.setattr(
        mod,
        "build_offline_publish_plan",
        lambda limit, scope=None: {"generated_at": "2026-04-13T12:05:00Z", "scope": scope, "publish_list": [], "topic_tree_governance": {"overall_decision": "publish"}},
    )
    monkeypatch.setattr(
        mod,
        "evaluate_publish_plan",
        lambda payload, target_total: {"decision": "publish", "lane_targets": {}, "candidate_freshness_by_lane": {}},
    )

    args = type(
        "Args",
        (),
        {
            "limit": 15,
            "scope": "business-growth-ops",
            "all_scope": False,
            "output_plan": tmp_path / "plan.json",
            "summary_json": None,
            "collect_mode": "safe",
            "no_collect": False,
            "no_named_topics": False,
        },
    )()

    summary = asyncio.run(mod._run(args))

    assert collect_calls == [("safe", "business-growth-ops")]
    assert summary["scope"] == "business-growth-ops"


def test_run_intake_freshness_gate_does_not_trigger_named_topics_from_old_hot_target(tmp_path: Path, monkeypatch) -> None:
    load_backend_env()
    import scripts.hotpost.run_intake_freshness_gate as mod

    named_topic_calls: list[str] = []

    monkeypatch.setattr(mod, "sync_topic_metadata", lambda: {"changed": 0})
    monkeypatch.setattr(
        mod,
        "_run_daily_collect",
        lambda mode, scope: asyncio.sleep(0, result={"business-growth-ops": 1}),
    )
    monkeypatch.setattr(
        mod,
        "_run_named_topic_collect",
        lambda mode: named_topic_calls.append(mode) or asyncio.sleep(0, result={"watch_count": 1, "candidate_count": 1}),
    )
    monkeypatch.setattr(
        mod,
        "build_offline_publish_plan",
        lambda limit, scope=None: {
            "generated_at": "2026-04-13T12:05:00Z",
            "scope": scope,
            "publish_list": [{"lane": "signal"}] * 3,
            "topic_tree_governance": {"overall_decision": "rewrite"},
        },
    )
    monkeypatch.setattr(
        mod,
        "evaluate_publish_plan",
        lambda payload, target_total: {
            "decision": "rewrite",
            "rewrite_reasons": ["signal_target_window_underfilled"],
            "fail_reasons": [],
            "lane_counts": {"hot": 0, "signal": 3},
            "candidate_freshness_by_lane": {"hot": {"acceptable_fresh": 0}},
        },
    )

    args = type(
        "Args",
        (),
        {
            "limit": 15,
            "scope": "business-growth-ops",
            "all_scope": False,
            "output_plan": tmp_path / "plan.json",
            "summary_json": None,
            "collect_mode": "safe",
            "no_collect": False,
            "no_named_topics": False,
        },
    )()

    summary = asyncio.run(mod._run(args))

    assert summary["final"]["decision"] == "rewrite"
    assert named_topic_calls == []


def test_run_intake_freshness_gate_triggers_governance_collect_after_publish(tmp_path: Path, monkeypatch) -> None:
    load_backend_env()
    import scripts.hotpost.run_intake_freshness_gate as mod

    governance_calls: list[tuple[str, int]] = []

    monkeypatch.setattr(mod, "sync_topic_metadata", lambda: {"changed": 0})
    monkeypatch.setattr(
        mod,
        "_run_daily_collect",
        lambda mode, scope: asyncio.sleep(0, result={"business-growth-ops": 1}),
    )
    monkeypatch.setattr(
        mod,
        "build_offline_publish_plan",
        lambda limit, scope=None: {
            "generated_at": "2026-04-13T12:05:00Z",
            "scope": scope,
            "publish_list": [{"lane": "signal", "plan_key": "candidate:1", "source_scope_id": "business-growth-ops"}],
            "topic_tree_governance": {"overall_decision": "rewrite", "scopes": {"business-growth-ops": {"overall_decision": "rewrite"}}},
        },
    )
    monkeypatch.setattr(
        mod,
        "evaluate_publish_plan",
        lambda payload, target_total: {
            "decision": "publish",
            "actual_total": 1,
            "rewrite_reasons": [],
            "fail_reasons": [],
            "lane_counts": {"signal": 1},
            "candidate_freshness_by_lane": {},
            "topic_tree_governance": {"scopes": {"business-growth-ops": {"overall_decision": "rewrite"}}},
        },
    )
    monkeypatch.setattr(
        mod,
        "build_governance_topic_watches_for_gate",
        lambda plan_payload, gate_summary, scope_id: [type("Watch", (), {"topic_id": "gov-1"})()],
    )
    monkeypatch.setattr(
        mod,
        "_run_named_topic_collect",
        lambda mode, watches=None: governance_calls.append((mode, len(list(watches or [])))) or asyncio.sleep(
            0,
            result={"watch_count": len(list(watches or [])), "candidate_count": 0, "candidate_ids": [], "topic_ids": ["gov-1"]},
        ),
    )

    args = type(
        "Args",
        (),
        {
            "limit": 15,
            "scope": "business-growth-ops",
            "all_scope": False,
            "output_plan": tmp_path / "plan.json",
            "summary_json": None,
            "collect_mode": "safe",
            "no_collect": False,
            "no_named_topics": False,
        },
    )()

    summary = asyncio.run(mod._run(args))

    assert governance_calls == [("safe", 1)]


def test_run_intake_freshness_gate_triggers_governance_collect_for_all_scope_publish(tmp_path: Path, monkeypatch) -> None:
    load_backend_env()
    import scripts.hotpost.run_intake_freshness_gate as mod

    governance_calls: list[tuple[str, int]] = []

    monkeypatch.setattr(mod, "sync_topic_metadata", lambda: {"changed": 0})
    monkeypatch.setattr(
        mod,
        "_run_daily_collect",
        lambda mode, scope: asyncio.sleep(0, result={"all": 3}),
    )
    monkeypatch.setattr(
        mod,
        "build_offline_publish_plan",
        lambda limit, scope=None: {
            "generated_at": "2026-04-13T12:05:00Z",
            "scope": scope,
            "publish_list": [{"lane": "signal", "plan_key": "candidate:1", "source_scope_id": "ai-automation"}],
            "topic_tree_governance": {
                "overall_decision": "rewrite",
                "scopes": {"ai-automation": {"overall_decision": "rewrite"}},
            },
        },
    )
    monkeypatch.setattr(
        mod,
        "evaluate_publish_plan",
        lambda payload, target_total: {
            "decision": "publish",
            "actual_total": 1,
            "rewrite_reasons": [],
            "fail_reasons": [],
            "lane_counts": {"signal": 1},
            "candidate_freshness_by_lane": {},
            "topic_tree_governance": {"scopes": {"ai-automation": {"overall_decision": "rewrite"}}},
        },
    )
    monkeypatch.setattr(
        mod,
        "build_governance_topic_watches_for_gate",
        lambda plan_payload, gate_summary, scope_id: [type("Watch", (), {"topic_id": "gov-all"})()],
    )
    monkeypatch.setattr(
        mod,
        "_run_named_topic_collect",
        lambda mode, watches=None: governance_calls.append((mode, len(list(watches or [])))) or asyncio.sleep(
            0,
            result={"watch_count": len(list(watches or [])), "candidate_count": 0, "candidate_ids": [], "topic_ids": ["gov-all"]},
        ),
    )

    args = type(
        "Args",
        (),
        {
            "limit": 15,
            "scope": None,
            "all_scope": False,
            "output_plan": tmp_path / "plan.json",
            "summary_json": None,
            "collect_mode": "safe",
            "no_collect": False,
            "no_named_topics": False,
        },
    )()

    summary = asyncio.run(mod._run(args))

    assert summary["scope"] is None
    assert governance_calls == [("safe", 1)]


def test_run_intake_freshness_gate_keeps_current_publish_when_governance_preview_rewrites(tmp_path: Path, monkeypatch) -> None:
    load_backend_env()
    import scripts.hotpost.run_intake_freshness_gate as mod

    eval_calls = iter(
        [
            {
                "decision": "publish",
                "actual_total": 2,
                "rewrite_reasons": [],
                "fail_reasons": [],
                "lane_counts": {"signal": 1, "hot": 1},
                "candidate_freshness_by_lane": {},
                "topic_tree_governance": {"scopes": {"ai-automation": {"overall_decision": "rewrite"}}},
            },
            {
                "decision": "rewrite",
                "actual_total": 15,
                "rewrite_reasons": ["hot_over_age_limit"],
                "fail_reasons": [],
                "lane_counts": {"signal": 9, "hot": 4, "breakdown": 2},
                "candidate_freshness_by_lane": {},
                "topic_tree_governance": {"scopes": {"ai-automation": {"overall_decision": "rewrite"}}},
            },
        ]
    )

    monkeypatch.setattr(mod, "sync_topic_metadata", lambda: {"changed": 0})
    monkeypatch.setattr(
        mod,
        "_run_daily_collect",
        lambda mode, scope: asyncio.sleep(0, result={"all": 1}),
    )
    monkeypatch.setattr(
        mod,
        "build_offline_publish_plan",
        lambda limit, scope=None: {
            "generated_at": "2026-04-13T12:05:00Z",
            "scope": scope,
            "publish_list": [{"lane": "signal", "plan_key": "candidate:1", "source_scope_id": "ai-automation"}],
            "topic_tree_governance": {"overall_decision": "rewrite", "scopes": {"ai-automation": {"overall_decision": "rewrite"}}},
        },
    )
    monkeypatch.setattr(mod, "evaluate_publish_plan", lambda payload, target_total: next(eval_calls))
    monkeypatch.setattr(
        mod,
        "build_governance_topic_watches_for_gate",
        lambda plan_payload, gate_summary, scope_id: [type("Watch", (), {"topic_id": "gov-all"})()],
    )
    monkeypatch.setattr(
        mod,
        "_run_named_topic_collect",
        lambda mode, watches=None: asyncio.sleep(
            0,
            result={"watch_count": len(list(watches or [])), "candidate_count": 1, "candidate_ids": ["cand-x"], "topic_ids": ["gov-all"]},
        ),
    )

    args = type(
        "Args",
        (),
        {
            "limit": 15,
            "scope": None,
            "all_scope": False,
            "output_plan": tmp_path / "plan.json",
            "summary_json": None,
            "collect_mode": "safe",
            "no_collect": False,
            "no_named_topics": False,
        },
    )()

    summary = asyncio.run(mod._run(args))

    assert summary["final"]["decision"] == "publish"
    assert summary["governance_preview"]["decision"] == "rewrite"
    assert summary["publish_ready"] is True
    assert summary["triggered_actions"] == ["daily_collect", "collect_governance_topics"]


def test_run_intake_freshness_gate_marks_not_publish_ready_when_yield_exhausted(tmp_path: Path, monkeypatch) -> None:
    load_backend_env()
    import scripts.hotpost.run_intake_freshness_gate as mod

    monkeypatch.setattr(mod, "sync_topic_metadata", lambda: {"changed": 0})
    monkeypatch.setattr(
        mod,
        "build_offline_publish_plan",
        lambda limit, scope=None: {
            "generated_at": "2026-04-13T12:05:00Z",
            "scope": scope,
            "publish_list": [],
            "topic_tree_governance": {"overall_decision": "publish"},
        },
    )
    monkeypatch.setattr(
        mod,
        "evaluate_publish_plan",
        lambda payload, target_total: {
            "decision": "publish",
            "actual_total": 0,
            "yield_exhausted": True,
            "rewrite_reasons": [],
            "fail_reasons": [],
            "lane_counts": {},
            "candidate_freshness_by_lane": {},
        },
    )

    args = type(
        "Args",
        (),
        {
            "limit": 15,
            "scope": None,
            "all_scope": False,
            "output_plan": tmp_path / "plan.json",
            "summary_json": None,
            "collect_mode": "safe",
            "no_collect": True,
            "no_named_topics": False,
        },
    )()

    summary = asyncio.run(mod._run(args))

    assert summary["final"]["yield_exhausted"] is True
    assert summary["publish_ready"] is False
