from __future__ import annotations

from typing import Any

from app.schemas.hotpost_card_drafts import ValidationCardDraft, WritingCardDraft


DraftCard = ValidationCardDraft | WritingCardDraft


def assess_draft_surface_readiness(draft: DraftCard) -> dict[str, Any]:
    reasons: list[str] = []
    if not list(draft.evidence_quotes or []):
        reasons.append("missing_evidence_quotes")
    required_summary = [draft.summary_line, draft.audience, draft.why_now, draft.source_link]
    if any(not str(value or "").strip() for value in required_summary):
        reasons.append("summary_fields_incomplete")
    detail_values = draft.detail.model_dump().values()
    if any((isinstance(value, str) and not value.strip()) or (isinstance(value, list) and not value) for value in detail_values):
        reasons.append("detail_fields_incomplete")
    return {
        "is_ready": not reasons,
        "reasons": reasons,
    }


def is_draft_surface_ready(draft: DraftCard) -> bool:
    return bool(assess_draft_surface_readiness(draft)["is_ready"])


__all__ = [
    "DraftCard",
    "assess_draft_surface_readiness",
    "is_draft_surface_ready",
]
