from __future__ import annotations

import re

from app.schemas.hotpost_card_candidates import CandidatePack


_TOKEN_RE = re.compile(r"[a-z0-9]{3,}|[\u4e00-\u9fff]{2,}", re.IGNORECASE)
_GENERIC = {
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
    "ecommerce",
    "seller",
    "sellers",
    "buy",
    "better",
    "best",
    "using",
    "with",
    "from",
    "that",
    "find",
    "one",
    "can",
}


def assess_breakdown_suggestion_coherence(items: list[CandidatePack]) -> dict[str, object]:
    anchor_sets = [_candidate_anchors(item) for item in items]
    shared = _shared_anchors(anchor_sets)
    supported = _quote_supported_anchors(items, shared)
    should_block = len(items) >= 2 and not supported
    reasons = ["weak_anchor_overlap"] if should_block else []
    return {
        "should_block": should_block,
        "reasons": reasons,
        "shared_anchors": sorted(supported),
    }


def _candidate_anchors(item: CandidatePack) -> set[str]:
    anchors: set[str] = set()
    for text in [*item.matched_keywords, item.query, item.title]:
        for token in _TOKEN_RE.findall(str(text).lower()):
            normalized = token.strip().lower()
            if normalized in _GENERIC:
                continue
            if normalized.isdigit():
                continue
            anchors.add(normalized)
    return anchors


def _shared_anchors(anchor_sets: list[set[str]]) -> set[str]:
    if not anchor_sets:
        return set()
    shared = set(anchor_sets[0])
    for anchors in anchor_sets[1:]:
        shared &= anchors
    return shared


def _quote_supported_anchors(items: list[CandidatePack], shared: set[str]) -> set[str]:
    if not shared:
        return set()
    supported: set[str] = set()
    for anchor in shared:
        if all(_anchor_supported_by_candidate(anchor, item) for item in items):
            supported.add(anchor)
    return supported


def _anchor_supported_by_candidate(anchor: str, item: CandidatePack) -> bool:
    needle = anchor.lower()
    for quote in item.evidence_quotes:
        text = str(quote.text).lower()
        if needle in text:
            return True
    for text in [*item.matched_keywords, item.query, item.title]:
        if needle in str(text).lower():
            return True
    return False


__all__ = ["assess_breakdown_suggestion_coherence"]
