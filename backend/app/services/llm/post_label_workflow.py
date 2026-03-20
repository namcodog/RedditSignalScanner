from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.services.llm.label_batch_support import (
    LLMLabelRunStats,
    build_post_item,
    process_label_batches,
    should_use_long_lab,
)


@dataclass(slots=True, frozen=True)
class IncrementalPostLabelWorkflowInput:
    settings: Any
    limit: int
    lookback_days: int
    llm_batch_size: int
    low_score_max: float
    high_score_ratio: float
    mid_score_min: float
    mid_score_max: float
    lab_long_sample_rate: float
    lab_body_ratio: float
    lab_comment_ratio: float


@dataclass(slots=True, frozen=True)
class IncrementalPostLabelWorkflowDeps:
    session_factory: Callable[[], Any]
    labeler_factory: Callable[..., Any]
    fetch_post_candidates: Callable[..., Awaitable[list[dict[str, Any]]]]
    fetch_top_comments: Callable[..., Awaitable[list[str]]]
    persist_post_analysis: Callable[..., Awaitable[None]]


async def run_incremental_post_label_workflow(
    *,
    workflow_input: IncrementalPostLabelWorkflowInput,
    deps: IncrementalPostLabelWorkflowDeps,
) -> dict[str, Any]:
    settings = workflow_input.settings
    api_key = settings.gemini_api_key
    if not api_key:
        return {"processed": 0, "status": "missing_api_key"}

    core_body_chars = int(settings.llm_label_body_chars)
    core_comment_chars = int(settings.llm_label_comment_chars)
    lab_body_chars = max(200, int(core_body_chars * workflow_input.lab_body_ratio))
    lab_comment_chars = max(
        80,
        int(core_comment_chars * workflow_input.lab_comment_ratio),
    )

    core_labeler = deps.labeler_factory(
        model=settings.llm_label_model_name,
        prompt_version=settings.llm_label_prompt_version,
        max_body_chars=core_body_chars,
        max_comment_chars=core_comment_chars,
        api_key=api_key,
    )
    lab_labeler = deps.labeler_factory(
        model=settings.llm_label_model_name,
        prompt_version=settings.llm_label_prompt_version,
        max_body_chars=lab_body_chars,
        max_comment_chars=lab_comment_chars,
        api_key=api_key,
    )

    candidates = await deps.fetch_post_candidates(
        limit=workflow_input.limit,
        lookback_days=workflow_input.lookback_days,
    )
    if not candidates:
        return {"processed": 0, "status": "no_candidates"}

    stats = LLMLabelRunStats()
    async with deps.session_factory() as session:
        long_items: list[dict[str, Any]] = []
        short_items: list[dict[str, Any]] = []
        row_by_id: dict[int, dict[str, Any]] = {}

        for row in candidates:
            value_score = float(row.get("value_score") or 0.0)
            if value_score <= workflow_input.low_score_max:
                continue
            pool = str(row.get("business_pool") or "lab").lower()
            use_long = pool == "core"
            if pool == "lab":
                use_long = should_use_long_lab(
                    row_id=int(row["id"]),
                    value_score=value_score,
                    mid_score_min=workflow_input.mid_score_min,
                    mid_score_max=workflow_input.mid_score_max,
                    sample_rate=workflow_input.lab_long_sample_rate,
                )

            comment_limit = 2 if use_long else 1
            top_comments = await deps.fetch_top_comments(
                row["source"],
                row["source_post_id"],
                limit=comment_limit,
            )
            item = build_post_item(row, top_comments=top_comments)
            row_by_id[int(row["id"])] = row
            if use_long:
                long_items.append(item)
            else:
                short_items.append(item)

        stats.attempted = len(long_items) + len(short_items)

        await process_label_batches(
            session=session,
            items=long_items,
            batch_size=workflow_input.llm_batch_size,
            label_kind="post_labels/core",
            stats=stats,
            batch_label=lambda batch: core_labeler.label_posts_batch(items=batch),
            single_label=lambda item: core_labeler.label_post(
                title=str(item.get("title") or ""),
                body=str(item.get("body") or ""),
                subreddit=str(item.get("subreddit") or ""),
                comments=item.get("comments") or [],
            ),
            persist_batch=lambda result: deps.persist_post_analysis(
                session=session,
                row_by_id=row_by_id,
                labeler=core_labeler,
                prompt_version=settings.llm_label_prompt_version,
                item_id=int(result["id"]),
                analysis=result["analysis"],
                score=result["score"].__dict__,
                input_chars=int(result["input_chars"]),
                output_chars=int(result["output_chars"]),
            ),
            persist_single=lambda item, single_result: deps.persist_post_analysis(
                session=session,
                row_by_id=row_by_id,
                labeler=core_labeler,
                prompt_version=settings.llm_label_prompt_version,
                item_id=int(item["id"]),
                analysis=single_result[0],
                score=single_result[1].__dict__,
                input_chars=single_result[2],
                output_chars=single_result[3],
            ),
        )

        await process_label_batches(
            session=session,
            items=short_items,
            batch_size=workflow_input.llm_batch_size,
            label_kind="post_labels/lab",
            stats=stats,
            batch_label=lambda batch: lab_labeler.label_posts_batch(items=batch),
            single_label=lambda item: lab_labeler.label_post(
                title=str(item.get("title") or ""),
                body=str(item.get("body") or ""),
                subreddit=str(item.get("subreddit") or ""),
                comments=item.get("comments") or [],
            ),
            persist_batch=lambda result: deps.persist_post_analysis(
                session=session,
                row_by_id=row_by_id,
                labeler=lab_labeler,
                prompt_version=settings.llm_label_prompt_version,
                item_id=int(result["id"]),
                analysis=result["analysis"],
                score=result["score"].__dict__,
                input_chars=int(result["input_chars"]),
                output_chars=int(result["output_chars"]),
            ),
            persist_single=lambda item, single_result: deps.persist_post_analysis(
                session=session,
                row_by_id=row_by_id,
                labeler=lab_labeler,
                prompt_version=settings.llm_label_prompt_version,
                item_id=int(item["id"]),
                analysis=single_result[0],
                score=single_result[1].__dict__,
                input_chars=single_result[2],
                output_chars=single_result[3],
            ),
        )

    return stats.to_result()

