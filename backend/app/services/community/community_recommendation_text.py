from __future__ import annotations

from app.services.community.community_recommendation_models import CommunitySignal
from app.services.community.interest_tag_catalog import RecommendationPolicy


def _format(template: str, values: dict[str, object]) -> str:
    return template.format(**values)


def public_reasons(
    signal: CommunitySignal,
    policy: RecommendationPolicy,
    semantic_terms: tuple[str, ...],
) -> tuple[str, ...]:
    templates = policy.reason_templates
    related_terms = "、".join(semantic_terms[:3]) or "当前标签"
    values = {
        "recent_posts_15d": signal.recent_posts_15d,
        "historical_posts": signal.historical_posts,
        "hotpost_cards": signal.hotpost_cards,
        "related_terms": related_terms,
        "sample_title": signal.sample_titles[0] if signal.sample_titles else "",
    }
    reasons: list[str] = []
    if signal.recent_posts_15d:
        reasons.append(_format(templates["recent_activity"], values))
    elif signal.historical_posts:
        reasons.append(_format(templates["historical_depth"], values))
    if semantic_terms or signal.semantic_observations or signal.content_labels or signal.content_entities:
        reasons.append(_format(templates["semantic_fit"], values))
    if signal.hotpost_cards:
        reasons.append(_format(templates["signal_density"], values))
    if not reasons:
        reasons.append(_format(templates["low_evidence"], values))
    return tuple(dict.fromkeys(reasons))


def public_terms(semantic_terms: tuple[str, ...], tag_name: str) -> tuple[str, ...]:
    terms = tuple(term for term in semantic_terms[:3] if "_" not in term)
    return terms or (tag_name,)


def evidence_summary(
    signal: CommunitySignal,
    semantic_terms: tuple[str, ...],
    policy: RecommendationPolicy,
) -> tuple[str, ...]:
    templates = policy.evidence_summary_templates
    values = {
        "recent_posts_15d": signal.recent_posts_15d,
        "semantic_terms": ", ".join(semantic_terms[:5]),
        "semantic_observations": signal.semantic_observations,
        "hotpost_cards": signal.hotpost_cards,
        "historical_posts": signal.historical_posts,
        "sample_title": signal.sample_titles[0] if signal.sample_titles else "",
    }
    summary: list[str] = []
    if signal.recent_posts_15d:
        summary.append(_format(templates["recent_activity"], values))
    if semantic_terms:
        summary.append(_format(templates["semantic_terms"], values))
    elif signal.semantic_observations:
        summary.append(_format(templates["semantic_observations"], values))
    if signal.hotpost_cards:
        summary.append(_format(templates["hotpost_cards"], values))
    if signal.historical_posts:
        summary.append(_format(templates["historical_posts"], values))
    if signal.sample_titles:
        summary.append(_format(templates["sample_title"], values))
    return tuple(summary or (_format(templates["low_evidence"], values),))


def evidence_teaser(signal: CommunitySignal, policy: RecommendationPolicy) -> str:
    if signal.sample_titles:
        return policy.reason_templates["sample_title"].format(sample_title=signal.sample_titles[0])
    return ""
