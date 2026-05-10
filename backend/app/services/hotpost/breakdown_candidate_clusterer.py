from __future__ import annotations

import re
from collections import Counter, defaultdict
from hashlib import sha1
from itertools import combinations

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_card_review import BreakdownSuggestion
from app.schemas.hotpost_signal import SourceScopeId
from app.services.hotpost.breakdown_suggestion_quality import assess_breakdown_suggestion_coherence
from app.services.hotpost.card_candidate_store import list_candidates


_ALLOWED_TOPIC_PACKS = {"selection-signals", "agent-builder", "organic-discovery", "paid-economics"}
_FOCUS_TOKEN_RE = re.compile(r"[a-z0-9]{3,}|[\u4e00-\u9fff]{2,}", re.IGNORECASE)
_FOCUS_GENERIC = {
    "listing",
    "search",
    "top",
    "hot",
    "new",
    "rising",
    "day",
    "week",
    "agent",
    "agents",
    "tool",
    "tools",
    "workflow",
    "workflows",
    "product",
    "products",
    "ai",
    "code",
    "coding",
    "builder",
    "automation",
    "with",
    "from",
    "that",
    "this",
    "what",
    "why",
    "how",
    "you",
    "people",
    "teams",
    "report",
    "budget",
}
_PACK_HYPOTHESIS = {
    "selection-signals": "这些讨论表面在找不同东西，背后可能都在筛同一种购买标准{focus_suffix}。",
    "agent-builder": "这些讨论表面在聊不同能力，背后可能都卡在同一个落地门槛{focus_suffix}。",
    "organic-discovery": "这些讨论表面在聊流量和内容变化，背后可能都卡在同一种分发逻辑变动{focus_suffix}。",
    "paid-economics": "这些讨论表面在聊不同投放问题，背后可能都卡在同一种投放经济账{focus_suffix}。",
}


def list_breakdown_suggestions(
    source_scope_id:Optional[ SourceScopeId] = None,
    *,
    limit: int = 20,
) -> list[BreakdownSuggestion]:
    eligible_items = [item for item in list_candidates(source_scope_id) if _eligible(item)]
    scoped_groups: dict[tuple[str, str, str], list[CandidatePack]] = defaultdict(list)
    scoped_candidates: dict[tuple[str, str], list[CandidatePack]] = defaultdict(list)
    for item in eligible_items:
        scoped_groups[(item.source_scope_id, item.topic_pack_id or "", _focus_key(item))].append(item)
        scoped_candidates[(item.source_scope_id, item.topic_pack_id or "")].append(item)

    candidate_groups: list[list[CandidatePack]] = list(scoped_groups.values())
    for items in scoped_candidates.values():
        candidate_groups.extend(_pairwise_anchor_groups(items))

    suggestions: list[BreakdownSuggestion] = []
    seen_groups: set[tuple[str, ...]] = set()
    for items in candidate_groups:
        deduped = _dedupe_candidates(items)
        group_key = tuple(sorted(item.candidate_id for item in deduped))
        if len(group_key) < 2 or group_key in seen_groups:
            continue
        seen_groups.add(group_key)
        suggestion = _build_suggestion(deduped, _group_focus_key(deduped))
        if suggestion is not None:
            suggestions.append(suggestion)

    ranked = _drop_subset_suggestions(suggestions)
    ranked.sort(key=lambda item: (item.evidence_score, item.thread_count, item.community_count), reverse=True)
    return ranked[:limit]


def get_breakdown_suggestion(suggestion_id: str) -> BreakdownSuggestion:
    for item in list_breakdown_suggestions(limit=200):
        if item.suggestion_id == suggestion_id:
            return item
    raise LookupError(f"Breakdown suggestion not found: {suggestion_id}")


def _build_suggestion(items: list[CandidatePack], focus_key: str) ->Optional[ BreakdownSuggestion]:
    deduped = _dedupe_candidates(items)
    post_ids = {item.post_id for item in deduped}
    quotes = {quote.text.strip() for item in deduped for quote in item.evidence_quotes if quote.text.strip()}
    communities = {item.matched_subreddit for item in deduped}
    if not _meets_breakdown_evidence_bar(deduped, post_ids, communities, quotes):
        return None
    quality = assess_breakdown_suggestion_coherence(deduped)
    if bool(quality["should_block"]):
        return None
    ordered = sorted(deduped, key=lambda item: (item.created_at, item.candidate_id))
    candidate_ids = [item.candidate_id for item in ordered]
    digest = sha1("|".join(candidate_ids).encode("utf-8")).hexdigest()[:10]
    topic_pack_id = deduped[0].topic_pack_id or "unknown"
    return BreakdownSuggestion(
        suggestion_id=f"suggestion-{deduped[0].source_scope_id}-{digest}",
        source_scope_id=deduped[0].source_scope_id,
        topic_pack_id=topic_pack_id,
        candidate_ids=candidate_ids,
        thread_count=len(post_ids),
        community_count=len(communities),
        intent_tags=_merge_intents(deduped),
        evidence_score=_evidence_score(deduped, len(communities), len(quotes)),
        hypothesis=_build_hypothesis(topic_pack_id, focus_key),
        reason_codes=_reason_codes(deduped, communities, quality["shared_anchors"]),
    )


def _pairwise_anchor_groups(items: list[CandidatePack]) -> list[list[CandidatePack]]:
    deduped = _dedupe_candidates(items)
    groups: list[list[CandidatePack]] = []
    for left, right in combinations(deduped, 2):
        quality = assess_breakdown_suggestion_coherence([left, right])
        if bool(quality["should_block"]) or not quality["shared_anchors"]:
            continue
        groups.append([left, right])
    return groups


def _eligible(item: CandidatePack) -> bool:
    return (
        bool(item.topic_pack_id)
        and item.topic_pack_id in _ALLOWED_TOPIC_PACKS
        and item.time_window in {"24h", "7d"}
        and len(item.evidence_quotes) >= 1
    )


def _focus_key(item: CandidatePack) -> str:
    keywords = [_normalize(text) for text in item.matched_keywords if _normalize(text)]
    if keywords:
        return keywords[0]
    if not item.query.startswith("listing:"):
        normalized_query = _normalize(item.query)
        if normalized_query:
            return normalized_query
    anchor = _best_focus_anchor(item)
    if anchor:
        return anchor
    return _normalize(item.query) or _normalize(item.title)


def _group_focus_key(items: list[CandidatePack]) -> str:
    quality = assess_breakdown_suggestion_coherence(items)
    shared = [anchor for anchor in quality["shared_anchors"] if _normalize(anchor)]
    focus_counts: Counter[str] = Counter()
    for item in items:
        focus = _focus_key(item)
        if focus:
            focus_counts[focus] += 1
    if focus_counts:
        focus_key, count = focus_counts.most_common(1)[0]
        if count >= 2 and not (len(shared) >= 2 and focus_key in shared):
            return focus_key
    if shared:
        ordered = _ordered_shared_anchors(items, shared)
        if len(ordered) >= 2:
            combined = " ".join(ordered[:2])
            if len(combined) <= 28:
                return combined
        return ordered[0]
    if focus_counts:
        return focus_counts.most_common(1)[0][0]
    return _focus_key(items[0]) if items else ""


def _ordered_shared_anchors(items: list[CandidatePack], shared: list[str]) -> list[str]:
    allowed = {anchor.lower() for anchor in shared}
    ordered: list[str] = []
    seen: set[str] = set()
    for item in items:
        texts = [item.title, *[quote.text for quote in item.evidence_quotes]]
        for text in texts:
            for token in _FOCUS_TOKEN_RE.findall(str(text)):
                normalized = token.strip().lower()
                if normalized not in allowed or normalized in seen:
                    continue
                seen.add(normalized)
                ordered.append(normalized)
    if ordered:
        return ordered
    return sorted(allowed)


def _normalize(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def _best_focus_anchor(item: CandidatePack) -> str:
    counts: Counter[str] = Counter()
    capitalized: set[str] = set()
    for text, weight in [(item.title, 3), *[(quote.text, 2) for quote in item.evidence_quotes]]:
        for token in _FOCUS_TOKEN_RE.findall(str(text)):
            normalized = token.strip().lower()
            if normalized in _FOCUS_GENERIC or normalized.isdigit():
                continue
            if token != normalized:
                capitalized.add(normalized)
            counts[normalized] += weight
    if not counts:
        return ""
    anchor, _ = max(counts.items(), key=lambda pair: (pair[0] in capitalized, pair[1], len(pair[0]), pair[0]))
    return anchor


def _dedupe_candidates(items: list[CandidatePack]) -> list[CandidatePack]:
    seen: set[str] = set()
    ordered: list[CandidatePack] = []
    for item in sorted(items, key=lambda candidate: candidate.collected_at, reverse=True):
        if item.candidate_id in seen:
            continue
        seen.add(item.candidate_id)
        ordered.append(item)
    return ordered


def _drop_subset_suggestions(items: list[BreakdownSuggestion]) -> list[BreakdownSuggestion]:
    kept: list[BreakdownSuggestion] = []
    ranked = sorted(
        items,
        key=lambda item: (len(item.candidate_ids), item.evidence_score, item.thread_count, item.community_count),
        reverse=True,
    )
    for item in ranked:
        candidate_ids = set(item.candidate_ids)
        if any(
            kept_item.source_scope_id == item.source_scope_id
            and kept_item.topic_pack_id == item.topic_pack_id
            and candidate_ids < set(kept_item.candidate_ids)
            for kept_item in kept
        ):
            continue
        kept.append(item)
    return kept


def _merge_intents(items: list[CandidatePack]) -> list[str]:
    merged: list[str] = []
    for item in items:
        for tag in item.intent_tags:
            if tag not in merged:
                merged.append(tag)
    return merged


def _evidence_score(items: list[CandidatePack], community_count: int, quote_count: int) -> int:
    return min(100, 30 + len(items) * 20 + min(community_count, 3) * 10 + min(quote_count, 4) * 5)


def _build_hypothesis(topic_pack_id: str, focus_key: str) -> str:
    template = _PACK_HYPOTHESIS.get(topic_pack_id, "这些讨论可能共同指向同一个更深层问题。")
    focus_suffix = _focus_suffix(focus_key)
    return template.format(focus_suffix=focus_suffix)


def _focus_suffix(focus_key: str) -> str:
    cleaned = _normalize(focus_key)
    if not cleaned or any(token in cleaned for token in ("listing:", "search:", "top:", "hot:", "rising:", "day", "week")):
        return ""
    if len(cleaned) > 28:
        return ""
    return f"：{cleaned}"


def _reason_codes(items: list[CandidatePack], communities: set[str], shared_anchors: object) -> list[str]:
    codes = ["same_scope", "same_topic_pack", "multi_post_evidence"]
    overlap = set(_normalize(text) for item in items for text in item.matched_keywords if _normalize(text))
    if overlap:
        codes.append("keyword_overlap")
    if shared_anchors:
        codes.append("coherent_anchor_overlap")
    if len(communities) >= 2:
        codes.append("cross_community")
    if len(_merge_intents(items)) >= 2:
        codes.append("intent_mix")
    return codes


def _meets_breakdown_evidence_bar(
    items: list[CandidatePack],
    post_ids: set[str],
    communities: set[str],
    quotes: set[str],
) -> bool:
    return (
        len(items) >= 2
        and len(post_ids) >= 2
        and len(quotes) >= 3
        and (len(communities) >= 2 or len(post_ids) >= 3)
    )


__all__ = ["get_breakdown_suggestion", "list_breakdown_suggestions"]
