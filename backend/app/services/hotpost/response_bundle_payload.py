from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from app.services.hotpost.detail_builder import (
    build_top_discovery_posts,
    build_top_rants,
    extract_competitor_mentions,
)
from app.services.hotpost.enrichment import enrich_opportunity_payload, enrich_rant_payload
from app.services.hotpost.rant_action_rules import (
    build_rant_recommended_actions,
    sanitize_rant_expression,
)
from app.services.hotpost.response_bundle_common import (
    COMPETITOR_NAME_STOPWORDS,
    HotpostResponseBundleInput,
    get_payload_value,
    sanitize_competitor_mentions,
    select_key_comments,
    set_payload_value,
    stable_migration_destinations,
)
from app.services.hotpost.rules import classify_intent_label, normalize_text


def build_base_response_payload(
    bundle: HotpostResponseBundleInput,
    *,
    status_value: str,
    debug_info: Any,
) -> tuple[dict[str, Any], int]:
    evidence_count = len(bundle.top_posts)
    community_counts = Counter(post.subreddit for post in bundle.top_posts)
    community_distribution = {
        sub: f"{count / evidence_count * 100:.0f}%" if evidence_count else "0%"
        for sub, count in community_counts.most_common(5)
    }
    payload: dict[str, Any] = {
        "query_id": bundle.query_id,
        "query": bundle.query,
        "mode": bundle.mode,
        "search_time": datetime.now(timezone.utc),
        "from_cache": False,
        "status": status_value,
        "summary": bundle.summary_result.text,
        "top_posts": bundle.top_posts,
        "key_comments": select_key_comments(bundle.all_comments, limit=5),
        "pain_points": bundle.pain_points,
        "opportunities": bundle.opportunities,
        "trending_keywords": None,
        "communities": list(community_counts.keys()),
        "related_queries": [],
        "evidence_count": evidence_count,
        "community_distribution": community_distribution,
        "sentiment_overview": bundle.sentiment_overview,
        "rant_intensity": bundle.rant_intensity,
        "need_urgency": bundle.need_urgency,
        "confidence": bundle.confidence,
        "notes": bundle.notes,
        "debug_info": debug_info,
    }
    return payload, evidence_count


def apply_mode_payload_enrichment(
    bundle: HotpostResponseBundleInput,
    payload: dict[str, Any],
    *,
    evidence_count: int,
) -> dict[str, Any]:
    if bundle.mode == "rant":
        return _apply_rant_payload_enrichment(bundle, payload, evidence_count=evidence_count)
    if bundle.mode == "opportunity":
        return _apply_opportunity_payload_enrichment(bundle, payload, evidence_count=evidence_count)
    return payload


def build_next_steps_payload(bundle: HotpostResponseBundleInput, payload: dict[str, Any]) -> dict[str, Any]:
    next_keywords = bundle.keywords[:5]
    if bundle.mode == "trending":
        generated_keywords = payload.get("trending_keywords")
        if isinstance(generated_keywords, list) and generated_keywords:
            next_keywords = [str(item).strip() for item in generated_keywords if str(item).strip()][:5]

    next_steps: dict[str, Any] = {
        "deepdive_available": True,
        "deepdive_token": None,
        "suggested_keywords": next_keywords,
    }
    if bundle.mode == "rant":
        actions = build_rant_recommended_actions(
            payload,
            query_family=bundle.query_family,
            primary_friction=bundle.primary_friction,
            get_payload_value=get_payload_value,
        )
        if actions:
            next_steps["recommended_actions"] = actions
    return next_steps


def _apply_rant_payload_enrichment(
    bundle: HotpostResponseBundleInput,
    payload: dict[str, Any],
    *,
    evidence_count: int,
) -> dict[str, Any]:
    payload["pain_points"] = bundle.pain_points
    blocked_competitor_terms = {
        str(item).strip().lower()
        for item in list(bundle.keywords) + list(bundle.domain_terms) + list(bundle.expanded_terms)
        if str(item).strip()
    } | COMPETITOR_NAME_STOPWORDS
    category_counts = Counter(bundle.categories)
    payload = enrich_rant_payload(
        payload,
        category_counts=category_counts,
        lexicon=bundle.lexicon,
        fallback_quotes=[post.title for post in bundle.top_posts if post.title][:3],
        evidence_count=evidence_count,
        query_family=bundle.query_family,
    )
    if not payload.get("competitor_mentions"):
        payload["competitor_mentions"] = extract_competitor_mentions(bundle.top_posts, query=bundle.query)
    payload["competitor_mentions"] = sanitize_competitor_mentions(
        list(payload.get("competitor_mentions") or []),
        blocked_terms=blocked_competitor_terms,
    )

    intent_counts = Counter()
    for post in bundle.top_posts:
        text = normalize_text(f"{post.title} {post.body_preview or ''}")
        intent_counts[classify_intent_label(text, bundle.lexicon)] += 1
    total_intents = sum(intent_counts.values())
    total_mentions = intent_counts.get("already_left", 0) + intent_counts.get("considering", 0)
    payload["migration_intent"] = {
        "already_left": f"{intent_counts.get('already_left', 0) / total_intents * 100:.0f}%" if total_intents else "0%",
        "considering": f"{intent_counts.get('considering', 0) / total_intents * 100:.0f}%" if total_intents else "0%",
        "staying_reluctantly": f"{intent_counts.get('staying_reluctantly', 0) / total_intents * 100:.0f}%" if total_intents else "0%",
        "total_mentions": total_mentions,
        "percentage": round(total_mentions / total_intents, 4) if total_intents else 0.0,
        "status_distribution": {
            "already_left": intent_counts.get("already_left", 0) / total_intents if total_intents else 0.0,
            "considering": intent_counts.get("considering", 0) / total_intents if total_intents else 0.0,
            "staying": intent_counts.get("staying_reluctantly", 0) / total_intents if total_intents else 0.0,
        },
    }
    payload["top_rants"] = build_top_rants(bundle.top_posts)
    migration = payload.get("migration_intent") or {}
    destinations = stable_migration_destinations(list(payload.get("competitor_mentions") or []))
    if destinations:
        migration["destinations"] = destinations
    else:
        migration.pop("destinations", None)
        migration.pop("key_quote", None)
    payload["migration_intent"] = migration
    sanitize_rant_expression(
        payload,
        keywords=bundle.keywords,
        query_family=bundle.query_family,
        primary_friction=bundle.primary_friction,
        get_payload_value=get_payload_value,
        set_payload_value=set_payload_value,
    )
    return payload


def _apply_opportunity_payload_enrichment(
    bundle: HotpostResponseBundleInput,
    payload: dict[str, Any],
    *,
    evidence_count: int,
) -> dict[str, Any]:
    opportunity_strength = "weak"
    if evidence_count >= 20 and bundle.me_too_count >= 5:
        opportunity_strength = "strong"
    elif evidence_count >= 10:
        opportunity_strength = "medium"
    payload["opportunity_strength"] = opportunity_strength
    payload = enrich_opportunity_payload(
        payload,
        me_too_count=bundle.me_too_count,
        opportunity_strength=opportunity_strength,
    )
    payload["top_discovery_posts"] = build_top_discovery_posts(bundle.top_posts)
    market = payload.get("market_opportunity")
    if isinstance(market, dict):
        market.setdefault("strength", opportunity_strength)
        payload["market_opportunity"] = market
    return payload
