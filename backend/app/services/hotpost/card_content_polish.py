from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.hotpost.client_copy_normalizer import polish_generated_text, polish_nested_strings
from app.services.hotpost.legacy_signal_copy_builder import (
    build_continue_signal as _build_continue_signal,
    build_signal_why_now as _build_signal_why_now,
    build_signal_why_test_now as _build_signal_why_test_now,
    build_stop_signal as _build_stop_signal,
)
from app.services.hotpost.published_card_overrides import PUBLISHED_CARD_OVERRIDES


def polish_published_card(card: dict[str, Any], *, preserve_semantic_fields: bool = True) -> dict[str, Any]:
    polished = deepcopy(card)
    overrides = PUBLISHED_CARD_OVERRIDES.get(str(polished.get("card_id") or ""))
    if overrides:
        _deep_merge(polished, overrides)

    polished["title"] = polish_generated_text(str(polished.get("title") or ""), field_name="title")
    polished["summary_line"] = polish_generated_text(str(polished.get("summary_line") or ""), field_name="summary_line")
    polished["audience"] = polish_generated_text(str(polished.get("audience") or ""), field_name="audience")
    if not preserve_semantic_fields:
        polished["why_now"] = _build_signal_why_now(
            source_communities=list((polished.get("source_module") or {}).get("primary_communities") or []),
            thread_count=int(polished.get("thread_count") or (polished.get("source_module") or {}).get("thread_count") or 1),
            community_count=int(polished.get("community_count") or (polished.get("source_module") or {}).get("community_count") or 1),
            intent_tags=[str(item) for item in (polished.get("intent_tags") or [])],
            why_now_reason=str(polished.get("why_now_reason") or ""),
        )

    detail = polished.get("detail") or {}
    if isinstance(detail, dict):
        if preserve_semantic_fields:
            polished["detail"] = detail
            return polished
        if polished.get("card_type") == "validate":
            detail["why_test_now"] = _build_signal_why_test_now(
                source_communities=list((polished.get("source_module") or {}).get("primary_communities") or []),
                thread_count=int(polished.get("thread_count") or (polished.get("source_module") or {}).get("thread_count") or 1),
                community_count=int(polished.get("community_count") or (polished.get("source_module") or {}).get("community_count") or 1),
                intent_tags=[str(item) for item in (polished.get("intent_tags") or [])],
                why_now_reason=str(polished.get("why_now_reason") or ""),
            )
            detail["continue_signal"] = _build_continue_signal([str(item) for item in (polished.get("intent_tags") or [])])
            detail["stop_signal"] = _build_stop_signal()
        polished["detail"] = polish_nested_strings(detail)

    return polished


def _deep_merge(target: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value


__all__ = [
    "polish_generated_text",
    "polish_published_card",
]
