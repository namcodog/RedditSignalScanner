from __future__ import annotations

import re

from app.schemas.hotpost_clues import WritingCardDetail
from app.services.hotpost.card_payload_store import load_published_cards


_ASCII_RE = re.compile(r"[a-z0-9]{3,}", re.IGNORECASE)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_STOP = {"大家", "真正", "问题", "工具", "系统", "团队", "功能", "不是", "一个", "开始", "已经", "如果", "因为"}


def audit_breakdown_overlap(*, threshold: float = 0.16) -> dict[str, object]:
    cards = [
        WritingCardDetail.model_validate(item)
        for item in load_published_cards()
        if item.get("card_type") == "write"
    ]
    pairs = []
    for index, left in enumerate(cards):
        for right in cards[index + 1 :]:
            if left.source_scope_id != right.source_scope_id:
                continue
            score, shared = _overlap_score(left, right)
            if score < threshold:
                continue
            pairs.append(
                {
                    "left_card_id": left.card_id,
                    "right_card_id": right.card_id,
                    "source_scope_id": left.source_scope_id,
                    "score": round(score, 4),
                    "shared_terms": shared[:8],
                    "left_title": left.title,
                    "right_title": right.title,
                }
            )
    pairs.sort(key=lambda item: item["score"], reverse=True)
    return {"pair_count": len(pairs), "pairs": pairs}


def _overlap_score(left: WritingCardDetail, right: WritingCardDetail) -> tuple[float, list[str]]:
    left_terms = _terms(left.title, left.detail.thesis, left.summary_line)
    right_terms = _terms(right.title, right.detail.thesis, right.summary_line)
    if not left_terms or not right_terms:
        return 0.0, []
    shared = sorted(left_terms & right_terms)
    score = len(shared) / min(len(left_terms), len(right_terms))
    return score, shared


def _terms(*parts: str) -> set[str]:
    terms: set[str] = set()
    for part in parts:
        text = str(part)
        for token in _ASCII_RE.findall(text):
            normalized = token.lower()
            if normalized in _STOP:
                continue
            terms.add(normalized)
        for block in _CJK_RE.findall(text):
            for index in range(len(block) - 1):
                token = block[index : index + 2]
                if token in _STOP:
                    continue
                terms.add(token)
    return terms


__all__ = ["audit_breakdown_overlap"]
