from __future__ import annotations

import json
from pathlib import Path

from app.schemas.hotpost_clues import CardSummary, Category, ValidationCardDetail, WritingCardDetail
from app.services.hotpost.card_payload_store import load_categories, load_published_cards
from app.services.hotpost.card_lane_policy import resolve_lane
from app.services.hotpost.hot_controversy_chart import enrich_hot_controversy_chart
from app.services.hotpost.mini_snapshot import build_mini_snapshot
from app.services.hotpost.mini_snapshot_supplement import SUPPLEMENT_SURFACE_BUCKET

_MINI_SNAPSHOT_LATEST_PATH = Path(__file__).resolve().parents[3] / "data" / "hotpost" / "mini_snapshots" / "latest.json"


def _to_card_summary(item: dict) -> CardSummary:
    normalized = enrich_hot_controversy_chart(dict(item))
    return CardSummary.model_validate(
        {
            "card_id": normalized["card_id"],
            "signal_id": normalized["signal_id"],
            "card_type": normalized["card_type"],
            "lane": resolve_lane(normalized.get("lane"), card_type=normalized["card_type"]),
            "category_id": normalized["category_id"],
            "source_scope_id": normalized["source_scope_id"],
            "source_scope_name": normalized["source_scope_name"],
            "source_domain_id": normalized["source_domain_id"],
            "source_domain_name": normalized["source_domain_name"],
            "source_event_at": normalized.get("source_event_at"),
            "title": normalized["title"],
            "summary_line": normalized["summary_line"],
            "audience": normalized["audience"],
            "why_now": normalized["why_now"],
            "why_now_reason": normalized["why_now_reason"],
            "signal_level": normalized.get("signal_level"),
            "intent_tags": normalized["intent_tags"],
            "top_community": normalized["source_module"]["top_community"],
            "thread_count": normalized["source_module"]["thread_count"],
            "community_count": normalized["source_module"]["community_count"],
            "source_module": normalized.get("source_module"),
            "preview_quote": normalized["preview_quote"],
            "published_at": normalized["published_at"],
            "controversy_chart": normalized.get("controversy_chart"),
        }
    )


def _load_latest_mini_snapshot_payload() -> dict:
    if not _MINI_SNAPSHOT_LATEST_PATH.exists():
        return {}
    payload = json.loads(_MINI_SNAPSHOT_LATEST_PATH.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_snapshot_cards() -> list[dict]:
    payload = _load_latest_mini_snapshot_payload()
    cards = payload.get("cards")
    if isinstance(cards, list):
        return [item for item in cards if isinstance(item, dict)]
    built = build_mini_snapshot({"categories": load_categories(), "published": load_published_cards()})
    return [item for item in built.get("cards", []) if isinstance(item, dict)]


def list_categories() -> list[Category]:
    return [Category.model_validate(item) for item in load_categories()]


def list_card_summaries(*, card_type: str, cursor:Optional[ str], page_size: int) ->Optional[ tuple[list[CardSummary], str]]:
    items = _load_snapshot_cards()
    if card_type == "supplement":
        items = [item for item in items if str(item.get("surface_bucket") or "") == SUPPLEMENT_SURFACE_BUCKET]
    if card_type == "hot":
        items = [item for item in items if resolve_lane(item.get("lane"), card_type=item["card_type"]) == "hot"]
    elif card_type == "validate":
        items = [
            item
            for item in items
            if item["card_type"] == "validate"
            and resolve_lane(item.get("lane"), card_type=item["card_type"]) == "signal"
        ]
    elif card_type not in {"all", "supplement"}:
        items = [item for item in items if item["card_type"] == card_type]
    start = int(cursor or "0")
    window = items[start : start + page_size]
    cards = [_to_card_summary(item) for item in window]
    next_cursor = str(start + page_size) if start + page_size < len(items) else None
    return cards, next_cursor


def get_card_summary(card_id: str) ->Optional[ CardSummary]:
    for item in load_published_cards():
        if item["card_id"] == card_id:
            return _to_card_summary(item)
    return None


def list_card_summaries_by_ids(card_ids: list[str]) -> list[CardSummary]:
    lookup = {item["card_id"]: item for item in load_published_cards()}
    return [_to_card_summary(lookup[card_id]) for card_id in card_ids if card_id in lookup]


def get_card_detail(card_id: str) -> ValidationCardDetail |Optional[ WritingCardDetail]:
    for item in load_published_cards():
        if item["card_id"] != card_id:
            continue
        normalized_item = enrich_hot_controversy_chart(dict(item))
        normalized = {
            **normalized_item,
            "lane": resolve_lane(normalized_item.get("lane"), card_type=normalized_item["card_type"]),
            "top_community": normalized_item["source_module"]["top_community"],
            "thread_count": normalized_item["source_module"]["thread_count"],
            "community_count": normalized_item["source_module"]["community_count"],
        }
        if normalized_item["card_type"] == "validate":
            return ValidationCardDetail.model_validate(normalized)
        return WritingCardDetail.model_validate(normalized)
    return None
