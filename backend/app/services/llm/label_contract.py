from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def normalize_post_analysis(data: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "content_type": str(data.get("content_type") or "other").strip().lower(),
        "main_intent": str(data.get("main_intent") or "offtopic").strip().lower(),
        "sentiment": float(data.get("sentiment") or 0.0),
        "pain_tags": _coerce_list(data.get("pain_tags")),
        "aspect_tags": _coerce_list(data.get("aspect_tags")),
        "entities": {
            "known": _coerce_list((data.get("entities") or {}).get("known")),
            "new": _coerce_list((data.get("entities") or {}).get("new")),
        },
        "crossborder_signals": {
            "mentions_shipping": _coerce_bool(
                (data.get("crossborder_signals") or {}).get("mentions_shipping")
            ),
            "mentions_tax": _coerce_bool(
                (data.get("crossborder_signals") or {}).get("mentions_tax")
            ),
        },
        "purchase_intent_score": float(data.get("purchase_intent_score") or 0.0),
    }


def normalize_comment_analysis(data: Mapping[str, Any]) -> dict[str, Any]:
    base = normalize_post_analysis(data)
    base["actor_type"] = str(data.get("actor_type") or "other").strip().lower()
    return base


@dataclass(frozen=True)
class LLMScoreResult:
    value_score: float
    opportunity_score: float
    business_pool: str


def score_post_analysis(analysis: Mapping[str, Any]) -> LLMScoreResult:
    base_score = 3.0

    ctype = analysis.get("content_type", "other")
    if ctype == "user_review":
        base_score += 3.0
    elif ctype == "ask_question":
        base_score += 1.0
    elif ctype == "news_sharing":
        base_score += 1.0
    elif ctype == "rant":
        base_score += 2.0

    intent = analysis.get("main_intent", "offtopic")
    if intent == "share_solution":
        base_score += 2.0
    elif intent == "complain":
        base_score += 2.0
    elif intent == "recommend_product":
        base_score += 1.0

    pains = analysis.get("pain_tags") or []
    base_score += min(len(pains) * 1.5, 4.5)

    cb = analysis.get("crossborder_signals") or {}
    if cb.get("mentions_shipping"):
        base_score += 1.0
    if cb.get("mentions_tax"):
        base_score += 1.0

    pi_score = float(analysis.get("purchase_intent_score") or 0.0)
    if pi_score > 0.7:
        base_score *= 1.2

    final_value = max(0.0, min(10.0, base_score))
    opp_score = (len(pains) * 0.25) + (pi_score * 0.5)
    if intent == "complain":
        opp_score += 0.2
    final_opp = max(0.0, min(1.0, opp_score))

    pool = "lab"
    if final_value >= 8.0:
        pool = "core"
    elif final_value <= 3.9:
        pool = "noise"

    return LLMScoreResult(
        value_score=round(final_value, 2),
        opportunity_score=round(final_opp, 2),
        business_pool=pool,
    )


def score_comment_analysis(analysis: Mapping[str, Any]) -> LLMScoreResult:
    base_score = 3.0

    actor = analysis.get("actor_type", "other")
    if actor == "buyer_review":
        base_score += 2.0
    elif actor == "buyer_ask":
        base_score += 1.0
    elif actor == "seller_operator":
        base_score -= 1.0
    elif actor == "expert_sharing":
        base_score += 2.0

    intent = analysis.get("main_intent", "offtopic")
    if intent == "share_solution":
        base_score += 3.0
    elif intent == "complain":
        base_score += 2.0
    elif intent == "recommend_product":
        base_score += 1.0
    elif intent == "offtopic":
        base_score -= 2.0

    pains = analysis.get("pain_tags") or []
    base_score += min(len(pains) * 1.0, 3.0)

    cb = analysis.get("crossborder_signals") or {}
    if cb.get("mentions_shipping"):
        base_score += 1.0
    if cb.get("mentions_tax"):
        base_score += 1.0

    pi_score = float(analysis.get("purchase_intent_score") or 0.0)
    if pi_score > 0.7:
        base_score *= 1.2

    final_value = max(0.0, min(10.0, base_score))
    opp_score = (len(pains) * 0.2) + (pi_score * 0.5)
    if intent == "complain":
        opp_score += 0.2
    final_opp = max(0.0, min(1.0, opp_score))

    pool = "lab"
    if final_value >= 8.0:
        pool = "core"
    elif final_value <= 3.9:
        pool = "noise"

    return LLMScoreResult(
        value_score=round(final_value, 2),
        opportunity_score=round(final_opp, 2),
        business_pool=pool,
    )


__all__ = [
    "LLMScoreResult",
    "normalize_comment_analysis",
    "normalize_post_analysis",
    "score_comment_analysis",
    "score_post_analysis",
]
