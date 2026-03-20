from app.services.report.render_bundle import (
    ControlledMarkdownResult,
    build_metrics_summary,
    build_report_render_bundle,
)


def test_build_metrics_summary_ignores_bad_layer_entries() -> None:
    summary = build_metrics_summary(
        {
            "entity_coverage": {
                "overall": 0.8,
                "brands": 0.6,
                "pain_points": 0.7,
                "top10_unique_share": 0.4,
            },
            "layer_coverage": [
                {"layer": "brands", "posts": 10, "hit_posts": 6, "coverage": 0.6},
                {"layer": "bad", "posts": "oops"},
            ],
        }
    )

    assert summary is not None
    assert summary.overall == 0.8
    assert len(summary.layers) == 1
    assert summary.layers[0].layer == "brands"


def test_build_report_render_bundle_renders_controlled_html_when_missing_base_html() -> None:
    bundle = build_report_render_bundle(
        base_report_html=None,
        controlled_result=ControlledMarkdownResult(
            markdown="# Controlled",
            metrics_data={},
            llm_used=True,
            source="executive_summary",
        ),
        blocked_by_quality_gate=False,
        market_enhancements=None,
    )

    assert bundle.report_html is not None
    assert "Controlled" in bundle.report_html
    assert bundle.llm_used is True
    assert bundle.controlled_md_source == "executive_summary"


def test_build_report_render_bundle_marks_community_market_mode() -> None:
    bundle = build_report_render_bundle(
        base_report_html=None,
        controlled_result=ControlledMarkdownResult(
            markdown="community market body",
            metrics_data={},
            llm_used=False,
            source="community_market",
        ),
        blocked_by_quality_gate=False,
        market_enhancements={"personas": []},
    )

    assert bundle.market_enhancements is not None
    assert bundle.market_enhancements["mode"] == "community_market"
    assert bundle.market_enhancements["personas"] == []
