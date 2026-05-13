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


def _copy_if_present(payload: dict[str, Any], facts: Mapping[str, Any], field: str) -> None:
    value = facts.get(field)
    if value is not None:
        payload[field] = value


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
    is_v2_package = "aggregates" in facts and "meta" in facts

    if is_v2_package:
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
    else:
        communities = [
            dict(item)
            for item in _as_list(facts.get("communities"))
            if isinstance(item, Mapping)
        ]
        communities.sort(key=lambda item: item.get("final_score", 0), reverse=True)

        payload = {
            "overall": {
                "global_ps_ratio": facts.get("global_ps_ratio"),
                "total_posts": facts.get("total_posts"),
                "total_comments": facts.get("total_comments"),
                "topic": facts.get("topic"),
                "trend_analysis": facts.get("trend_analysis"),
                "trend_source": facts.get("trend_source"),
            },
            "community_stats": _trim_list(communities, max_communities),
            "brand_pain": _trim_list(_as_list(facts.get("brand_pain")), 10),
            "pain_clusters": _trim_list(_as_list(facts.get("pain_clusters")), 5),
            "market_saturation": _as_list(facts.get("market_saturation")),
            "business_signals": _as_dict(facts.get("business_signals")),
            "sample_posts_db": _trim_list(_as_list(facts.get("sample_posts_db")), max_posts),
            "sample_comments_db": _trim_list(_as_list(facts.get("sample_comments_db")), max_comments),
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
    _copy_if_present(payload, facts, "diagnostics")
    _copy_if_present(payload, facts, "market_landscape")
    _copy_if_present(payload, facts, "price_analysis")
    _copy_if_present(payload, facts, "usage_context")
    _copy_if_present(payload, facts, "community_personas")

    topic_keywords = _as_list(facts.get("topic_keywords"))
    if topic_keywords:
        payload["topic_keywords"] = topic_keywords[:30]

    return payload


__all__ = ["build_facts_slice_for_report"]
