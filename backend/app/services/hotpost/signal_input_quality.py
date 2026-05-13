from __future__ import annotations

from typing import Any

from app.schemas.hotpost_card_drafts import ValidationCardDraft


LOW_VALUE_QUOTE_MARKERS = (
    "i am a bot",
    "contact the moderators",
    "automoderator",
    "auto moderator",
    "hit me up if",
    "want to chat",
    "discord.gg/",
)
JOKE_OR_SATIRE_MARKERS = (
    "this is a joke",
    "joke article",
    "satire",
    "shitpost",
    "meme post",
    "not a real article",
)
COMPLAINT_ONLY_INTENTS = {
    "明确阻塞",
    "明确阻塞 / 吐槽到影响行动",
}
META_COMPLAINT_PATTERNS = (
    "click bait",
    "clickbait",
    "click baity",
    "clickbaity",
    "clickbait title",
    "clickbait titles",
    "clickbait headline",
    "clickbait headlines",
    "title",
    "what i found",
    "stop with",
)


def assess_signal_input_quality(bundle: dict[str, Any]) -> dict[str, Any]:
    quotes = bundle.get("evidence_quotes") or []
    thread_count = int(bundle.get("thread_count") or 0)
    community_count = int(bundle.get("community_count") or 0)
    title = str(bundle.get("title") or "")
    intent_tags = [str(tag).strip() for tag in (bundle.get("intent_tags") or []) if str(tag).strip()]
    substantive = [quote for quote in quotes if not _is_low_value_quote(str((quote or {}).get("text") or quote))]
    quote_texts = [str((quote or {}).get("text") or quote) for quote in quotes]
    reasons: list[str] = []
    if len(substantive) == 0:
        reasons.append("no_substantive_quotes")
    if thread_count <= 1 and len(substantive) <= 1:
        reasons.append("single_thread_weak_evidence")
    if community_count <= 1 and len(substantive) <= 1:
        reasons.append("single_community_weak_evidence")
    if (
        thread_count <= 1
        and community_count <= 1
        and len(substantive) <= 2
        and intent_tags
        and all(tag in COMPLAINT_ONLY_INTENTS for tag in intent_tags)
    ):
        reasons.append("complaint_only_no_market_signal")
    if _is_meta_community_complaint(title, quote_texts, thread_count, community_count):
        reasons.append("meta_community_complaint")
    if _is_joke_or_satire_low_signal(title, quote_texts, thread_count, community_count, len(substantive)):
        reasons.append("joke_or_satire_low_signal")
    return {
        "should_block": bool(reasons),
        "reasons": reasons,
        "substantive_quote_count": len(substantive),
        "raw_quote_count": len(quotes),
    }


def assess_signal_draft_input_quality(draft: ValidationCardDraft) -> dict[str, Any]:
    return assess_signal_input_quality(
        {
            "title": draft.title,
            "thread_count": draft.thread_count,
            "community_count": draft.community_count,
            "intent_tags": list(draft.intent_tags),
            "evidence_quotes": [quote.model_dump(mode="json") for quote in draft.evidence_quotes],
        }
    )


def _is_low_value_quote(text: str) -> bool:
    normalized = " ".join(str(text or "").lower().split())
    cjk_count = sum(1 for ch in normalized if "\u4e00" <= ch <= "\u9fff")
    if any(marker in normalized for marker in LOW_VALUE_QUOTE_MARKERS):
        return True
    if cjk_count == 0 and len(normalized) < 24:
        return True
    if cjk_count > 0 and cjk_count < 8:
        return True
    if normalized.count("?") >= 2 and len(normalized) < 120:
        return True
    return False


def _is_meta_community_complaint(
    title: str,
    quote_texts: list[str],
    thread_count: int,
    community_count: int,
) -> bool:
    if thread_count > 1 or community_count > 1:
        return False
    haystack = " ".join([title, *quote_texts]).lower()
    if not any(pattern in haystack for pattern in META_COMPLAINT_PATTERNS):
        return False
    complaint_markers = (
        "stop with",
        "getting old",
        "clickbait",
        "click bait",
        "click baity",
        "clickbaity",
        "headline",
        "what i found",
    )
    return any(marker in haystack for marker in complaint_markers)


def _is_joke_or_satire_low_signal(
    title: str,
    quote_texts: list[str],
    thread_count: int,
    community_count: int,
    substantive_quote_count: int,
) -> bool:
    if thread_count > 1 or community_count > 1:
        return False
    haystack = " ".join([title, *quote_texts]).lower()
    if not any(marker in haystack for marker in JOKE_OR_SATIRE_MARKERS):
        return False
    return substantive_quote_count <= 2


__all__ = ["assess_signal_draft_input_quality", "assess_signal_input_quality"]
