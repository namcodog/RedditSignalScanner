from __future__ import annotations

from typing import Any

from app.schemas.hotpost_signal import SourceScopeId
from app.services.hotpost.experimental_candidate_store import replace_experimental_scope_candidates
from app.services.hotpost.source_scope_candidate_collector import collect_scope_candidates_with_summary


async def collect_experimental_scope_probe(
    scope_id: SourceScopeId,
    *,
    max_candidates: int | None = None,
    mode: str = "safe",
) -> dict[str, Any]:
    summary = await collect_scope_candidates_with_summary(
        scope_id,
        max_candidates=max_candidates,
        mode=mode,
        include_experimental=True,
        experimental_only=True,
        persist=False,
    )
    write_result = replace_experimental_scope_candidates(scope_id, list(summary.get("items") or []))
    summary["experimental_candidate_store"] = write_result
    return summary


__all__ = ["collect_experimental_scope_probe"]
