from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Any

from app.schemas.hotpost_card_candidates import CandidatePack
from app.services.hotpost.card_content_generator import LLMClientFactory, generate_card_content
from app.services.hotpost.card_draft_builder import seed_validation_draft
from app.services.hotpost.card_content_llm_router import build_card_content_client
from app.services.hotpost.review_queue_snapshot_store import get_snapshot_candidate, load_review_queue_snapshot
from app.services.llm.clients.codex_cli_client import CodexCLIChatClient
from app.services.llm.clients.gemini_cli_client import GeminiCLIChatClient


def build_signal_cli_shadow_client_factory(
    *,
    model: str,
    cwd: Path,
    min_timeout_seconds: float = 180.0,
) -> LLMClientFactory:
    def _factory(_route_model: str, timeout: float) -> GeminiCLIChatClient:
        return GeminiCLIChatClient(
            model=model,
            timeout_seconds=max(float(timeout), float(min_timeout_seconds)),
            cwd=cwd,
        )

    return _factory


def load_signal_shadow_candidates(
    *,
    snapshot_id:Optional[ str] = None,
    candidate_ids:Optional[ list[str]] = None,
    limit:Optional[ int] = None,
) -> list[CandidatePack]:
    if candidate_ids:
        items = [get_snapshot_candidate(candidate_id, snapshot_id=snapshot_id) for candidate_id in candidate_ids]
    else:
        payload = load_review_queue_snapshot(snapshot_id)
        items = [CandidatePack.model_validate(item) for item in payload.get("candidates", [])]

    signal_items: list[CandidatePack] = []
    for item in items:
        seeded = seed_validation_draft(item)
        if seeded.lane != "signal":
            continue
        signal_items.append(item)
        if limit is not None and len(signal_items) >= limit:
            break
    return signal_items


def write_signal_shadow_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def build_signal_api_shadow_client_factory() -> LLMClientFactory:
    def _factory(route_model: str, timeout: float):
        return build_card_content_client(route_model, timeout=timeout)

    return _factory


def build_signal_codex_shadow_client_factory(
    *,
    model: str,
    cwd: Path,
    min_timeout_seconds: float = 180.0,
) -> LLMClientFactory:
    def _factory(_route_model: str, timeout: float) -> CodexCLIChatClient:
        return CodexCLIChatClient(
            model=model,
            timeout_seconds=max(float(timeout), float(min_timeout_seconds)),
            cwd=cwd,
        )

    return _factory


async def generate_signal_shadow_from_candidate(
    candidate: CandidatePack,
    *,
    client_factory: LLMClientFactory,
) -> dict[str, Any]:
    draft = seed_validation_draft(candidate)
    if draft.lane != "signal":
        raise ValueError(
            f"signal shadow only supports lane=signal candidates: {candidate.candidate_id} actual_lane={draft.lane}"
        )
    generated = await generate_card_content(
        draft,
        allow_breakdown=False,
        client_factory=client_factory,
    )
    return {
        "candidate_id": generated.candidate_id,
        "lane": generated.lane,
        "source_scope_id": generated.source_scope_id,
        "source_scope_name": generated.source_scope_name,
        "topic_pack_id": generated.topic_pack_id,
        "title": generated.title,
        "summary_line": generated.summary_line,
        "audience": generated.audience,
        "why_now": generated.why_now,
        "detail": generated.detail.model_dump(mode="json"),
    }


__all__ = [
    "build_signal_api_shadow_client_factory",
    "build_signal_cli_shadow_client_factory",
    "build_signal_codex_shadow_client_factory",
    "load_signal_shadow_candidates",
    "write_signal_shadow_jsonl",
    "generate_signal_shadow_from_candidate",
]
