from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from app.services.llm.comment_label_planner import IncrementalCommentLabelPlan
from app.services.llm.label_batch_support import (
    LLMLabelRunStats,
    build_comment_item,
    process_label_batches,
    should_use_long_lab,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class IncrementalCommentLabelWorkflowInput:
    settings: Any
    plan: IncrementalCommentLabelPlan
    online_budget_cap: int
    llm_batch_size: int
    low_score_max: float
    high_score_ratio: float
    mid_score_min: float
    mid_score_max: float
    lab_long_sample_rate: float
    lab_body_ratio: float
    lab_comment_ratio: float


@dataclass(slots=True)
class IncrementalCommentLabelWorkflowDeps:
    session_factory: Callable[[], Any]
    labeler_factory: Callable[..., Any]
    persist_comment_analysis: Callable[..., Awaitable[None]]


async def run_incremental_comment_label_workflow(
    *,
    workflow_input: IncrementalCommentLabelWorkflowInput,
    deps: IncrementalCommentLabelWorkflowDeps,
) -> dict[str, Any]:
    settings = workflow_input.settings
    api_key = settings.gemini_api_key
    if not api_key:
        return {
            "processed": 0,
            "status": "missing_api_key",
            "task_scope": "incremental_only",
        }

    prefilter_stats = workflow_input.plan.prefilter_stats
    filtered_candidates = workflow_input.plan.candidates
    if not filtered_candidates:
        return {
            "processed": 0,
            "status": "no_candidates",
            "rule_filtered": prefilter_stats.filtered_short,
            "deduped": prefilter_stats.deduped,
            "task_scope": "incremental_only",
        }

    core_body_chars = int(settings.llm_label_body_chars)
    core_comment_chars = int(settings.llm_label_comment_chars)
    lab_body_chars = max(160, int(core_body_chars * workflow_input.lab_body_ratio))
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

    stats = LLMLabelRunStats()
    async with deps.session_factory() as session:
        long_items: list[dict[str, Any]] = []
        short_items: list[dict[str, Any]] = []

        for row in filtered_candidates:
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

            item = build_comment_item(row)
            if use_long:
                long_items.append(item)
            else:
                short_items.append(item)

        stats.attempted = len(long_items) + len(short_items)

        if stats.attempted > workflow_input.online_budget_cap:
            logger.warning(
                "comment_budget_cap_hit: attempted=%d cap=%d — truncating",
                stats.attempted,
                workflow_input.online_budget_cap,
            )
            long_cap = int(workflow_input.online_budget_cap * workflow_input.high_score_ratio)
            short_cap = workflow_input.online_budget_cap - long_cap
            long_items = long_items[:long_cap]
            short_items = short_items[:short_cap]
            stats.attempted = len(long_items) + len(short_items)
            stats.mark_degraded("budget_capped")

        logger.info(
            "comment_candidates_after_rules: admitted=%d rule_filtered=%d deduped=%d",
            stats.attempted,
            prefilter_stats.filtered_short,
            prefilter_stats.deduped,
        )

        if stats.attempted == 0:
            return {
                "processed": 0,
                "status": "no_candidates",
                "rule_filtered": prefilter_stats.filtered_short,
                "deduped": prefilter_stats.deduped,
                "task_scope": "incremental_only",
            }

        await process_label_batches(
            session=session,
            items=long_items,
            batch_size=workflow_input.llm_batch_size,
            label_kind="comment_labels/core",
            stats=stats,
            batch_label=lambda batch: core_labeler.label_comments_batch(items=batch),
            single_label=lambda item: core_labeler.label_comment(
                body=str(item.get("body") or ""),
                post_title=str(item.get("post_title") or ""),
                subreddit=str(item.get("subreddit") or ""),
            ),
            persist_batch=lambda result: deps.persist_comment_analysis(
                session=session,
                labeler=core_labeler,
                prompt_version=settings.llm_label_prompt_version,
                item_id=int(result["id"]),
                analysis=result["analysis"],
                score=result["score"].__dict__,
                input_chars=int(result["input_chars"]),
                output_chars=int(result["output_chars"]),
            ),
            persist_single=lambda item, single_result: deps.persist_comment_analysis(
                session=session,
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
            label_kind="comment_labels/lab",
            stats=stats,
            batch_label=lambda batch: lab_labeler.label_comments_batch(items=batch),
            single_label=lambda item: lab_labeler.label_comment(
                body=str(item.get("body") or ""),
                post_title=str(item.get("post_title") or ""),
                subreddit=str(item.get("subreddit") or ""),
            ),
            persist_batch=lambda result: deps.persist_comment_analysis(
                session=session,
                labeler=lab_labeler,
                prompt_version=settings.llm_label_prompt_version,
                item_id=int(result["id"]),
                analysis=result["analysis"],
                score=result["score"].__dict__,
                input_chars=int(result["input_chars"]),
                output_chars=int(result["output_chars"]),
            ),
            persist_single=lambda item, single_result: deps.persist_comment_analysis(
                session=session,
                labeler=lab_labeler,
                prompt_version=settings.llm_label_prompt_version,
                item_id=int(item["id"]),
                analysis=single_result[0],
                score=single_result[1].__dict__,
                input_chars=single_result[2],
                output_chars=single_result[3],
            ),
        )

    result = stats.to_result()
    result["task_scope"] = "incremental_only"
    result["rule_filtered"] = prefilter_stats.filtered_short
    result["deduped"] = prefilter_stats.deduped
    return result
