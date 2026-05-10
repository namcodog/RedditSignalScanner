from __future__ import annotations

from typing import Callable

from app.services.hotpost.rules import normalize_text


QUESTION_MARKERS = ("?", "？", "anyone", "how do i", "怎么", "为什么", "谁能", "求助")
COMPARE_MARKERS = (" vs ", " versus ", " better than ", " prefer ", " over ", " 比 ", " 不如 ", " 更")
COMPARE_FAILURE_MARKERS = (
    "drops constraints",
    "drop constraints",
    "drops parts",
    "ignores parts",
    "forgets earlier requirements",
    "forgets instructions",
    "loses context",
    "lost context",
    "misses parts",
    "misses half",
    "only does the first half",
    "derails after",
    "does not",
    "doesn't",
    "worse than",
    "不如",
    "听不懂",
    "漏约束",
    "丢约束",
)
COMPARE_CAPABILITY_MARKERS = (
    "follows the whole brief",
    "keeps the whole brief",
    "keeps track",
    "keeps full context",
    "full context",
    "full brief in mind",
    "retains context",
    "respects constraints",
    "handles multi-step",
    "follows all requirements",
    "follow instructions",
    "instruction following",
    "follows long instructions",
    "follow long instructions",
    "end to end",
)


def classify_quote_type(quote: str, *, complaint_detector: Callable[[str], bool]) -> str:
    normalized = normalize_text(quote)
    if not normalized:
        return "neutral"
    if any(marker in normalized for marker in QUESTION_MARKERS):
        return "question"
    is_compare = any(marker in normalized for marker in COMPARE_MARKERS)
    has_complaint = complaint_detector(quote)
    if is_compare and has_complaint:
        return "compare"
    if has_complaint:
        return "complaint"
    if is_compare:
        return "compare"
    return "neutral"


def _looks_like_positive_compare_quote(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized or any(marker in normalized for marker in QUESTION_MARKERS):
        return False
    return any(marker in normalized for marker in COMPARE_CAPABILITY_MARKERS)


def looks_like_positive_compare_quote(text: str) -> bool:
    return _looks_like_positive_compare_quote(text)


def _compare_prefers_target(*, normalized_quote: str, preferred: str, other: str) -> bool:
    preferred_norm = normalize_text(preferred)
    other_norm = normalize_text(other)
    if not preferred_norm or not other_norm:
        return False
    preferred_pos = normalized_quote.find(preferred_norm)
    other_pos = normalized_quote.find(other_norm)
    better_pos = normalized_quote.find("better than")
    if preferred_pos >= 0 and other_pos >= 0 and better_pos >= 0 and preferred_pos < better_pos < other_pos:
        return True
    over_pos = normalized_quote.find(" over ")
    prefer_pos = normalized_quote.find("prefer")
    if preferred_pos >= 0 and other_pos >= 0 and over_pos >= 0 and preferred_pos < over_pos < other_pos:
        return True
    if prefer_pos >= 0 and preferred_pos >= prefer_pos and other_pos >= 0 and (
        over_pos < 0 or preferred_pos < over_pos < other_pos
    ):
        return True
    patterns = (
        f"{preferred_norm} better than {other_norm}",
        f"{preferred_norm} over {other_norm}",
        f"prefer {preferred_norm} over {other_norm}",
        f"prefer {preferred_norm}",
        f"{other_norm} worse than {preferred_norm}",
        f"{preferred_norm} 比 {other_norm}",
    )
    return any(pattern in normalized_quote for pattern in patterns)


def build_compare_side_entries(
    *,
    quote: str,
    compare_targets: list[str],
    complaint_detector: Callable[[str], bool],
) -> list[tuple[str, str]]:
    # Compare 题的核心不是“这句相关吗”，而是“这句到底站哪边、在夸还是在骂”。
    if len(compare_targets) < 2:
        return []
    normalized_quote = normalize_text(quote)
    if not normalized_quote:
        return []
    left, right = compare_targets[0], compare_targets[1]
    entries: list[tuple[str, str]] = []

    def append_entry(side: str, stance: str) -> None:
        item = (side, stance)
        if item not in entries:
            entries.append(item)

    if _compare_prefers_target(normalized_quote=normalized_quote, preferred=left, other=right):
        append_entry(left, "prefer")
        append_entry(right, "dislike")
    if _compare_prefers_target(normalized_quote=normalized_quote, preferred=right, other=left):
        append_entry(right, "prefer")
        append_entry(left, "dislike")
    if not entries:
        left_pos = normalized_quote.find(normalize_text(left))
        right_pos = normalized_quote.find(normalize_text(right))
        left_window = normalized_quote[max(left_pos - 48, 0) : left_pos + len(normalize_text(left)) + 80] if left_pos >= 0 else ""
        right_window = normalized_quote[max(right_pos - 48, 0) : right_pos + len(normalize_text(right)) + 80] if right_pos >= 0 else ""
        left_positive = _looks_like_positive_compare_quote(left_window)
        right_positive = _looks_like_positive_compare_quote(right_window)
        left_negative = complaint_detector(left_window) or any(marker in left_window for marker in COMPARE_FAILURE_MARKERS)
        right_negative = complaint_detector(right_window) or any(marker in right_window for marker in COMPARE_FAILURE_MARKERS)
        if left_positive and right_negative:
            append_entry(left, "prefer")
            append_entry(right, "dislike")
        elif right_positive and left_negative:
            append_entry(right, "prefer")
            append_entry(left, "dislike")
    if not entries:
        left_pos = normalized_quote.find(normalize_text(left))
        right_pos = normalized_quote.find(normalize_text(right))
        if left_pos >= 0 and right_pos >= 0 and (" while " in normalized_quote or " but " in normalized_quote):
            split_text = normalized_quote.split(" while ", 1) if " while " in normalized_quote else normalized_quote.split(" but ", 1)
            left_clause = split_text[0]
            right_clause = split_text[1] if len(split_text) > 1 else ""
            if left_pos < right_pos:
                if _looks_like_positive_compare_quote(left_clause) and any(marker in right_clause for marker in COMPARE_FAILURE_MARKERS):
                    append_entry(left, "prefer")
                    append_entry(right, "dislike")
            else:
                if any(marker in left_clause for marker in COMPARE_FAILURE_MARKERS) and _looks_like_positive_compare_quote(right_clause):
                    append_entry(left, "dislike")
                    append_entry(right, "prefer")
    if entries:
        return entries

    mention_count = sum(1 for side in compare_targets[:2] if normalize_text(side) in normalized_quote)
    for side in compare_targets[:2]:
        normalized_side = normalize_text(side)
        if not normalized_side or normalized_side not in normalized_quote:
            continue
        if mention_count == 1 and (complaint_detector(quote) or any(marker in normalized_quote for marker in COMPARE_FAILURE_MARKERS)):
            append_entry(side, "complaint")
        elif mention_count == 1 and _looks_like_positive_compare_quote(quote):
            append_entry(side, "praise")
    return entries


__all__ = [
    "COMPARE_MARKERS",
    "QUESTION_MARKERS",
    "build_compare_side_entries",
    "classify_quote_type",
    "looks_like_positive_compare_quote",
]
