from __future__ import annotations

from app.schemas.hotpost_card_drafts import WritingCardDraft
from app.schemas.hotpost_card_review import BreakdownDraftMaterializeResult
from app.schemas.hotpost_signal import SourceScopeId
from app.services.hotpost.breakdown_candidate_clusterer import list_breakdown_suggestions
from app.services.hotpost.card_candidate_store import get_candidates
from app.services.hotpost.card_content_generator import generate_card_content
from app.services.hotpost.card_draft_store import list_drafts, save_draft
from app.services.hotpost.card_group_draft_builder import seed_group_writing_draft
from app.services.hotpost.card_payload_store import load_published_cards


async def materialize_breakdown_drafts(
    source_scope_id:Optional[ SourceScopeId] = None,
    *,
    limit: int = 20,
) -> list[BreakdownDraftMaterializeResult]:
    suggestions = list_breakdown_suggestions(source_scope_id, limit=limit)
    existing_draft_ids = {draft.draft_id for draft in list_drafts(card_type="write")}
    published_card_ids = {item["card_id"] for item in load_published_cards()}
    results: list[BreakdownDraftMaterializeResult] = []
    for suggestion in suggestions:
        seeded = seed_group_writing_draft(get_candidates(suggestion.candidate_ids))
        if seeded.draft_id in existing_draft_ids or seeded.card_id in published_card_ids:
            results.append(
                BreakdownDraftMaterializeResult(
                    suggestion_id=suggestion.suggestion_id,
                    status="skipped_existing",
                    draft_id=seeded.draft_id,
                    card_id=seeded.card_id,
                    reason="draft_or_card_already_exists",
                )
            )
            continue
        try:
            generated = await generate_card_content(seeded)
            if not isinstance(generated, WritingCardDraft) or generated.card_type != "write":
                raise ValueError("breakdown_generation_did_not_hold_write_bar")
            save_draft(generated)
            existing_draft_ids.add(generated.draft_id)
            results.append(
                BreakdownDraftMaterializeResult(
                    suggestion_id=suggestion.suggestion_id,
                    status="materialized",
                    draft_id=generated.draft_id,
                    card_id=generated.card_id,
                )
            )
        except Exception as exc:
            results.append(
                BreakdownDraftMaterializeResult(
                    suggestion_id=suggestion.suggestion_id,
                    status="failed",
                    draft_id=seeded.draft_id,
                    card_id=seeded.card_id,
                    reason=str(exc),
                )
            )
    return results


__all__ = ["materialize_breakdown_drafts"]
