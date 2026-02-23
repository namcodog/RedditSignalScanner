from __future__ import annotations

from typing import Any, Mapping, Sequence


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _trim_list(value: Sequence[Any], limit: int) -> list[Any]:
    if limit <= 0:
        return []
    return list(value[:limit])


def build_facts_slice_for_report(
    *,
    facts_v2_package: Mapping[str, Any],
    facts_v2_quality: Mapping[str, Any] | None = None,
    trend_summary: Mapping[str, Any] | None = None,
    market_saturation: Sequence[Mapping[str, Any]] | None = None,
    battlefield_profiles: Sequence[Mapping[str, Any]] | None = None,
    top_drivers: Sequence[Mapping[str, Any]] | None = None,
    max_communities: int = 8,
    max_posts: int = 20,
    max_comments: int = 30,
) -> dict[str, Any]:
    facts = _as_dict(facts_v2_package)
    aggregates = _as_dict(facts.get("aggregates"))
    data_lineage = _as_dict(facts.get("data_lineage"))
    business_signals = _as_dict(facts.get("business_signals"))

    communities = _as_list(aggregates.get("communities"))
    aggregates["communities"] = _trim_list(communities, max_communities)

    sample_posts_db = _trim_list(_as_list(facts.get("sample_posts_db")), max_posts)
    sample_comments_db = _trim_list(_as_list(facts.get("sample_comments_db")), max_comments)

    payload: dict[str, Any] = {
        "meta": _as_dict(facts.get("meta")),
        "data_lineage": data_lineage,
        "aggregates": aggregates,
        "business_signals": business_signals,
        "sample_posts_db": sample_posts_db,
        "sample_comments_db": sample_comments_db,
    }

    if facts_v2_quality is not None:
        payload["facts_v2_quality"] = dict(facts_v2_quality)
    if trend_summary is not None:
        payload["trend_summary"] = dict(trend_summary)
    if market_saturation is not None:
        payload["market_saturation"] = list(market_saturation)
    if battlefield_profiles is not None:
        payload["battlefield_profiles"] = list(battlefield_profiles)
    if top_drivers is not None:
        payload["top_drivers"] = list(top_drivers)

    return payload


__all__ = ["build_facts_slice_for_report"]
