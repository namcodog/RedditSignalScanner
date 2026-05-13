from __future__ import annotations

from typing import Optional, Any

from app.services.hotpost.card_content_generator import (
    build_backfill_draft,
    generate_card_content,
    refresh_breakdown_content,
)
from app.schemas.hotpost_card_drafts import WritingCardDraft
from app.schemas.hotpost_clues import WritingDetail
from app.schemas.hotpost_validate_details import normalize_validation_detail_payload


_TOP_LEVEL_SEMANTIC_FIELDS = (
    "title",
    "summary_line",
    "audience",
    "why_now",
)


async def refresh_published_card_semantics(item: dict[str, Any]) -> dict[str, Any]:
    draft = build_backfill_draft(item)
    if isinstance(draft, WritingCardDraft):
        generated = await refresh_breakdown_content(draft)
    else:
        generated = await generate_card_content(draft, allow_breakdown=False)
    regenerated = _semantic_payload_from_draft(generated)
    return merge_semantic_refresh(item, regenerated)


def merge_semantic_refresh(original: dict[str, Any], regenerated: dict[str, Any]) -> dict[str, Any]:
    updated = dict(original)

    for field in _TOP_LEVEL_SEMANTIC_FIELDS:
        if regenerated.get(field):
            updated[field] = regenerated[field]

    regenerated_detail = regenerated.get("detail")
    if isinstance(regenerated_detail, dict):
        lane = str(original.get("lane") or updated.get("lane") or "signal")
        detail = dict(original.get("detail") or {})
        detail.pop("min_test_action", None)
        for field, value in regenerated_detail.items():
            if field == "min_test_action":
                continue
            detail[field] = value
        updated["detail"] = _normalize_refreshed_detail(
            card_type=str(original.get("card_type") or updated.get("card_type") or ""),
            lane=lane,
            detail=detail,
        )

    _refresh_preview_quote(updated, original, regenerated)
    _preserve_publish_identity(updated, original)
    return updated


def select_cards_for_semantic_refresh(
    cards: list[dict[str, Any]],
    *,
    card_ids:Optional[ set[str]] = None,
    lanes:Optional[ set[str]] = None,
    card_types:Optional[ set[str]] = None,
    limit:Optional[ int] = None,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for card in cards:
        if card_ids and str(card.get("card_id") or "") not in card_ids:
            continue
        if lanes and str(card.get("lane") or "") not in lanes:
            continue
        if card_types and str(card.get("card_type") or "") not in card_types:
            continue
        selected.append(card)
        if limit is not None and len(selected) >= limit:
            break
    return selected


def semantic_change_summary(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    detail_before = before.get("detail") if isinstance(before.get("detail"), dict) else {}
    detail_after = after.get("detail") if isinstance(after.get("detail"), dict) else {}
    changed: dict[str, Any] = {}

    for field in _TOP_LEVEL_SEMANTIC_FIELDS:
        if before.get(field) != after.get(field):
            changed[field] = {"before": before.get(field), "after": after.get(field)}

    detail_changes = {}
    for field, after_value in detail_after.items():
        if field == "min_test_action":
            continue
        if detail_before.get(field) != after_value:
            detail_changes[field] = {"before": detail_before.get(field), "after": after_value}
    if detail_changes:
        changed["detail"] = detail_changes

    return changed


def _refresh_preview_quote(
    updated: dict[str, Any],
    original: dict[str, Any],
    regenerated: dict[str, Any],
) -> None:
    regenerated_preview = regenerated.get("preview_quote")
    if not isinstance(regenerated_preview, dict):
        return
    original_quotes = [quote for quote in original.get("quotes") or [] if isinstance(quote, dict)]
    original_permalinks = {str(quote.get("permalink") or "") for quote in original_quotes}
    preview_permalink = str(regenerated_preview.get("permalink") or "")
    if preview_permalink not in original_permalinks:
        return
    updated["preview_quote"] = regenerated_preview

    regenerated_quotes = [quote for quote in regenerated.get("quotes") or [] if isinstance(quote, dict)]
    regenerated_permalinks = {str(quote.get("permalink") or "") for quote in regenerated_quotes}
    if regenerated_permalinks == original_permalinks:
        updated["quotes"] = regenerated_quotes


def _preserve_publish_identity(updated: dict[str, Any], original: dict[str, Any]) -> None:
    for field in (
        "card_id",
        "signal_id",
        "card_type",
        "lane",
        "category_id",
        "published_at",
        "source_event_at",
        "source_link",
        "source_module",
        "source_scope_id",
        "source_scope_name",
        "source_domain_id",
        "source_domain_name",
        "why_now_reason",
        "signal_level",
        "intent_tags",
        "top_community",
        "thread_count",
        "community_count",
    ):
        if field in original:
            updated[field] = original[field]


def _semantic_payload_from_draft(draft: Any) -> dict[str, Any]:
    quotes = [quote.model_dump(mode="json") for quote in draft.evidence_quotes]
    return {
        "title": draft.title,
        "summary_line": draft.summary_line,
        "audience": draft.audience,
        "why_now": draft.why_now,
        "preview_quote": quotes[0] if quotes else None,
        "quotes": quotes,
        "detail": draft.detail.model_dump(mode="json", exclude={"min_test_action"}),
    }


def _normalize_refreshed_detail(*, card_type: str, lane: str, detail: dict[str, Any]) -> dict[str, Any]:
    if card_type == "write" or lane == "breakdown":
        return WritingDetail.model_validate(detail).model_dump(mode="json")
    normalized_detail = normalize_validation_detail_payload(lane, detail)
    normalized_detail.pop("min_test_action", None)
    return normalized_detail


__all__ = [
    "merge_semantic_refresh",
    "refresh_published_card_semantics",
    "select_cards_for_semantic_refresh",
    "semantic_change_summary",
]
