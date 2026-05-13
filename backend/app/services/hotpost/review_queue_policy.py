from __future__ import annotations

from app.schemas.hotpost_card_drafts import ValidationCardDraft, WritingCardDraft
from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.card_draft_builder import seed_validation_draft, seed_writing_draft
from app.services.hotpost.card_review_rejection_store import list_rejected_candidate_ids
from app.services.hotpost.draft_surface_readiness import is_draft_surface_ready
from app.services.hotpost.publish_surface_gate_tiering import RELAXABLE_REASONS
from app.services.hotpost.publish_surface_quality import assess_publish_surface_candidate


def filter_actionable_candidates(
    candidates: list[CandidatePack],
    *,
    card_type:Optional[ str],
    published_items: list[dict],
    draft_items: list[dict],
) -> list[CandidatePack]:
    published_ids = {item["card_id"] for item in published_items}
    draft_ids = {
        item.card_id
        for item in (_load_draft(raw) for raw in draft_items)
        if item is not None and is_draft_surface_ready(item)
    }
    rejected_ids = list_rejected_candidate_ids()
    actionable: list[CandidatePack] = []
    for candidate in candidates:
        if candidate.candidate_id in rejected_ids:
            continue
        target = seed_validation_draft(candidate) if card_type != "write" else seed_writing_draft(candidate)
        if target.card_id in published_ids or target.card_id in draft_ids:
            continue
        if card_type != "write":
            quality = assess_publish_surface_candidate(candidate, lane=target.lane)
            if quality["should_block"] and not _allow_hot_review_candidate(quality=quality, lane=target.lane):
                continue
        actionable.append(candidate)
    return actionable


def _load_draft(payload: dict) -> ValidationCardDraft | WritingCardDraft | None:
    try:
        if payload["card_type"] == "validate":
            return ValidationCardDraft.model_validate(payload)
        return WritingCardDraft.model_validate(payload)
    except Exception:
        return None


def _allow_hot_review_candidate(*, quality: dict, lane: str) -> bool:
    if lane != "hot":
        return False
    reasons = {str(reason) for reason in list(quality.get("reasons") or []) if str(reason)}
    return bool(reasons) and reasons.issubset(RELAXABLE_REASONS)
