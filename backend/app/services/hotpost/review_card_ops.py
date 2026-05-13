from __future__ import annotations

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_card_drafts import ValidationCardDraft, WritingCardDraft
from app.services.hotpost.card_candidate_store import get_candidate, get_candidates
from app.services.hotpost.card_content_generator import generate_card_content
from app.services.hotpost.draft_surface_readiness import is_draft_surface_ready
from app.services.hotpost.card_draft_builder import seed_validation_draft, seed_writing_draft
from app.services.hotpost.card_draft_store import list_drafts, save_draft, update_draft
from app.services.hotpost.card_group_draft_builder import seed_group_validation_draft, seed_group_writing_draft


DraftCard = ValidationCardDraft | WritingCardDraft


async def seed_review_draft(candidate_id: str, card_type: str) -> DraftCard:
    candidate = get_candidate(candidate_id)
    return await seed_review_draft_from_candidate(candidate, card_type)


async def seed_review_draft_from_candidate(candidate: CandidatePack, card_type: str) -> DraftCard:
    seeded = seed_validation_draft(candidate) if card_type == "validate" else seed_writing_draft(candidate)
    generated = await generate_card_content(seeded)
    _save_or_replace_draft(generated)
    return generated


async def seed_review_group_draft(candidate_ids: list[str], card_type: str) -> DraftCard:
    candidates = get_candidates(candidate_ids)
    seeded = (
        seed_group_validation_draft(candidates)
        if card_type == "validate"
        else seed_group_writing_draft(candidates)
    )
    generated = await generate_card_content(seeded)
    _save_or_replace_draft(generated)
    return generated


def _save_or_replace_draft(draft: DraftCard) -> DraftCard:
    existing = next((item for item in list_drafts() if item.draft_id == draft.draft_id), None)
    if existing is None:
        return save_draft(draft)
    if is_draft_surface_ready(existing):
        raise ValueError("Draft already exists")
    return update_draft(draft.draft_id, draft)


__all__ = ["seed_review_draft", "seed_review_draft_from_candidate", "seed_review_group_draft"]
