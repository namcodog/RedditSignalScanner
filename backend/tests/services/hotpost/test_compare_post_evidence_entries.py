from __future__ import annotations

from types import SimpleNamespace

from app.services.hotpost.compare_targets import infer_compare_targets
from app.services.hotpost.rant_evidence_cards import collect_rant_evidence_units
from app.services.hotpost.rant_evidence_metrics import build_rant_evidence_metrics


def _comment(*, idx: int, body: str, score: int = 10) -> SimpleNamespace:
    return SimpleNamespace(
        body=body,
        score=score,
        permalink=f"https://reddit.com/r/test/comments/{idx}",
        comment_fullname=f"t1_{idx}",
    )


def _post(
    *,
    idx: int,
    title: str,
    body_preview: str = "",
    top_comments: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=f"t3_{idx}",
        title=title,
        body_preview=body_preview,
        reddit_url=f"https://reddit.com/r/test/{idx}",
        subreddit="r/LocalLLaMA",
        created_utc=0,
        score=100 - idx,
        top_comments=list(top_comments or []),
    )


def test_collect_rant_evidence_units_accepts_compare_post_voice_without_comments() -> None:
    payload = {
        "top_posts": [
            _post(idx=1, title="I prefer Linear over Jira for project management"),
        ],
        "top_quotes": [],
        "pain_points": [],
    }

    units = collect_rant_evidence_units(
        payload,
        complaint_facets=[],
        query="为什么团队现在在项目管理上更偏向 Linear 而不是 Jira",
        keywords=["Linear", "Jira", "项目管理"],
        query_family="comparison_complaint_discovery",
    )

    valid_units = [unit for unit in units if unit.get("valid")]
    assert valid_units
    assert any(unit.get("source_type") == "post" for unit in valid_units)
    assert any(unit.get("side") == "Linear" for unit in valid_units)


def test_build_rant_evidence_metrics_uses_post_voice_for_compare_counts() -> None:
    payload = {
        "top_posts": [
            _post(idx=1, title="I prefer Linear over Jira for project management"),
            _post(idx=2, title="Linear is better than Jira for project management"),
            _post(idx=3, title="Jira is worse than Linear for project management"),
        ],
        "top_quotes": [],
        "pain_points": [],
    }

    metrics = build_rant_evidence_metrics(
        payload,
        complaint_facets=[],
        query="为什么团队现在在项目管理上更偏向 Linear 而不是 Jira",
        keywords=["Linear", "Jira", "项目管理"],
        query_family="comparison_complaint_discovery",
    )

    assert metrics["valid_evidence_cards"] > 0
    assert metrics["compare_left_count"] > 0
    assert metrics["compare_right_count"] > 0
    assert "project management" in metrics["focus_bundle_hits"]


def test_collect_rant_evidence_units_resolves_comment_side_from_thread_frame() -> None:
    payload = {
        "top_posts": [
            _post(
                idx=1,
                title="Why Linear is better than Jira for project management",
                top_comments=[
                    _comment(
                        idx=1,
                        body="Same here, much better for our team once the board gets busy.",
                    )
                ],
            ),
        ],
        "top_quotes": [],
        "pain_points": [],
    }

    units = collect_rant_evidence_units(
        payload,
        complaint_facets=[],
        query="为什么团队现在在项目管理上更偏向 Linear 而不是 Jira",
        keywords=["Linear", "Jira", "项目管理"],
        query_family="comparison_complaint_discovery",
    )

    rescued_comment_units = [
        unit
        for unit in units
        if unit.get("valid")
        and unit.get("source_type") == "comment"
        and unit.get("side_resolution_source") == "thread_frame"
    ]

    assert rescued_comment_units
    assert any(unit.get("focus_resolution_source") == "thread_frame" for unit in rescued_comment_units)
    assert any(unit.get("side") == "Linear" for unit in rescued_comment_units)


def test_build_rant_evidence_metrics_reports_thread_frame_resolution_sources() -> None:
    payload = {
        "top_posts": [
            _post(
                idx=1,
                title="Why Linear is better than Jira for project management",
                top_comments=[
                    _comment(
                        idx=1,
                        body="Same here, much better for our team once the board gets busy.",
                    )
                ],
            ),
            _post(idx=2, title="Linear is better than Jira for project management"),
            _post(idx=3, title="Jira is worse than Linear for project management"),
        ],
        "top_quotes": [],
        "pain_points": [],
    }

    metrics = build_rant_evidence_metrics(
        payload,
        complaint_facets=[],
        query="为什么团队现在在项目管理上更偏向 Linear 而不是 Jira",
        keywords=["Linear", "Jira", "项目管理"],
        query_family="comparison_complaint_discovery",
    )

    assert metrics["side_resolution_sources"]["thread_frame"] >= 1
    assert metrics["focus_resolution_sources"]["thread_frame"] >= 1


def test_infer_compare_targets_prefers_entities_over_scenario_terms() -> None:
    targets = infer_compare_targets(
        "为什么团队现在在项目管理上更偏向 Linear 而不是 Jira",
        ["Linear", "Jira", "项目管理"],
    )

    assert targets == ["Linear", "Jira"]
