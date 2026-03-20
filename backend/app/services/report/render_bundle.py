from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Mapping

from app.schemas.report_payload import LayerCoverageItem, MetricsSummary


@dataclass(slots=True, frozen=True)
class ControlledMarkdownResult:
    markdown: str | None
    metrics_data: dict[str, Any]
    llm_used: bool
    source: str | None


@dataclass(slots=True, frozen=True)
class ReportRenderBundle:
    report_html: str | None
    metrics_summary: MetricsSummary | None
    llm_used: bool
    controlled_md_source: str | None
    market_enhancements: dict[str, Any] | None


def build_metrics_summary(metrics_data: Mapping[str, Any] | None) -> MetricsSummary | None:
    if not metrics_data:
        return None

    entity_coverage = metrics_data.get("entity_coverage", {}) or {}
    layer_coverage = metrics_data.get("layer_coverage", []) or []
    layers: list[LayerCoverageItem] = []
    for entry in layer_coverage:
        try:
            layers.append(
                LayerCoverageItem(
                    layer=str(entry.get("layer")),
                    posts=int(entry.get("posts", 0) or 0),
                    hit_posts=int(entry.get("hit_posts", 0) or 0),
                    coverage=float(entry.get("coverage", 0.0) or 0.0),
                )
            )
        except Exception:
            continue

    return MetricsSummary(
        overall=float(entity_coverage.get("overall", 0.0) or 0.0),
        brands=float(entity_coverage.get("brands", 0.0) or 0.0),
        pain_points=float(entity_coverage.get("pain_points", 0.0) or 0.0),
        top10_unique_share=float(entity_coverage.get("top10_unique_share", 0.0) or 0.0),
        layers=layers,
    )


def _render_markdown_html(markdown_text: str) -> str:
    try:
        import markdown as markdown_lib  # type: ignore

        return markdown_lib.markdown(markdown_text, extensions=["extra", "tables"])
    except Exception:
        return f"<pre>{escape(markdown_text)}</pre>"


def build_report_render_bundle(
    *,
    base_report_html: str | None,
    controlled_result: ControlledMarkdownResult,
    blocked_by_quality_gate: bool,
    market_enhancements: Mapping[str, Any] | None = None,
) -> ReportRenderBundle:
    merged_market_enhancements = (
        dict(market_enhancements)
        if isinstance(market_enhancements, Mapping)
        else None
    )
    if controlled_result.source == "community_market":
        if merged_market_enhancements is None:
            merged_market_enhancements = {}
        merged_market_enhancements["mode"] = "community_market"

    prefer_controlled_html = controlled_result.source == "community_market"

    rendered_html: str | None = None
    if controlled_result.markdown and not blocked_by_quality_gate and (
        prefer_controlled_html or not base_report_html
    ):
        rendered_html = _render_markdown_html(controlled_result.markdown)

    return ReportRenderBundle(
        report_html=rendered_html or base_report_html,
        metrics_summary=build_metrics_summary(controlled_result.metrics_data),
        llm_used=controlled_result.llm_used,
        controlled_md_source=controlled_result.source,
        market_enhancements=merged_market_enhancements,
    )


__all__ = [
    "ControlledMarkdownResult",
    "ReportRenderBundle",
    "build_metrics_summary",
    "build_report_render_bundle",
]
