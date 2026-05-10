from __future__ import annotations

import re
from typing import Any, Callable

from app.services.hotpost.rules import normalize_text
from app.services.hotpost.symptom_phrase import extract_symptom_phrase


_CJK_TEXT_RE = re.compile(r"[\u3400-\u9fff]")


def normalize_quote_text(value: Any, *, max_chars: int = 160) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def quote_signature(text: str) -> str:
    return normalize_text(text)[:120]


def looks_like_human_quote(text: str) -> bool:
    quote = normalize_quote_text(text, max_chars=240)
    if len(quote) < 18:
        return False
    letters = sum(1 for ch in quote if ch.isalpha() or _CJK_TEXT_RE.search(ch))
    digits = sum(1 for ch in quote if ch.isdigit())
    if letters < 6:
        return False
    if digits > letters and " " not in quote and not _CJK_TEXT_RE.search(quote):
        return False
    return True


def build_voice_first_top_quotes(
    evidence_units: list[dict[str, Any]],
    *,
    limit: int,
    complaint_detector: Callable[[str], bool],
) -> list[dict[str, Any]]:
    # voices-first 的核心规则：先拿“真像人话、真在抱怨”的原话，再考虑排序和去重。
    if limit <= 0:
        return []
    scoped = [unit for unit in evidence_units if bool(unit.get("valid"))]
    if not scoped:
        scoped = [
            unit
            for unit in evidence_units
            if complaint_detector(str(unit.get("quote") or ""))
            and looks_like_human_quote(str(unit.get("quote") or ""))
        ]
    if not scoped:
        return []

    selected: list[dict[str, Any]] = []
    seen_quotes: set[str] = set()
    seen_threads: set[str] = set()

    def normalize_thread_key(value: Any) -> str:
        return normalize_text(str(value or ""))

    def append_quote(unit: dict[str, Any], *, allow_thread_repeat: bool) -> None:
        if len(selected) >= limit:
            return
        quote = normalize_quote_text(unit.get("quote"), max_chars=220)
        if not quote:
            return
        normalized_quote = quote_signature(quote)
        if not normalized_quote or normalized_quote in seen_quotes:
            return
        thread_key = normalize_thread_key(unit.get("thread_key") or unit.get("url") or quote)
        if not allow_thread_repeat and thread_key and thread_key in seen_threads:
            return
        quote_id = str(unit.get("quote_id") or "").strip() or f"voice-{len(selected) + 1}"
        selected.append(
            {
                "quote": quote,
                "score": int(unit.get("score") or 0),
                "subreddit": str(unit.get("subreddit") or "").strip() or None,
                "url": str(unit.get("url") or "").strip() or None,
                "thread_url": str(unit.get("url") or "").strip() or None,
                "thread_id": thread_key or None,
                "quote_id": quote_id,
                "created_utc": unit.get("created_utc"),
                "why_important": extract_symptom_phrase(quote),
            }
        )
        seen_quotes.add(normalized_quote)
        if thread_key:
            seen_threads.add(thread_key)

    for unit in scoped:
        append_quote(unit, allow_thread_repeat=False)
    if len(selected) < limit:
        for unit in scoped:
            append_quote(unit, allow_thread_repeat=True)
    return selected[:limit]


__all__ = [
    "build_voice_first_top_quotes",
    "looks_like_human_quote",
    "normalize_quote_text",
    "quote_signature",
]
