from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Optional, Any

from app.services.hotpost.compare_targets import infer_compare_targets
from app.services.hotpost.rules import normalize_text


def _normalize_thread_key(value: Any) -> str:
    return normalize_text(str(value or ""))


@dataclass(slots=True)
class CompareEvidenceMatrix:
    evidence_cards: list[dict[str, Any]]
    left_target:Optional[ str]
    right_target:Optional[ str]
    valid_evidence_count: int
    unique_thread_count: int
    left_count: int
    right_count: int
    render_mode: str
    insufficient_reason:Optional[ str]


def build_compare_evidence_matrix(
    *,
    evidence_cards: list[dict[str, Any]],
    query: str,
    keywords: list[str],
    query_family:Optional[ str],
) ->Optional[ CompareEvidenceMatrix]:
    if normalize_text(query_family or "") != "comparison_complaint_discovery":
        return None
    compare_targets = infer_compare_targets(query, keywords)
    left_target = compare_targets[0] if len(compare_targets) >= 1 else None
    right_target = compare_targets[1] if len(compare_targets) >= 2 else None
    unique_threads = {
        _normalize_thread_key(card.get("thread_key") or card.get("url") or card.get("quote"))
        for card in evidence_cards
        if _normalize_thread_key(card.get("thread_key") or card.get("url") or card.get("quote"))
    }
    target_counts: Counter[str] = Counter()
    for card in evidence_cards:
        normalized_target = _normalize_thread_key(card.get("side") or card.get("target"))
        if normalized_target:
            target_counts[normalized_target] += 1
    left_count = int(target_counts.get(normalize_text(left_target), 0)) if left_target else 0
    right_count = int(target_counts.get(normalize_text(right_target), 0)) if right_target else 0

    render_mode = "compare"
    insufficient_reason:Optional[ str] = None
    if not evidence_cards:
        render_mode = "no_hit"
        insufficient_reason = "no_valid_compare_evidence"
    elif left_count < 2 or right_count < 2:
        render_mode = "insufficient_evidence"
        insufficient_reason = "compare_sides_incomplete"
    elif len(unique_threads) < 3:
        render_mode = "insufficient_evidence"
        insufficient_reason = "compare_threads_below_threshold"

    return CompareEvidenceMatrix(
        evidence_cards=evidence_cards,
        left_target=left_target,
        right_target=right_target,
        valid_evidence_count=len(evidence_cards),
        unique_thread_count=len(unique_threads),
        left_count=left_count,
        right_count=right_count,
        render_mode=render_mode,
        insufficient_reason=insufficient_reason,
    )


__all__ = ["CompareEvidenceMatrix", "build_compare_evidence_matrix"]
