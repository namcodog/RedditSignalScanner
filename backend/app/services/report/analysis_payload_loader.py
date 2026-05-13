from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import ValidationError

from app.schemas.analysis import AnalysisRead
from app.services.analysis import assign_competitor_layers, build_layer_summary


class AnalysisPayloadValidationError(Exception):
    """Raised when report analysis payload cannot be normalized into AnalysisRead."""


def classify_severity(sentiment_score: float) -> str:
    if sentiment_score <= -0.6:
        return "high"
    if sentiment_score <= -0.3:
        return "medium"
    return "low"


def format_analysis_version(version: Any) -> str:
    try:
        numeric = float(version)
    except (TypeError, ValueError):
        return str(version)
    if numeric.is_integer():
        return f"{numeric:.1f}"
    return str(numeric)


def _derive_title(description: str) -> str:
    if not description:
        return ""
    text = description.strip()
    for sep in ("。", "，", ".", ",", "；", ";", ":", "：", "-", "—"):
        if sep in text:
            text = text.split(sep, 1)[0].strip()
            break
    return text[:18] if len(text) > 18 else text


def _normalise_insights(insights: dict[str, Any]) -> dict[str, Any]:
    pain_points = insights.get("pain_points") or []
    for item in pain_points:
        sentiment = float(item.get("sentiment_score", 0.0))
        item["sentiment_score"] = max(-1.0, min(1.0, sentiment))
        if not item.get("severity"):
            item["severity"] = classify_severity(sentiment)
        item.setdefault("example_posts", [])
        item.setdefault("user_examples", [])
        description = str(item.get("description") or "").strip()
        if description:
            item.setdefault("text", description)
            if not item.get("title"):
                item["title"] = _derive_title(description)

    insights.setdefault("pain_points", pain_points)

    pain_clusters = insights.get("pain_clusters") or []
    for cluster in pain_clusters:
        for key in ("positive_mean", "negative_mean", "neutral_mean"):
            value = cluster.get(key)
            if isinstance(value, (int, float)):
                cluster[key] = max(-1.0, min(1.0, float(value)))
        for key in ("score", "relevance", "relevance_score"):
            if key in cluster and isinstance(cluster[key], (int, float)):
                cluster[key] = max(-1.0, min(1.0, float(cluster[key])))
    insights["pain_clusters"] = pain_clusters

    competitors_raw = insights.get("competitors") or []
    competitors = assign_competitor_layers(competitors_raw)
    insights["competitors"] = competitors
    insights.setdefault("competitor_layers_summary", build_layer_summary(competitors))

    if not insights.get("channel_breakdown"):
        channels = []
        entity_summary = insights.get("entity_summary") or {}
        if isinstance(entity_summary, Mapping):
            channels = entity_summary.get("channels") or []
        if isinstance(channels, Mapping):
            channels = list(channels.values())
        if isinstance(channels, list):
            insights["channel_breakdown"] = [
                {"name": row.get("name"), "mentions": row.get("mentions", 0)}
                for row in channels[:5]
                if isinstance(row, Mapping) and row.get("name")
            ]
        else:
            insights["channel_breakdown"] = []

    opportunities = insights.get("opportunities") or []
    for item in opportunities:
        if not isinstance(item, Mapping):
            continue
        description = str(item.get("description") or "").strip()
        if description:
            item.setdefault("text", description)
            if not item.get("title"):
                item["title"] = _derive_title(description)
    insights["opportunities"] = opportunities
    insights.setdefault("action_items", insights.get("action_items") or [])
    insights.setdefault("pain_clusters", insights.get("pain_clusters") or [])

    summary = insights.get("competitor_layers_summary") or []
    if not isinstance(summary, list):
        summary = []
    if len(summary) < 2:
        needed = 2 - len(summary)
        used_layers = {
            str((entry or {}).get("layer"))
            for entry in summary
            if isinstance(entry, Mapping)
        }
        extras: list[dict[str, Any]] = []

        for comp in competitors:
            if len(extras) >= needed:
                break
            layer = str(comp.get("layer") or "layer_auto").lower() or "layer_auto"
            if layer in used_layers:
                continue
            extras.append(
                {
                    "layer": layer,
                    "label": layer.title(),
                    "top_competitors": [
                        {
                            "name": str(comp.get("name") or ""),
                            "mentions": int(comp.get("mentions") or 0),
                            "sentiment": comp.get("sentiment"),
                        }
                    ],
                    "threats": str(
                        (comp.get("strengths") or [""])[0]
                        if isinstance(comp.get("strengths"), Sequence)
                        and not isinstance(comp.get("strengths"), (str, bytes))
                        and comp.get("strengths")
                        else ""
                    ),
                }
            )
            used_layers.add(layer)

        while len(extras) < needed:
            filler_layer = f"layer_auto_{len(summary) + len(extras) + 1}"
            extras.append(
                {
                    "layer": filler_layer,
                    "label": filler_layer.replace("_", " ").title(),
                    "top_competitors": [
                        {
                            "name": "Synthetic competitor",
                            "mentions": 0,
                            "sentiment": None,
                        }
                    ],
                    "threats": "",
                }
            )
        if extras:
            summary.extend(extras[:needed])
    insights["competitor_layers_summary"] = summary

    current_summary = insights.get("entity_summary") or {}
    insights.setdefault(
        "entity_summary",
        {
            "brands": current_summary.get("brands", []),
            "features": current_summary.get("features", []),
            "pain_points": current_summary.get("pain_points", []),
        },
    )
    return insights


def _normalise_sources(sources: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "communities",
        "posts_analyzed",
        "cache_hit_rate",
        "ps_ratio",
        "analysis_duration_seconds",
        "reddit_api_calls",
        "collection_warnings",
        "product_description",
        "communities_detail",
        "recovery_strategy",
        "fallback_quality",
        "dedup_stats",
        "duplicates_summary",
        "seed_source",
        "data_source",
        "report_tier",
        "analysis_blocked",
        "facts_v2_quality",
        "trend_source",
        "trend_degraded",
        "facts_slice",
        "report_structured",
        "structured_llm_status",
        "structured_llm_reason",
        "knowledge_graph",
        "llm_used",
        "llm_model",
        "llm_rounds",
    }
    filtered = {key: sources.get(key) for key in allowed_keys if key in sources}
    filtered.setdefault("communities", [])
    filtered.setdefault("posts_analyzed", 0)
    filtered.setdefault("cache_hit_rate", 0.0)
    filtered.setdefault("analysis_duration_seconds", None)
    filtered.setdefault("reddit_api_calls", None)
    filtered.setdefault("collection_warnings", [])
    filtered.setdefault("product_description", None)
    filtered.setdefault("communities_detail", [])
    filtered.setdefault("ps_ratio", None)
    filtered.setdefault("report_tier", None)
    filtered.setdefault("analysis_blocked", None)
    filtered.setdefault("facts_v2_quality", None)
    filtered.setdefault("trend_source", None)
    filtered.setdefault("trend_degraded", None)
    filtered.setdefault("facts_slice", None)
    filtered.setdefault("report_structured", None)
    filtered.setdefault("structured_llm_status", None)
    filtered.setdefault("structured_llm_reason", None)
    filtered.setdefault("knowledge_graph", None)
    filtered.setdefault("llm_used", None)
    filtered.setdefault("llm_model", None)
    filtered.setdefault("llm_rounds", None)
    return filtered


def _migrate_v09_to_v10(
    insights: dict[str, Any],
    sources: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], str]:
    migrated_insights = copy.deepcopy(insights)
    for item in migrated_insights.get("pain_points", []) or []:
        sentiment = float(item.get("sentiment_score", 0.0))
        item.setdefault("severity", classify_severity(sentiment))
        item.setdefault("example_posts", [])
        item.setdefault("user_examples", [])

    migrated_sources = copy.deepcopy(sources)
    if "analysis_duration" in migrated_sources:
        if migrated_sources.get("analysis_duration_seconds") is None:
            try:
                migrated_sources["analysis_duration_seconds"] = int(
                    round(float(migrated_sources["analysis_duration"]))
                )
            except Exception:
                migrated_sources["analysis_duration_seconds"] = None
        migrated_sources.pop("analysis_duration", None)

    return migrated_insights, migrated_sources, "1.0"


def _apply_version_migrations(
    *,
    version: str,
    insights: dict[str, Any],
    sources: dict[str, Any],
    target_analysis_version: str,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    current = format_analysis_version(version)
    target = format_analysis_version(target_analysis_version)
    migrations: dict[str, Any] = {
        "0.9": _migrate_v09_to_v10,
    }

    visited: set[str] = set()
    updated_insights = insights
    updated_sources = sources

    while current in migrations and current != target and current not in visited:
        visited.add(current)
        migrator = migrations[current]
        updated_insights, updated_sources, current = migrator(
            updated_insights,
            updated_sources,
        )

    return updated_insights, updated_sources, current


def validate_report_analysis_payload(
    *,
    analysis: Any,
    target_analysis_version: str,
) -> AnalysisRead:
    raw_insights = copy.deepcopy(analysis.insights or {})
    raw_sources = copy.deepcopy(analysis.sources or {})
    (
        migrated_insights,
        migrated_sources,
        resolved_version,
    ) = _apply_version_migrations(
        version=str(analysis.analysis_version),
        insights=raw_insights,
        sources=raw_sources,
        target_analysis_version=target_analysis_version,
    )
    processed_insights = _normalise_insights(migrated_insights)
    processed_sources = _normalise_sources(migrated_sources)

    payload = {
        "id": analysis.id,
        "task_id": analysis.task_id,
        "insights": processed_insights,
        "sources": processed_sources,
        "confidence_score": analysis.confidence_score,
        "analysis_version": resolved_version,
        "created_at": analysis.created_at,
    }

    try:
        return AnalysisRead.model_validate(payload)
    except ValidationError as exc:
        raise AnalysisPayloadValidationError(
            "Failed to validate analysis payload"
        ) from exc
