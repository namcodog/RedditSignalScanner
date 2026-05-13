from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha1

from app.schemas.hotpost_card_candidates import CandidatePack, TimeWindow
from app.schemas.hotpost_clues import QuotePreview
from app.schemas.hotpost_signal import SignalLevel, WhyNowReason


_LEVEL_ORDER = {"hot": 3, "rising": 2, "sustained": 1}
_WINDOW_ORDER = {"24h": 3, "7d": 2, "30d": 1}
_WHY_NOW_ORDER = {"new_threads_24h": 4, "new_comments_24h": 3, "switch_signal_7d": 2, "recurring_7d": 1}


def build_grouped_candidates(candidates: list[CandidatePack]) -> list[CandidatePack]:
    grouped: dict[tuple[str, str, tuple[str, ...]], list[CandidatePack]] = defaultdict(list)
    for candidate in candidates:
        if not candidate.topic_pack_id:
            continue
        cluster_signature = _cluster_signature(candidate)
        if not cluster_signature:
            continue
        grouped[(candidate.source_scope_id, candidate.topic_pack_id, cluster_signature)].append(candidate)

    promoted: list[CandidatePack] = []
    for items in grouped.values():
        deduped = _dedupe_candidates(items)
        post_ids = {item.post_id for item in deduped if item.post_id}
        if len(post_ids) < 2:
            continue
        quotes = _merge_quotes(deduped)
        if len(quotes) < 2:
            continue
        communities = _merge_communities(deduped)
        best = max(deduped, key=lambda item: (_LEVEL_ORDER[item.signal_level], item.score, item.num_comments))
        topic_cluster_ids = _merge_topic_cluster_ids(deduped)
        digest = sha1("|".join(sorted(item.candidate_id for item in deduped)).encode("utf-8")).hexdigest()[:10]
        promoted.append(
            CandidatePack(
                candidate_id=f"group-{best.source_scope_id}-{digest}",
                signal_id=f"sig-group-{best.source_scope_id}-{digest}",
                source_scope_id=best.source_scope_id,
                source_scope_name=best.source_scope_name,
                topic_pack_id=best.topic_pack_id,
                topic_cluster_id=topic_cluster_ids[0] if len(topic_cluster_ids) == 1 else None,
                topic_cluster_ids=topic_cluster_ids,
                named_topic_ids=_merge_named_topic_ids(deduped),
                query=best.query,
                matched_subreddit=best.matched_subreddit,
                post_id=best.post_id,
                title=best.title,
                score=best.score,
                num_comments=best.num_comments,
                created_at=max(item.created_at for item in deduped),
                collected_at=max(item.collected_at for item in deduped),
                collect_batch_id=best.collect_batch_id,
                time_window=_pick_time_window(deduped),
                signal_level=_pick_signal_level(deduped),
                why_now_reason=_pick_why_now(deduped),
                listing_source=best.listing_source,
                primary_reason=f"{best.topic_pack_id}:grouped_evidence",
                matched_keywords=_merge_keywords(deduped),
                top_communities=communities,
                thread_count=len(post_ids),
                community_count=len(communities),
                quote_count=len(quotes),
                intent_tags=_merge_intents(deduped),
                evidence_quotes=quotes[:5],
            )
        )
    return promoted


def _dedupe_candidates(candidates: list[CandidatePack]) -> list[CandidatePack]:
    seen: set[str] = set()
    ordered: list[CandidatePack] = []
    for item in candidates:
        if item.candidate_id in seen:
            continue
        seen.add(item.candidate_id)
        ordered.append(item)
    return ordered


def _cluster_signature(candidate: CandidatePack) -> tuple[str, ...]:
    cluster_ids = {
        str(cluster_id).strip()
        for cluster_id in [*(candidate.topic_cluster_ids or []), *([candidate.topic_cluster_id] if candidate.topic_cluster_id else [])]
        if str(cluster_id).strip()
    }
    return tuple(sorted(cluster_ids))


def _merge_quotes(candidates: list[CandidatePack]) -> list[QuotePreview]:
    seen: set[tuple[str, str]] = set()
    merged: list[QuotePreview] = []
    for candidate in candidates:
        for quote in candidate.evidence_quotes:
            key = (quote.text.strip(), quote.permalink.strip())
            if not key[0] or key in seen:
                continue
            seen.add(key)
            merged.append(quote)
    return merged


def _merge_communities(candidates: list[CandidatePack]) -> list[str]:
    counts = Counter()
    for candidate in candidates:
        for community in [*candidate.top_communities, f"r/{candidate.matched_subreddit}"]:
            normalized = str(community).strip()
            if normalized:
                counts[normalized] += 1
    return [community for community, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _merge_topic_cluster_ids(candidates: list[CandidatePack]) -> list[str]:
    counts: Counter[str] = Counter()
    for candidate in candidates:
        for cluster_id in [*candidate.topic_cluster_ids, *([candidate.topic_cluster_id] if candidate.topic_cluster_id else [])]:
            if cluster_id:
                counts[cluster_id] += 1
    return [cluster_id for cluster_id, _ in counts.most_common()]


def _merge_named_topic_ids(candidates: list[CandidatePack]) -> list[str]:
    merged: list[str] = []
    for candidate in candidates:
        for topic_id in candidate.named_topic_ids:
            if topic_id and topic_id not in merged:
                merged.append(topic_id)
    return merged


def _merge_keywords(candidates: list[CandidatePack]) -> list[str]:
    merged: list[str] = []
    for candidate in candidates:
        for keyword in candidate.matched_keywords:
            if keyword and keyword not in merged:
                merged.append(keyword)
    return merged


def _merge_intents(candidates: list[CandidatePack]) -> list[str]:
    merged: list[str] = []
    for candidate in candidates:
        for intent in candidate.intent_tags:
            if intent and intent not in merged:
                merged.append(intent)
    return merged


def _pick_signal_level(candidates: list[CandidatePack]) -> SignalLevel:
    return max(candidates, key=lambda item: _LEVEL_ORDER[item.signal_level]).signal_level


def _pick_time_window(candidates: list[CandidatePack]) -> TimeWindow:
    return max(candidates, key=lambda item: _WINDOW_ORDER[item.time_window]).time_window


def _pick_why_now(candidates: list[CandidatePack]) -> WhyNowReason:
    return max(candidates, key=lambda item: _WHY_NOW_ORDER[item.why_now_reason]).why_now_reason


__all__ = ["build_grouped_candidates"]
