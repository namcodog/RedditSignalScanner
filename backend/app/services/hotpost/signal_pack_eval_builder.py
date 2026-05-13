from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_card_drafts import ValidationCardDraft
from app.services.hotpost.card_content_generator import generate_card_content
from app.services.hotpost.card_draft_builder import seed_validation_draft
from app.services.hotpost.signal_eval_set_builder import _draft_case
from app.services.hotpost.card_payload_store import load_candidates


SignalGenerator = Callable[[ValidationCardDraft], Awaitable[ValidationCardDraft]]


async def build_signal_pack_eval_cases(
    *,
    source_scope_id: str,
    topic_pack_id: str,
    generator: SignalGenerator = generate_card_content,
) -> dict[str, Any]:
    candidates = [
        CandidatePack.model_validate(item)
        for item in load_candidates()
        if item.get("source_scope_id") == source_scope_id and item.get("topic_pack_id") == topic_pack_id
    ]
    generation_failures: list[dict[str, str]] = []
    cases: list[dict[str, Any]] = []
    for candidate in _sort_candidates(candidates):
        try:
            draft = await generator(seed_validation_draft(candidate))
            cases.append(_draft_case(candidate, draft))
        except Exception as exc:
            generation_failures.append({"candidate_id": candidate.candidate_id, "error": str(exc)})
    return {
        "source_scope_id": source_scope_id,
        "topic_pack_id": topic_pack_id,
        "case_count": len(cases),
        "generation_failure_count": len(generation_failures),
        "cases": cases,
        "generation_failures": generation_failures,
    }


def _sort_candidates(candidates: list[CandidatePack]) -> list[CandidatePack]:
    return sorted(
        candidates,
        key=lambda item: (
            item.signal_level,
            item.thread_count,
            item.community_count,
            item.quote_count,
            item.score,
            item.num_comments,
        ),
        reverse=True,
    )


__all__ = ["build_signal_pack_eval_cases"]
