from __future__ import annotations

from app.services.hotpost.remediation import build_hotpost_remediation_plan


def test_build_hotpost_remediation_plan_expands_query_parts_and_subreddits() -> None:
    plan = build_hotpost_remediation_plan(
        mode="rant",
        search_query="robot vacuum",
        base_query_parts=["robot vacuum"],
        base_subreddits=["r/robotvacuums"],
        gaps=["missing_pain_points", "missing_pain_voice"],
    )

    assert plan is not None
    assert plan.query_parts[0] == "robot vacuum"
    assert len(plan.query_parts) > 1
    assert "r/robotvacuums" in plan.subreddits
    assert plan.added_terms
    assert any("自动补证" in note for note in plan.notes)


def test_build_hotpost_remediation_plan_returns_none_without_gaps() -> None:
    plan = build_hotpost_remediation_plan(
        mode="trending",
        search_query="creator economy",
        base_query_parts=["creator economy"],
        base_subreddits=[],
        gaps=[],
    )

    assert plan is None
