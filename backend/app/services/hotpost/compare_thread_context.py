from __future__ import annotations

from collections.abc import Callable

from app.services.hotpost.compare_quote_signals import (
    build_compare_side_entries,
    looks_like_positive_compare_quote,
)
from app.services.hotpost.rant_evidence_helpers import focus_matches_quote
from app.services.hotpost.rules import normalize_text


def resolve_compare_side_entries(
    *,
    quote: str,
    compare_targets: list[str],
    complaint_detector: Callable[[str], bool],
    thread_title: str = "",
    thread_body: str = "",
) -> list[dict[str, object]]:
    explicit_entries = build_compare_side_entries(
        quote=quote,
        compare_targets=compare_targets,
        complaint_detector=complaint_detector,
    )
    if explicit_entries:
        return [
            {
                "side": side,
                "stance": stance,
                "side_resolution_source": "explicit_span",
                "confidence": 0.95,
            }
            for side, stance in explicit_entries
        ]

    thread_frame = " ".join(part for part in [thread_title, thread_body] if str(part or "").strip()).strip()
    if not thread_frame:
        return []

    frame_entries = build_compare_side_entries(
        quote=thread_frame,
        compare_targets=compare_targets,
        complaint_detector=complaint_detector,
    )
    normalized_quote = normalize_text(quote)
    if not frame_entries or not normalized_quote:
        return []

    if not (
        complaint_detector(quote)
        or looks_like_positive_compare_quote(quote)
        or any(marker in normalized_quote for marker in {"same here", "same", "agree", "exactly", "me too"})
    ):
        return []

    return [
        {
            "side": side,
            "stance": stance,
            "side_resolution_source": "thread_frame",
            "confidence": 0.72,
        }
        for side, stance in frame_entries
    ]


def resolve_focus_match(
    *,
    quote: str,
    focus_terms: list[str],
    thread_title: str = "",
    thread_body: str = "",
) ->Optional[ tuple[bool, str]]:
    if not focus_terms:
        return True, None
    normalized_quote = normalize_text(quote)
    if normalized_quote and focus_matches_quote(normalized_quote=normalized_quote, focus_terms=focus_terms):
        return True, "explicit_span"

    thread_frame = " ".join(part for part in [thread_title, thread_body] if str(part or "").strip()).strip()
    normalized_frame = normalize_text(thread_frame)
    if normalized_frame and focus_matches_quote(normalized_quote=normalized_frame, focus_terms=focus_terms):
        return True, "thread_frame"
    return False, None


__all__ = ["resolve_compare_side_entries", "resolve_focus_match"]
