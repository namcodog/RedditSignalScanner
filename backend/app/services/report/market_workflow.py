from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from pathlib import Path
from importlib import import_module
from typing import Any, Awaitable, Callable, Mapping, Sequence

from app.schemas.analysis import AnalysisRead
from app.services.analysis.t1_clustering import build_pain_clusters
from app.services.analysis.t1_stats import T1StatsSnapshot, build_stats_snapshot
from app.services.report.render_bundle import ControlledMarkdownResult
from app.services.report.t1_market_agent import ReportInputs, T1MarketReportAgent

logger = logging.getLogger(__name__)


def serialize_market_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return {str(key): serialize_market_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_market_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(serialize_market_value(item) for item in value)
    if hasattr(value, "to_dict"):
        try:
            return value.to_dict()
        except Exception:
            return value
    if is_dataclass(value):
        return asdict(value)
    return value


async def build_market_report_markdown(
    db: Any,
    *,
    quality_level: str,
    product_description: str,
    analysis_payload: AnalysisRead | None = None,
) -> tuple[str | None, T1StatsSnapshot | None, list[Any] | None, bool]:
    if quality_level not in {"standard", "premium"}:
        return None, None, None, False
    template_markdown = await _render_market_template_markdown(
        analysis_payload=analysis_payload,
    )
    if template_markdown:
        return template_markdown, None, None, False
    stats = await build_stats_snapshot(db)
    clusters = await build_pain_clusters(db)
    agent = T1MarketReportAgent(
        ReportInputs(
            stats=stats,
            clusters=clusters,
            product_description=product_description,
        ),
        quality_level=quality_level,
    )
    markdown = agent.render()
    return markdown, stats, clusters, agent.llm_used


def _candidate_paths(path: Path) -> list[Path]:
    if path.is_absolute():
        return [path]
    parts = path.parts
    if parts and parts[0] == "backend":
        return [path, Path(*parts[1:])]
    return [path, Path("backend") / path]


def _first_existing(path: Path) -> Path | None:
    for candidate in _candidate_paths(path):
        try:
            if candidate.exists():
                return candidate
        except Exception:
            continue
    return None


async def _render_market_template_markdown(
    *,
    analysis_payload: AnalysisRead | None,
) -> str | None:
    if analysis_payload is None:
        return None

    from app.core.config import settings
    from app.services.report.market_report import MarketReportBuilder

    template_path = _first_existing(Path(settings.market_report_template_path))
    if template_path is None or not template_path.exists():
        return None

    builder = MarketReportBuilder()
    analysis_dict = {
        "insights": analysis_payload.insights.model_dump(mode="json"),
        "sources": analysis_payload.sources.model_dump(mode="json"),
    }
    personas = await builder.quick_personas(analysis_dict)
    quotes = await builder.quick_quotes(analysis_dict)
    saturation = await builder.quick_saturation(analysis_dict)
    copy_ammo = builder.quick_copy_ammo(analysis_dict)
    gtm_plans = builder.quick_gtm_plans(
        analysis=analysis_dict,
        personas=personas,
    )
    context = builder.build_context(
        analysis=analysis_dict,
        personas=personas,
        quotes=quotes,
        saturation=saturation,
        copy_ammo=copy_ammo,
        gtm_plans=gtm_plans,
    )
    template_text = template_path.read_text(encoding="utf-8")
    return template_text.format_map(defaultdict(str, context))


async def build_market_enhancements(
    db: Any,
    analysis_payload: AnalysisRead,
    *,
    enabled: bool,
) -> dict[str, Any] | None:
    if not enabled:
        return None

    from app.services.report.market_report import MarketReportBuilder

    builder = MarketReportBuilder()
    analysis_dict = analysis_payload.model_dump(mode="python")
    insights = analysis_dict.get("insights") or {}
    sources = analysis_dict.get("sources") or {}
    communities = [str(item) for item in (sources.get("communities") or []) if str(item).strip()]
    pain_points = list(insights.get("pain_points") or [])
    brands = [
        str(item.get("name") or "").strip()
        for item in (insights.get("competitors") or [])
        if isinstance(item, Mapping) and str(item.get("name") or "").strip()
    ]

    async def _run_personas() -> list[Any]:
        try:
            mod = import_module("app.services.analysis.persona_generator")
            generator = mod.PersonaGenerator()
            return await generator.generate_batch(db, communities, pain_points)
        except Exception as exc:
            if db is None and ("NoneType" in str(exc) or isinstance(exc, AttributeError)):
                return await builder.quick_personas(analysis_dict)
            logger.warning("market enhancements persona generation failed: %s", exc)
            return []

    async def _run_quotes() -> list[Any]:
        try:
            mod = import_module("app.services.analysis.quote_extractor")
            extractor = mod.QuoteExtractor()
            return extractor.extract_from_pain_points(pain_points)
        except Exception as exc:
            logger.warning("market enhancements quote extraction failed: %s", exc)
            return await builder.quick_quotes(analysis_dict)

    async def _run_saturation() -> list[Any]:
        try:
            mod = import_module("app.services.analysis.saturation_matrix")
            matrix = mod.SaturationMatrix()
            return await matrix.compute(db, communities, brands)
        except Exception as exc:
            if db is None and ("NoneType" in str(exc) or isinstance(exc, AttributeError)):
                return await builder.quick_saturation(analysis_dict)
            logger.warning("market enhancements saturation failed: %s", exc)
            return []

    personas_raw, quotes_raw, saturation_raw = await asyncio.gather(
        _run_personas(),
        _run_quotes(),
        _run_saturation(),
    )

    personas = serialize_market_value(personas_raw) or []
    quotes = serialize_market_value(quotes_raw) or []
    saturation = serialize_market_value(saturation_raw) or []
    gtm_personas = personas_raw
    if not gtm_personas or (
        isinstance(gtm_personas, Sequence)
        and gtm_personas
        and isinstance(gtm_personas[0], Mapping)
    ):
        gtm_personas = await builder.quick_personas(analysis_dict)
    gtm_plans = serialize_market_value(
        builder.quick_gtm_plans(
            analysis=analysis_dict,
            personas=gtm_personas,
        )
    ) or {}

    return {
        "mode": "community_market",
        "personas": personas,
        "quotes": quotes,
        "saturation": saturation,
        "gtm_plans": gtm_plans,
    }


async def build_controlled_markdown_result(
    *,
    blocked_by_quality_gate: bool,
    inline_llm_enabled: bool,
    prefer_market_markdown: bool,
    build_market_markdown: Callable[[], Awaitable[tuple[str | None, Any, Any, bool]]],
    render_controlled_summary: Callable[[], tuple[str | None, dict[str, Any]]],
) -> ControlledMarkdownResult:
    if not blocked_by_quality_gate and (inline_llm_enabled or prefer_market_markdown):
        try:
            market_md, _stats, _clusters, llm_used = await build_market_markdown()
        except Exception:
            market_md, llm_used = None, False
        if market_md:
            return ControlledMarkdownResult(
                markdown=market_md,
                metrics_data={},
                llm_used=llm_used,
                source="community_market",
            )

    controlled_md, metrics_data = render_controlled_summary()
    if controlled_md:
        return ControlledMarkdownResult(
            markdown=controlled_md,
            metrics_data=metrics_data,
            llm_used=False,
            source="executive_summary",
        )
    return ControlledMarkdownResult(
        markdown=None,
        metrics_data=metrics_data,
        llm_used=False,
        source=None,
    )


__all__ = [
    "build_controlled_markdown_result",
    "build_market_enhancements",
    "build_market_report_markdown",
    "serialize_market_value",
]
