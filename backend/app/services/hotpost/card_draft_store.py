from __future__ import annotations

from app.schemas.hotpost_card_drafts import ValidationCardDraft, WritingCardDraft
from app.schemas.hotpost_clues import CardType
from app.schemas.hotpost_signal import SourceScopeId
from app.services.hotpost.card_draft_builder import build_published_card
from app.services.hotpost.card_payload_store import load_drafts, mutate_drafts, mutate_drafts_and_published


def _load_draft(item: dict) -> ValidationCardDraft | WritingCardDraft:
    if item["card_type"] == "validate":
        return ValidationCardDraft.model_validate(item)
    return WritingCardDraft.model_validate(item)


def list_drafts(source_scope_id:Optional[ SourceScopeId] = None, card_type:Optional[ CardType] = None) -> list[ValidationCardDraft | WritingCardDraft]:
    items = [_load_draft(item) for item in load_drafts()]
    if source_scope_id is not None:
        items = [item for item in items if item.source_scope_id == source_scope_id]
    if card_type is not None:
        items = [item for item in items if item.card_type == card_type]
    return items


def save_draft(card: ValidationCardDraft | WritingCardDraft) -> ValidationCardDraft | WritingCardDraft:
    def _mutate(drafts: list[dict], published: list[dict]) -> ValidationCardDraft | WritingCardDraft:
        if any(item["draft_id"] == card.draft_id for item in drafts):
            raise ValueError("Draft already exists")
        if any(item["card_id"] == card.card_id for item in published):
            raise ValueError("Published card already exists")
        drafts.append(card.model_dump(mode="json"))
        return card

    return mutate_drafts_and_published(_mutate)


def update_draft(draft_id: str, card: ValidationCardDraft | WritingCardDraft) -> ValidationCardDraft | WritingCardDraft:
    def _mutate(drafts: list[dict]) -> ValidationCardDraft | WritingCardDraft:
        index = next((idx for idx, item in enumerate(drafts) if item["draft_id"] == draft_id), None)
        if index is None:
            raise LookupError("Draft not found")
        if card.draft_id != draft_id:
            raise ValueError("Draft id mismatch")
        drafts[index] = card.model_dump(mode="json")
        return card

    return mutate_drafts(_mutate)


def delete_draft(draft_id: str) -> bool:
    def _mutate(drafts: list[dict]) -> bool:
        index = next((idx for idx, item in enumerate(drafts) if item["draft_id"] == draft_id), None)
        if index is None:
            return False
        drafts.pop(index)
        return True

    return mutate_drafts(_mutate)


def publish_draft(draft_id: str) -> tuple[str, int]:
    def _mutate(drafts: list[dict], published: list[dict]) -> tuple[str, int]:
        index = next((idx for idx, item in enumerate(drafts) if item["draft_id"] == draft_id), None)
        if index is None:
            raise LookupError("Draft not found")
        draft = _load_draft(drafts[index])
        if any(item["card_id"] == draft.card_id for item in published):
            raise ValueError("Published card already exists")
        published.append(build_published_card(draft).model_dump(mode="json"))
        drafts.pop(index)
        return draft.card_id, len(published)

    return mutate_drafts_and_published(_mutate)
