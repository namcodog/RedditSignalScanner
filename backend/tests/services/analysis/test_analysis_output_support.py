from __future__ import annotations

from app.services.analysis.analysis_output_support import (
    build_analysis_output_artifacts,
    build_knowledge_graph,
)


def test_build_knowledge_graph_keeps_evidence_and_driver_links() -> None:
    payload = build_knowledge_graph(
        aggregates={"communities": [{"name": "r/paypal", "posts": 3, "comments": 2}]},
        high_value_pains=[
            {
                "name": "回款延迟与冻结",
                "mentions": 5,
                "unique_authors": 2,
                "evidence_quote_ids": ["c1", "p1"],
            }
        ],
        sample_posts_db=[
            {
                "id": "p1",
                "title": "Payout delay issue",
                "permalink": "https://reddit.com/p1",
                "subreddit": "r/paypal",
            }
        ],
        sample_comments_db=[
            {
                "id": "c1",
                "body": "Still waiting for balance",
                "permalink": "https://reddit.com/c1",
                "subreddit": "r/paypal",
            }
        ],
        top_drivers=[
            {
                "title": "回款拖延",
                "description": "到账慢影响资金周转",
                "actions": ["继续看证据"],
                "source_pains": ["回款延迟与冻结"],
            }
        ],
    )

    assert payload["communities"][0]["name"] == "r/paypal"
    assert payload["pain_points"][0]["evidence_ids"] == ["c1", "p1"]
    assert payload["pain_points"][0]["evidence"][0]["type"] == "comment"
    assert payload["drivers"][0]["source_pains"] == ["回款延迟与冻结"]


def test_build_analysis_output_artifacts_wires_ledger_slice_and_graph() -> None:
    captured: dict[str, object] = {}

    def fake_build_ledger(*, insights, sample_posts_db, sample_comments_db):
        captured["ledger_inputs"] = {
            "insights": insights,
            "posts": sample_posts_db,
            "comments": sample_comments_db,
        }
        return {"pain_points": [{"id": "pain-1"}]}

    def fake_build_slice(
        *,
        facts_v2_package,
        facts_v2_quality,
        trend_summary,
        market_saturation,
        battlefield_profiles,
        top_drivers,
    ):
        captured["slice_inputs"] = {
            "facts_v2_quality": facts_v2_quality,
            "trend_summary": trend_summary,
            "market_saturation": market_saturation,
            "battlefield_profiles": battlefield_profiles,
            "top_drivers": top_drivers,
        }
        return {"trend_summary": trend_summary}

    facts_v2_package = {"schema_version": "2.0"}
    artifacts = build_analysis_output_artifacts(
        facts_v2_package=facts_v2_package,
        facts_v2_quality={"tier": "A_full"},
        insights={
            "trend_summary": {"label": "hot"},
            "market_saturation": [{"level": "medium"}],
            "battlefield_profiles": [{"community": "r/paypal"}],
            "top_drivers": [{"title": "回款拖延"}],
        },
        ps_ratio_value=0.124,
        aggregates={"communities": [{"name": "r/paypal", "posts": 3, "comments": 0}]},
        high_value_pains=[
            {
                "description": "回款延迟与冻结",
                "mentions": 5,
                "unique_authors": 2,
                "evidence_quote_ids": ["p1"],
            }
        ],
        sample_posts_db=[{"id": "p1", "title": "Payout delay", "subreddit": "r/paypal"}],
        sample_comments_db=[],
        build_evidence_ledger_fn=fake_build_ledger,
        build_facts_slice_for_report_fn=fake_build_slice,
    )

    assert facts_v2_package["evidence_ledger"] == {"pain_points": [{"id": "pain-1"}]}
    assert artifacts.evidence_ledger == {"pain_points": [{"id": "pain-1"}]}
    assert artifacts.facts_slice["ps_ratio"] == 0.12
    assert artifacts.facts_slice["knowledge_graph"]["pain_points"][0]["name"] == "回款延迟与冻结"
    assert captured["slice_inputs"] == {
        "facts_v2_quality": {"tier": "A_full"},
        "trend_summary": {"label": "hot"},
        "market_saturation": [{"level": "medium"}],
        "battlefield_profiles": [{"community": "r/paypal"}],
        "top_drivers": [{"title": "回款拖延"}],
    }


def test_build_analysis_output_artifacts_handles_missing_package() -> None:
    artifacts = build_analysis_output_artifacts(
        facts_v2_package=None,
        facts_v2_quality=None,
        insights=None,
        ps_ratio_value=None,
        aggregates=None,
        high_value_pains=[],
        sample_posts_db=[],
        sample_comments_db=[],
        build_evidence_ledger_fn=lambda **_: {"unexpected": True},
        build_facts_slice_for_report_fn=lambda **_: {"unexpected": True},
    )

    assert artifacts.evidence_ledger is None
    assert artifacts.facts_slice is None
    assert artifacts.knowledge_graph is None
