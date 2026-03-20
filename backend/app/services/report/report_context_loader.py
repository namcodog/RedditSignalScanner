from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(slots=True, frozen=True)
class ReportRequestContext:
    task: Any
    analysis: Any
    cache_key: str


@dataclass(slots=True, frozen=True)
class ReportContextLoaderDeps:
    load_task_with_analysis: Callable[[UUID], Awaitable[Any | None]]
    is_membership_allowed: Callable[[Any], bool]
    make_not_found_error: Callable[[str], Exception]
    make_access_denied_error: Callable[[str], Exception]
    make_not_ready_error: Callable[[str], Exception]


async def load_report_request_context(
    *,
    task_id: UUID,
    user_id: UUID,
    deps: ReportContextLoaderDeps,
) -> ReportRequestContext:
    task = await deps.load_task_with_analysis(task_id)
    if task is None:
        raise deps.make_not_found_error("Task not found")

    if task.user_id != user_id:
        raise deps.make_access_denied_error("Not authorised to access this task")

    task_status = getattr(task, "status", None)
    if getattr(task_status, "value", task_status) != "completed":
        raise deps.make_not_ready_error("Task has not completed yet")

    analysis = getattr(task, "analysis", None)
    if analysis is None:
        raise deps.make_not_found_error("Analysis not found")

    if getattr(analysis, "report", None) is None:
        raise deps.make_not_found_error("Report not found")

    membership_level = getattr(getattr(task, "user", None), "membership_level", None)
    if not deps.is_membership_allowed(membership_level):
        raise deps.make_access_denied_error(
            "Your subscription tier does not include report access"
        )

    return ReportRequestContext(
        task=task,
        analysis=analysis,
        cache_key=f"report:{task_id}:{user_id}",
    )


__all__ = [
    "ReportContextLoaderDeps",
    "ReportRequestContext",
    "load_report_request_context",
]
