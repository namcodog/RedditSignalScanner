from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.services.llm.comment_label_workflow import (
    IncrementalCommentLabelWorkflowDeps,
    IncrementalCommentLabelWorkflowInput,
)
from app.services.llm.legacy_label_backfill_workflow import (
    LegacyLabelBackfillWorkflowDeps,
    LegacyLabelBackfillWorkflowInput,
)
from app.services.llm.post_label_workflow import (
    IncrementalPostLabelWorkflowDeps,
    IncrementalPostLabelWorkflowInput,
)


@dataclass(slots=True, frozen=True)
class LLMLabelTaskRuntimeConfig:
    llm_batch_size: int
    low_score_max: float
    high_score_min: float
    high_score_ratio: float
    mid_score_min: float
    mid_score_max: float
    lab_long_sample_rate: float
    lab_body_ratio: float
    lab_comment_ratio: float
    online_comment_budget_cap: int


@dataclass(slots=True, frozen=True)
class LLMLabelTaskRuntimeDeps:
    get_settings: Callable[[], Any]
    session_factory: Callable[[], Any]
    labeler_factory: Callable[..., Any]
    fetch_post_candidates: Callable[..., Awaitable[list[dict[str, Any]]]]
    fetch_top_comments: Callable[..., Awaitable[list[str]]]
    build_incremental_comment_label_plan: Callable[..., Awaitable[Any]]
    persist_post_analysis: Callable[..., Awaitable[None]]
    persist_comment_analysis: Callable[..., Awaitable[None]]
    upsert_legacy_post_label: Callable[..., Awaitable[None]]
    upsert_legacy_comment_label: Callable[..., Awaitable[None]]
    sync_llm_terms: Callable[..., Awaitable[Any]]
    json_sanitize: Callable[[Any], Any]
    run_incremental_post_label_workflow: Callable[..., Awaitable[dict[str, Any]]]
    run_incremental_comment_label_workflow: Callable[..., Awaitable[dict[str, Any]]]
    run_legacy_label_backfill_workflow: Callable[..., Awaitable[dict[str, Any]]]


async def run_label_posts_task(
    *,
    limit: int,
    lookback_days: int,
    deps: LLMLabelTaskRuntimeDeps,
    config: LLMLabelTaskRuntimeConfig,
) -> dict[str, Any]:
    settings = deps.get_settings()
    return await deps.run_incremental_post_label_workflow(
        workflow_input=IncrementalPostLabelWorkflowInput(
            settings=settings,
            limit=limit,
            lookback_days=lookback_days,
            llm_batch_size=config.llm_batch_size,
            low_score_max=config.low_score_max,
            high_score_ratio=config.high_score_ratio,
            mid_score_min=config.mid_score_min,
            mid_score_max=config.mid_score_max,
            lab_long_sample_rate=config.lab_long_sample_rate,
            lab_body_ratio=config.lab_body_ratio,
            lab_comment_ratio=config.lab_comment_ratio,
        ),
        deps=IncrementalPostLabelWorkflowDeps(
            session_factory=deps.session_factory,
            labeler_factory=deps.labeler_factory,
            fetch_post_candidates=deps.fetch_post_candidates,
            fetch_top_comments=deps.fetch_top_comments,
            persist_post_analysis=deps.persist_post_analysis,
        ),
    )


async def run_label_comments_task(
    *,
    limit: int,
    lookback_days: int,
    deps: LLMLabelTaskRuntimeDeps,
    config: LLMLabelTaskRuntimeConfig,
) -> dict[str, Any]:
    settings = deps.get_settings()
    plan = await deps.build_incremental_comment_label_plan(
        limit=limit,
        lookback_days=lookback_days,
    )
    return await deps.run_incremental_comment_label_workflow(
        workflow_input=IncrementalCommentLabelWorkflowInput(
            settings=settings,
            plan=plan,
            online_budget_cap=config.online_comment_budget_cap,
            llm_batch_size=config.llm_batch_size,
            low_score_max=config.low_score_max,
            high_score_ratio=config.high_score_ratio,
            mid_score_min=config.mid_score_min,
            mid_score_max=config.mid_score_max,
            lab_long_sample_rate=config.lab_long_sample_rate,
            lab_body_ratio=config.lab_body_ratio,
            lab_comment_ratio=config.lab_comment_ratio,
        ),
        deps=IncrementalCommentLabelWorkflowDeps(
            session_factory=deps.session_factory,
            labeler_factory=deps.labeler_factory,
            persist_comment_analysis=deps.persist_comment_analysis,
        ),
    )


async def run_backfill_legacy_labels_task(
    *,
    limit: int,
    deps: LLMLabelTaskRuntimeDeps,
) -> dict[str, Any]:
    return await deps.run_legacy_label_backfill_workflow(
        workflow_input=LegacyLabelBackfillWorkflowInput(limit=limit),
        deps=LegacyLabelBackfillWorkflowDeps(
            session_factory=deps.session_factory,
            upsert_post_label=deps.upsert_legacy_post_label,
            upsert_comment_label=deps.upsert_legacy_comment_label,
            sync_llm_terms=deps.sync_llm_terms,
            json_sanitize=deps.json_sanitize,
        ),
    )


__all__ = [
    "LLMLabelTaskRuntimeConfig",
    "LLMLabelTaskRuntimeDeps",
    "run_backfill_legacy_labels_task",
    "run_label_comments_task",
    "run_label_posts_task",
]
