from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, cast

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_card_drafts import ValidationCardDraft, WritingCardDraft
from app.services.hotpost.card_candidate_store import get_candidate, get_candidates
from app.services.hotpost.card_content_generator import (
    collect_generation_sub_stages,
    generate_card_content,
    generation_error_type,
)
from app.services.hotpost.card_content_rules_config import load_card_content_rules
from app.services.hotpost.draft_surface_readiness import is_draft_surface_ready
from app.services.hotpost.card_draft_builder import seed_validation_draft, seed_writing_draft
from app.services.hotpost.card_draft_store import list_drafts, save_draft, update_draft
from app.services.hotpost.card_payload_store import load_published_cards
from app.services.hotpost.generation_trace_store import save_generation_trace
from app.services.hotpost.card_group_draft_builder import seed_group_validation_draft, seed_group_writing_draft


DraftCard = ValidationCardDraft | WritingCardDraft


async def seed_review_draft(candidate_id: str, card_type: str) -> DraftCard:
    candidate = get_candidate(candidate_id)
    return await seed_review_draft_from_candidate(candidate, card_type)


async def seed_review_draft_from_candidate(candidate: CandidatePack, card_type: str) -> DraftCard:
    seeded = cast(
        DraftCard,
        seed_validation_draft(candidate) if card_type == "validate" else seed_writing_draft(candidate),
    )
    _assert_seed_not_already_saved(seeded)
    generated = await _run_seed_generation(
        seeded,
        card_type=card_type,
        generate=lambda draft: generate_card_content(
            draft,
            allow_breakdown=card_type == "write",
        ),
    )
    _save_or_replace_draft(generated)
    _save_precheck_if_present(generated)
    return generated


async def seed_review_group_draft(candidate_ids: list[str], card_type: str) -> DraftCard:
    candidates = get_candidates(candidate_ids)
    seeded = cast(
        DraftCard,
        (
            seed_group_validation_draft(candidates)
            if card_type == "validate"
            else seed_group_writing_draft(candidates)
        ),
    )
    _assert_seed_not_already_saved(seeded)
    generated = await _run_seed_generation(
        seeded,
        card_type=card_type,
        generate=lambda draft: generate_card_content(
            draft,
            allow_breakdown=card_type == "write",
        ),
    )
    _save_or_replace_draft(generated)
    _save_precheck_if_present(generated)
    return generated


async def _run_seed_generation(
    seeded: DraftCard,
    *,
    card_type: str,
    generate: Callable[[DraftCard], Awaitable[DraftCard]],
) -> DraftCard:
    trace = {
        "candidate_id": seeded.candidate_id,
        "draft_id": seeded.draft_id,
        "card_id": seeded.card_id,
        "card_type": card_type,
        "allow_breakdown": card_type == "write",
        "overall_status": "running",
        "stages": [
            {"name": "duplicate_preflight", "status": "completed"},
            {"name": "model_generation", "status": "started"},
        ],
    }
    sub_stages: list[dict[str, Any]] = []
    try:
        with collect_generation_sub_stages() as sub_stages:
            generated = await asyncio.wait_for(
                generate(seeded),
                timeout=_pipeline_total_seconds(),
            )
    except Exception as exc:
        save_generation_trace(
            seeded.draft_id,
            {
                **trace,
                "overall_status": "failed",
                "stages": [
                    {"name": "duplicate_preflight", "status": "completed"},
                    {"name": "model_generation", "status": "failed"},
                ],
                "sub_stages": list(sub_stages),
                "error_type": generation_error_type(exc),
                "error": (str(exc) or generation_error_type(exc))[:240],
            },
        )
        raise
    save_generation_trace(
        generated.draft_id,
        {
            **trace,
            "draft_id": generated.draft_id,
            "overall_status": "completed",
            "stages": [
                {"name": "duplicate_preflight", "status": "completed"},
                {"name": "model_generation", "status": "completed"},
            ],
            "sub_stages": list(sub_stages),
        },
    )
    return generated


def _pipeline_total_seconds() -> float:
    rules = load_card_content_rules()
    pipeline = rules.get("pipeline") or {}
    if not isinstance(pipeline, dict):
        return 150.0
    value = pipeline.get("total_seconds")
    return float(value) if value is not None else 150.0


def _assert_seed_not_already_saved(draft: DraftCard) -> None:
    existing = next((item for item in list_drafts() if item.draft_id == draft.draft_id), None)
    if existing is not None and is_draft_surface_ready(existing):
        raise ValueError("Draft already exists")
    if any(item.get("card_id") == draft.card_id for item in load_published_cards()):
        raise ValueError("Published card already exists")


def _save_precheck_if_present(draft: DraftCard) -> None:
    precheck_result = getattr(draft, "_hotpost_precheck_result", None)
    if isinstance(precheck_result, dict):
        from app.services.hotpost.draft_precheck_store import save_draft_precheck

        save_draft_precheck(draft.draft_id, precheck_result)


def _save_or_replace_draft(draft: DraftCard) -> DraftCard:
    existing = next((item for item in list_drafts() if item.draft_id == draft.draft_id), None)
    if existing is None:
        return save_draft(draft)
    if is_draft_surface_ready(existing):
        raise ValueError("Draft already exists")
    return update_draft(draft.draft_id, draft)


__all__ = ["seed_review_draft", "seed_review_draft_from_candidate", "seed_review_group_draft"]
