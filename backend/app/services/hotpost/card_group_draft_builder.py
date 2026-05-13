from __future__ import annotations

from collections import Counter
from hashlib import sha1

from app.schemas.hotpost_card_candidates import CandidatePack, TimeWindow
from app.schemas.hotpost_card_drafts import ValidationCardDraft, WritingCardDraft
from app.schemas.hotpost_clues import CardType, QuotePreview
from app.schemas.hotpost_signal import SignalLevel, WhyNowReason
from app.schemas.hotpost_validate_details import empty_validation_detail_payload


_BAD_PREFIXES = ("Welcome to /r/", "#####[Join the r/", "## **To /u/", "To keep this community relevant", "Feedback Friday!")
_LEVEL_ORDER = {"hot": 3, "rising": 2, "sustained": 1}
_WINDOW_ORDER = {"24h": 3, "7d": 2, "30d": 1}
_WHY_NOW_ORDER = {"new_threads_24h": 4, "new_comments_24h": 3, "switch_signal_7d": 2, "recurring_7d": 1}


def seed_group_validation_draft(candidates: list[CandidatePack]) -> ValidationCardDraft:
    merged = _merge_candidates(candidates)
    return ValidationCardDraft(
        **merged,
        card_type="validate",
        category_id="validate",
        detail=empty_validation_detail_payload(merged.get("lane")),
    )


def seed_group_writing_draft(candidates: list[CandidatePack]) -> WritingCardDraft:
    merged = _merge_candidates(candidates)
    return WritingCardDraft(
        **merged,
        card_type="write",
        category_id="write",
        detail={"thesis": "", "writing_angle_or_perspective": "", "tension_point_or_why_it_matters": "", "title_hooks": [], "quote_pack": []},
    )


def _merge_candidates(candidates: list[CandidatePack]) -> dict:
    if len(candidates) < 2:
        raise ValueError("Grouped draft requires at least 2 candidates")
    scope_ids = {item.source_scope_id for item in candidates}
    if len(scope_ids) != 1:
        raise ValueError("Grouped draft candidates must share one source scope")
    best = max(candidates, key=lambda item: (_LEVEL_ORDER[item.signal_level], item.score, item.num_comments))
    quotes = _merge_quotes(candidates)
    if len(quotes) < 2:
        raise ValueError("Grouped draft requires at least 2 usable quotes")
    communities = _merge_communities(candidates)
    digest = sha1("|".join(sorted(item.candidate_id for item in candidates)).encode("utf-8")).hexdigest()[:10]
    group_id = f"group-{best.source_scope_id}-{digest}"
    source_links = [f"https://www.reddit.com/r/{item.matched_subreddit}/comments/{item.post_id}" for item in candidates]
    topic_pack_id = _pick_topic_pack_id(candidates)
    topic_cluster_ids = _merge_topic_cluster_ids(candidates)
    named_topic_ids = _merge_named_topic_ids(candidates)
    return {
        "draft_id": f"draft-{group_id}",
        "candidate_id": group_id,
        "candidate_ids": [item.candidate_id for item in candidates],
        "card_id": f"card-{group_id}",
        "signal_id": f"sig-{group_id}",
        "topic_pack_id": topic_pack_id,
        "topic_cluster_id": topic_cluster_ids[0] if len(topic_cluster_ids) == 1 else None,
        "topic_cluster_ids": topic_cluster_ids,
        "named_topic_ids": named_topic_ids,
        "title": best.title,
        "source_scope_id": best.source_scope_id,
        "source_scope_name": best.source_scope_name,
        "matched_subreddit": best.matched_subreddit,
        "post_id": best.post_id,
        "source_event_at": max(item.created_at for item in candidates),
        "score": best.score,
        "num_comments": best.num_comments,
        "time_window": _pick_time_window(candidates),
        "signal_level": _pick_signal_level(candidates),
        "why_now_reason": _pick_why_now(candidates),
        "thread_count": len(candidates),
        "community_count": len(communities),
        "quote_count": len(quotes),
        "intent_tags": _merge_intents(candidates),
        "evidence_quotes": quotes[:5],
        "source_link": source_links[0],
        "source_links": source_links,
        "source_communities": communities,
        "draft_note": f"Seeded from grouped candidates: {', '.join(item.candidate_id for item in candidates)}",
    }


def _merge_quotes(candidates: list[CandidatePack]) -> list[QuotePreview]:
    seen: set[str] = set()
    quotes: list[QuotePreview] = []
    for item in candidates:
        for quote in item.evidence_quotes:
            text = quote.text.strip()
            if not text or text.startswith(_BAD_PREFIXES) or text in seen:
                continue
            seen.add(text)
            quotes.append(quote)
    return quotes


def _merge_communities(candidates: list[CandidatePack]) -> list[str]:
    counts = Counter(f"r/{item.matched_subreddit}" for item in candidates)
    return [name for name, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _merge_intents(candidates: list[CandidatePack]) -> list[str]:
    merged: list[str] = []
    for item in candidates:
        for tag in item.intent_tags:
            if tag not in merged:
                merged.append(tag)
    return merged


def _pick_topic_pack_id(candidates: list[CandidatePack]) ->Optional[ str]:
    counts = Counter(item.topic_pack_id for item in candidates if item.topic_pack_id)
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def _merge_topic_cluster_ids(candidates: list[CandidatePack]) -> list[str]:
    counts: Counter[str] = Counter()
    for item in candidates:
        for cluster_id in item.topic_cluster_ids:
            if cluster_id:
                counts[cluster_id] += 1
        if item.topic_cluster_id:
            counts[item.topic_cluster_id] += 1
    return [cluster_id for cluster_id, _ in counts.most_common()]


def _merge_named_topic_ids(candidates: list[CandidatePack]) -> list[str]:
    merged: list[str] = []
    for item in candidates:
        for topic_id in item.named_topic_ids:
            if topic_id and topic_id not in merged:
                merged.append(topic_id)
    return merged


def _pick_signal_level(candidates: list[CandidatePack]) -> SignalLevel:
    return max(candidates, key=lambda item: _LEVEL_ORDER[item.signal_level]).signal_level


def _pick_time_window(candidates: list[CandidatePack]) -> TimeWindow:
    return max(candidates, key=lambda item: _WINDOW_ORDER[item.time_window]).time_window


def _pick_why_now(candidates: list[CandidatePack]) -> WhyNowReason:
    return max(candidates, key=lambda item: _WHY_NOW_ORDER[item.why_now_reason]).why_now_reason
