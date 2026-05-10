from __future__ import annotations

from app.schemas.hotpost_card_candidates import CandidatePack
from app.schemas.hotpost_signal import SignalLevel, SourceScopeId
from app.services.hotpost.card_payload_store import load_candidates, mutate_candidates
from app.services.hotpost.card_review_rejection_store import list_rejected_candidate_ids


def _load_candidate(item: dict) -> CandidatePack:
    return CandidatePack.model_validate(item)


def list_candidates(
    source_scope_id: Optional[SourceScopeId] = None,
    signal_level: Optional[SignalLevel] = None,
    *,
    include_rejected: bool = False,
) -> list[CandidatePack]:
    items = [_load_candidate(item) for item in load_candidates()]
    if not include_rejected:
        rejected_ids = list_rejected_candidate_ids()
        items = [item for item in items if item.candidate_id not in rejected_ids]
    if source_scope_id is not None:
        items = [item for item in items if item.source_scope_id == source_scope_id]
    if signal_level is not None:
        items = [item for item in items if item.signal_level == signal_level]
    return sorted(items, key=lambda item: item.collected_at, reverse=True)


def get_candidate(candidate_id: str) -> CandidatePack:
    item = next((item for item in load_candidates() if item["candidate_id"] == candidate_id), None)
    if item is None:
        raise LookupError("Candidate not found")
    return _load_candidate(item)


def get_candidates(candidate_ids: list[str]) -> list[CandidatePack]:
    return [get_candidate(candidate_id) for candidate_id in candidate_ids]


def save_candidate(candidate: CandidatePack) -> CandidatePack:
    def _mutate(candidates: list[dict]) -> CandidatePack:
        if any(item["candidate_id"] == candidate.candidate_id for item in candidates):
            raise ValueError("Candidate already exists")
        candidates.append(candidate.model_dump(mode="json"))
        return candidate

    return mutate_candidates(_mutate)


def upsert_candidate(candidate: CandidatePack) -> CandidatePack:
    def _mutate(candidates: list[dict]) -> CandidatePack:
        items = [item for item in candidates if item["candidate_id"] != candidate.candidate_id]
        items.append(candidate.model_dump(mode="json"))
        candidates[:] = items
        return candidate

    return mutate_candidates(_mutate)


def replace_scope_candidates(source_scope_id: SourceScopeId, candidates: list[CandidatePack]) -> list[CandidatePack]:
    def _mutate(current_candidates: list[dict]) -> list[CandidatePack]:
        items = [item for item in current_candidates if item["source_scope_id"] != source_scope_id]
        items.extend(candidate.model_dump(mode="json") for candidate in candidates)
        current_candidates[:] = items
        return candidates

    return mutate_candidates(_mutate)
