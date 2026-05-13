from __future__ import annotations

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.hotpost_supply_contract import get_supply_hot_lane_rules
from app.services.hotpost.hotpost_supply_projection import get_topic_pack_payload


def _quote_text(candidate: CandidatePack) -> str:
    return " ".join(quote.text.lower() for quote in candidate.evidence_quotes)


def _has_any_term(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _candidate_text(candidate: CandidatePack) -> str:
    return f"{candidate.title.lower()} {_quote_text(candidate)}"


def _looks_like_low_signal_hot(candidate: CandidatePack, reject_terms: set[str]) -> bool:
    return _has_any_term(_candidate_text(candidate), reject_terms)


def _looks_like_practical_share(candidate: CandidatePack, practical_terms: set[str]) -> bool:
    return _has_any_term(_quote_text(candidate), practical_terms)


def _looks_like_direct_question_title(title: str, question_markers: set[str]) -> bool:
    normalized = title.lower().strip()
    if "?" in normalized:
        return True
    return any(normalized.startswith(f"{marker} ") for marker in question_markers)


def _has_title_debate_shape(title: str, title_terms: set[str]) -> bool:
    normalized = title.lower()
    return any(term in normalized for term in title_terms)


def _looks_like_collective_reporting(candidate: CandidatePack, reporting_terms: set[str]) -> bool:
    return _has_any_term(_candidate_text(candidate), reporting_terms)


def _looks_like_platform_watch(candidate: CandidatePack, platform_terms: set[str]) -> bool:
    return _has_any_term(_candidate_text(candidate), platform_terms)


def _has_hot_discussion_shape(
    candidate: CandidatePack,
    debate_terms: set[str],
    collective_reporting_terms: set[str],
    platform_action_terms: set[str],
    *,
    min_quote_count: int,
    min_collective_comments: int,
    title_debate_terms: set[str],
) -> bool:
    text = _quote_text(candidate)
    title_debate_shape = _has_title_debate_shape(candidate.title, title_debate_terms)
    collective_reporting_shape = _looks_like_collective_reporting(candidate, collective_reporting_terms)
    platform_watch_shape = _looks_like_platform_watch(candidate, platform_action_terms)
    if len(candidate.evidence_quotes) < min_quote_count:
        return (
            collective_reporting_shape
            or platform_watch_shape
            or (title_debate_shape and candidate.num_comments >= min_collective_comments)
        )
    long_quote = any(len(quote.text) >= 160 for quote in candidate.evidence_quotes)
    short_quote_cluster = candidate.num_comments >= min_collective_comments and len(text) >= 80
    return (
        collective_reporting_shape
        or platform_watch_shape
        or long_quote
        or short_quote_cluster
        or _has_any_term(text, debate_terms)
        or title_debate_shape
    )


def infer_validation_lane(candidate: CandidatePack) -> str:
    hot_rules = get_supply_hot_lane_rules()
    payload = get_topic_pack_payload(candidate.source_scope_id, candidate.topic_pack_id)
    is_listing = candidate.listing_source.startswith("listing:")
    is_high_heat = (
        candidate.score >= hot_rules["high_heat_override_score"]
        or candidate.num_comments >= hot_rules["high_heat_override_comments"]
    )
    discussion_shape = _has_hot_discussion_shape(
        candidate,
        hot_rules["debate_or_collective_terms"],
        hot_rules["collective_reporting_terms"],
        hot_rules["platform_action_terms"],
        min_quote_count=hot_rules["min_quote_count"],
        min_collective_comments=hot_rules["min_collective_comments"],
        title_debate_terms=hot_rules["title_debate_terms"],
    )
    collective_reporting_shape = _looks_like_collective_reporting(candidate, hot_rules["collective_reporting_terms"])
    platform_watch_shape = _looks_like_platform_watch(candidate, hot_rules["platform_action_terms"])
    if is_listing and not payload.get("allow_listing", True):
        return "signal"
    if candidate.signal_level == "sustained":
        sustained_override_pass = (
            candidate.score >= hot_rules["sustained_override_min_score"]
            or candidate.num_comments >= hot_rules["sustained_override_min_comments"]
        )
        if not sustained_override_pass and not discussion_shape:
            return "signal"
    elif candidate.signal_level not in {"hot", "rising"}:
        return "signal"
    if candidate.matched_subreddit.lower() in hot_rules["blocked_subreddits"]:
        return "signal"
    if candidate.score < hot_rules["min_score"] and candidate.num_comments < hot_rules["min_comments"]:
        return "signal"
    if any(tag in hot_rules["action_intents"] for tag in candidate.intent_tags) and _looks_like_direct_question_title(
        candidate.title, hot_rules["direct_question_markers"]
    ) and not (is_high_heat or collective_reporting_shape or platform_watch_shape):
        return "signal"
    if _looks_like_low_signal_hot(candidate, hot_rules["reject_terms"]):
        return "signal"
    if _looks_like_practical_share(candidate, hot_rules["practical_share_terms"]):
        return "signal"
    if not discussion_shape:
        return "signal"
    return "hot"


def resolve_lane(raw_lane:Optional[ str], *, card_type: str) -> str:
    if raw_lane in {"signal", "hot", "breakdown"}:
        return raw_lane
    if card_type == "write":
        return "breakdown"
    return "signal"


__all__ = ["infer_validation_lane", "resolve_lane"]
