from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from app.schemas.analysis import AnalysisRead
from app.services.report.controlled_summary_workflow import (
    ControlledSummaryWorkflowDeps,
    render_controlled_summary_workflow,
)


def _build_analysis_payload() -> AnalysisRead:
    return AnalysisRead.model_validate(
        {
            "id": uuid4(),
            "task_id": uuid4(),
            "insights": {
                "pain_points": [],
                "competitors": [],
                "opportunities": [],
                "action_items": [],
                "entity_summary": {"brands": [], "features": [], "pain_points": []},
                "pain_clusters": [],
                "competitor_layers_summary": [],
                "channel_breakdown": [],
                "top_drivers": [],
                "market_saturation": [],
                "battlefield_profiles": [],
            },
            "sources": {
                "communities": ["r/example"],
                "communities_detail": [],
                "posts_analyzed": 1,
                "cache_hit_rate": 0.5,
                "product_description": "demo product",
            },
            "confidence_score": Decimal("0.8"),
            "analysis_version": "1.0",
            "created_at": datetime.now(timezone.utc),
        }
    )


def test_controlled_summary_workflow_renders_with_existing_files(
    monkeypatch,
    tmp_path: Path,
) -> None:
    lexicon_path = tmp_path / "lexicon.json"
    metrics_path = tmp_path / "metrics.json"
    template_dir = tmp_path / "backend" / "config" / "report_templates"
    template_dir.mkdir(parents=True)
    template_path = template_dir / "executive_summary_v2.md"

    lexicon_path.write_text(json.dumps({"brands": ["foo"]}), encoding="utf-8")
    metrics_path.write_text(
        json.dumps({"entity_coverage": {"overall": 0.8}}),
        encoding="utf-8",
    )
    template_path.write_text("# Demo Template", encoding="utf-8")

    monkeypatch.setenv("SEMANTIC_LEXICON_PATH", str(lexicon_path))
    monkeypatch.setenv("SEMANTIC_METRICS_PATH", str(metrics_path))
    monkeypatch.chdir(tmp_path)

    captured: dict[str, object] = {}

    def fake_build_context(analysis_dict, lex_data, metrics_data, *, task_id: str):
        captured["analysis_dict"] = analysis_dict
        captured["lex_data"] = lex_data
        captured["metrics_data"] = metrics_data
        captured["task_id"] = task_id
        return {"summary": "ok"}, {}

    def fake_render(template: str, context: dict[str, object]) -> str:
        captured["template"] = template
        captured["context"] = context
        return "# rendered"

    result = render_controlled_summary_workflow(
        analysis_payload=_build_analysis_payload(),
        task_id=uuid4(),
        blocked_by_quality_gate=False,
        deps=ControlledSummaryWorkflowDeps(
            build_context=fake_build_context,
            render_report=fake_render,
        ),
    )

    assert result.markdown == "# rendered"
    assert result.metrics_data == {"entity_coverage": {"overall": 0.8}}
    assert captured["lex_data"] == {"brands": ["foo"]}
    assert captured["template"] == "# Demo Template"
    assert captured["context"] == {"summary": "ok"}


def test_controlled_summary_workflow_short_circuits_when_blocked() -> None:
    result = render_controlled_summary_workflow(
        analysis_payload=_build_analysis_payload(),
        task_id=uuid4(),
        blocked_by_quality_gate=True,
        deps=ControlledSummaryWorkflowDeps(
            build_context=lambda *_args, **_kwargs: (_args, _kwargs),
            render_report=lambda *_args, **_kwargs: "should-not-run",
        ),
    )

    assert result.markdown is None
    assert result.metrics_data == {}


def test_controlled_summary_workflow_returns_empty_when_template_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    result = render_controlled_summary_workflow(
        analysis_payload=_build_analysis_payload(),
        task_id=uuid4(),
        blocked_by_quality_gate=False,
        deps=ControlledSummaryWorkflowDeps(
            build_context=lambda *_args, **_kwargs: ({"ctx": True}, {}),
            render_report=lambda *_args, **_kwargs: "should-not-run",
        ),
    )

    assert result.markdown is None
    assert result.metrics_data == {}
