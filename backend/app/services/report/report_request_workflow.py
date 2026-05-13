from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import UUID

from app.schemas.report_payload import ReportPayload

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReportRequestWorkflowInput:
    task_id: UUID
    user_id: UUID
    inline_llm_enabled: bool


@dataclass(slots=True)
class ReportRequestWorkflowDeps:
    load_context: Callable[[UUID, UUID], Awaitable[Any]]
    cache_get: Callable[[str], Awaitable[ReportPayload | None]] | None
    cache_set: Callable[[str, ReportPayload], Awaitable[None]] | None
    validate_analysis_payload: Callable[[Any], Any]
    assemble_payload: Callable[[Any, Any, bool], Awaitable[Any]]


@dataclass(slots=True)
class ReportRequestWorkflowResult:
    payload: ReportPayload
    cache_hit: bool


async def run_report_request_workflow(
    *,
    workflow_input: ReportRequestWorkflowInput,
    deps: ReportRequestWorkflowDeps,
) -> ReportRequestWorkflowResult:
    context = await deps.load_context(
        workflow_input.task_id,
        workflow_input.user_id,
    )

    task = context.task
    analysis = context.analysis
    cache_key = context.cache_key

    if deps.cache_get is not None:
        cached = await deps.cache_get(cache_key)
        if cached is not None and cached.generated_at == analysis.report.generated_at:
            logger.debug("Cache hit for report task %s", workflow_input.task_id)
            return ReportRequestWorkflowResult(payload=cached, cache_hit=True)

    analysis_payload = deps.validate_analysis_payload(analysis)
    assembly_result = await deps.assemble_payload(
        task,
        analysis_payload,
        workflow_input.inline_llm_enabled,
    )
    payload = assembly_result.payload

    logger.debug(
        "Generated report payload for task %s (status=%s)",
        task.id,
        task.status,
    )
    if deps.cache_set is not None:
        await deps.cache_set(cache_key, payload)

    return ReportRequestWorkflowResult(payload=payload, cache_hit=False)


__all__ = [
    "ReportRequestWorkflowDeps",
    "ReportRequestWorkflowInput",
    "ReportRequestWorkflowResult",
    "run_report_request_workflow",
]
