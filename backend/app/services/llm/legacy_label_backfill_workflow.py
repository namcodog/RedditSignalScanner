from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping

from sqlalchemy import text as sqltext


logger = logging.getLogger(__name__)

_POST_BACKFILL_SQL = sqltext(
    """
    WITH latest_scores AS (
        SELECT DISTINCT ON (ps.post_id)
               ps.post_id,
               ps.llm_version,
               ps.tags_analysis,
               ps.entities_extracted,
               ps.value_score,
               ps.opportunity_score,
               ps.business_pool,
               ps.sentiment,
               ps.purchase_intent_score,
               ps.scored_at,
               p.text_norm_hash
        FROM post_scores ps
        JOIN posts_raw p ON p.id = ps.post_id
        LEFT JOIN post_llm_labels llm ON llm.post_id = ps.post_id
        LEFT JOIN post_llm_labels llm_hash
          ON p.text_norm_hash IS NOT NULL
         AND llm_hash.text_norm_hash = p.text_norm_hash
        WHERE ps.llm_version IS NOT NULL
          AND ps.llm_version <> 'none'
          AND ps.tags_analysis <> '{}'::jsonb
          AND llm.post_id IS NULL
          AND llm_hash.post_id IS NULL
        ORDER BY ps.post_id, ps.scored_at DESC NULLS LAST
    )
    SELECT *
    FROM latest_scores
    ORDER BY scored_at DESC NULLS LAST
    LIMIT :limit
    """
)

_COMMENT_BACKFILL_SQL = sqltext(
    """
    WITH latest_scores AS (
        SELECT DISTINCT ON (cs.comment_id)
               cs.comment_id,
               cs.llm_version,
               cs.tags_analysis,
               cs.entities_extracted,
               cs.value_score,
               cs.opportunity_score,
               cs.business_pool,
               cs.sentiment,
               cs.purchase_intent_score,
               cs.scored_at
        FROM comment_scores cs
        LEFT JOIN comment_llm_labels llm ON llm.comment_id = cs.comment_id
        WHERE cs.llm_version IS NOT NULL
          AND cs.llm_version <> 'none'
          AND cs.tags_analysis <> '{}'::jsonb
          AND llm.comment_id IS NULL
        ORDER BY cs.comment_id, cs.scored_at DESC NULLS LAST
    )
    SELECT *
    FROM latest_scores
    ORDER BY scored_at DESC NULLS LAST
    LIMIT :limit
    """
)


@dataclass(slots=True, frozen=True)
class LegacyLabelBackfillWorkflowInput:
    limit: int
    prompt_version: str = "legacy_v2"


@dataclass(slots=True, frozen=True)
class LegacyLabelBackfillWorkflowDeps:
    session_factory: Callable[[], Any]
    upsert_post_label: Callable[..., Awaitable[None]]
    upsert_comment_label: Callable[..., Awaitable[None]]
    sync_llm_terms: Callable[..., Awaitable[Any]]
    json_sanitize: Callable[[Any], Any]


def _build_analysis(
    row: Mapping[str, Any],
    *,
    json_sanitize: Callable[[Any], Any],
) -> dict[str, Any]:
    analysis = dict(row.get("tags_analysis") or {})
    entities = row.get("entities_extracted") or {}
    if entities:
        analysis["entities"] = entities
    if row.get("sentiment") is not None:
        analysis["sentiment"] = row.get("sentiment")
    if row.get("purchase_intent_score") is not None:
        analysis["purchase_intent_score"] = row.get("purchase_intent_score")
    return json_sanitize(analysis)


def _build_score(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "value_score": row.get("value_score"),
        "opportunity_score": row.get("opportunity_score"),
        "business_pool": row.get("business_pool"),
    }


def _resolve_status(
    *,
    processed: int,
    persist_failures: int,
    sync_failures: int,
) -> str:
    if processed == 0 and (persist_failures > 0 or sync_failures > 0):
        return "failed"
    if persist_failures > 0 or sync_failures > 0:
        return "degraded"
    return "completed"


async def _process_post_rows(
    *,
    session: Any,
    rows: list[Mapping[str, Any]],
    workflow_input: LegacyLabelBackfillWorkflowInput,
    deps: LegacyLabelBackfillWorkflowDeps,
) -> tuple[int, int, int]:
    processed = 0
    persist_failures = 0
    sync_failures = 0

    for row in rows:
        analysis = _build_analysis(row, json_sanitize=deps.json_sanitize)
        try:
            await deps.upsert_post_label(
                session=session,
                post_id=int(row["post_id"]),
                text_norm_hash=row.get("text_norm_hash"),
                llm_version=str(row.get("llm_version") or "legacy"),
                model_name=str(row.get("llm_version") or "legacy"),
                prompt_version=workflow_input.prompt_version,
                analysis=analysis,
                score=_build_score(row),
                input_chars=0,
                output_chars=0,
            )
            try:
                await deps.sync_llm_terms(
                    session,
                    analysis=analysis,
                    llm_version=str(row.get("llm_version") or "legacy"),
                    prompt_version=workflow_input.prompt_version,
                )
            except Exception:
                sync_failures += 1
                logger.warning(
                    "backfill_legacy_labels: sync_llm_terms failed for post_id=%s",
                    row.get("post_id"),
                )
            processed += 1
            if processed % 200 == 0:
                await session.commit()
        except Exception:
            persist_failures += 1
            await session.rollback()
            continue

    await session.commit()
    return processed, persist_failures, sync_failures


async def _process_comment_rows(
    *,
    session: Any,
    rows: list[Mapping[str, Any]],
    workflow_input: LegacyLabelBackfillWorkflowInput,
    deps: LegacyLabelBackfillWorkflowDeps,
) -> tuple[int, int, int]:
    processed = 0
    persist_failures = 0
    sync_failures = 0

    for row in rows:
        analysis = _build_analysis(row, json_sanitize=deps.json_sanitize)
        try:
            await deps.upsert_comment_label(
                session=session,
                comment_id=int(row["comment_id"]),
                llm_version=str(row.get("llm_version") or "legacy"),
                model_name=str(row.get("llm_version") or "legacy"),
                prompt_version=workflow_input.prompt_version,
                analysis=analysis,
                score=_build_score(row),
                input_chars=0,
                output_chars=0,
            )
            try:
                await deps.sync_llm_terms(
                    session,
                    analysis=analysis,
                    llm_version=str(row.get("llm_version") or "legacy"),
                    prompt_version=workflow_input.prompt_version,
                )
            except Exception:
                sync_failures += 1
                logger.warning(
                    "backfill_legacy_labels: sync_llm_terms failed for comment_id=%s",
                    row.get("comment_id"),
                )
            processed += 1
            if processed % 200 == 0:
                await session.commit()
        except Exception:
            persist_failures += 1
            await session.rollback()
            continue

    await session.commit()
    return processed, persist_failures, sync_failures


async def run_legacy_label_backfill_workflow(
    *,
    workflow_input: LegacyLabelBackfillWorkflowInput,
    deps: LegacyLabelBackfillWorkflowDeps,
) -> dict[str, Any]:
    async with deps.session_factory() as session:
        post_rows_result = await session.execute(
            _POST_BACKFILL_SQL,
            {"limit": int(workflow_input.limit)},
        )
        post_rows = list(post_rows_result.mappings().all())
        (
            post_processed,
            post_persist_failures,
            post_sync_failures,
        ) = await _process_post_rows(
            session=session,
            rows=post_rows,
            workflow_input=workflow_input,
            deps=deps,
        )

        comment_rows_result = await session.execute(
            _COMMENT_BACKFILL_SQL,
            {"limit": int(workflow_input.limit)},
        )
        comment_rows = list(comment_rows_result.mappings().all())
        (
            comment_processed,
            comment_persist_failures,
            comment_sync_failures,
        ) = await _process_comment_rows(
            session=session,
            rows=comment_rows,
            workflow_input=workflow_input,
            deps=deps,
        )

    processed = post_processed + comment_processed
    persist_failures = post_persist_failures + comment_persist_failures
    sync_failures = post_sync_failures + comment_sync_failures

    return {
        "processed": processed,
        "post_processed": post_processed,
        "comment_processed": comment_processed,
        "persist_failures": persist_failures,
        "sync_failures": sync_failures,
        "status": _resolve_status(
            processed=processed,
            persist_failures=persist_failures,
            sync_failures=sync_failures,
        ),
    }


__all__ = [
    "LegacyLabelBackfillWorkflowDeps",
    "LegacyLabelBackfillWorkflowInput",
    "run_legacy_label_backfill_workflow",
]
