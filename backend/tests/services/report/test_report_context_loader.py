from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.models.task import TaskStatus
from app.models.user import MembershipLevel
from app.services.report.report_context_loader import (
    ReportContextLoaderDeps,
    load_report_request_context,
)


@dataclass
class _FakeUser:
    membership_level: MembershipLevel | None


@dataclass
class _FakeAnalysis:
    report: object | None


@dataclass
class _FakeTask:
    id: UUID
    user_id: UUID
    status: TaskStatus
    analysis: _FakeAnalysis | None
    user: _FakeUser | None


class _FakeRepository:
    def __init__(self, task: _FakeTask | None) -> None:
        self._task = task

    async def get_task_with_analysis(self, task_id: UUID) -> _FakeTask | None:
        if self._task and self._task.id == task_id:
            return self._task
        return None


def _deps(repo: _FakeRepository) -> ReportContextLoaderDeps:
    return ReportContextLoaderDeps(
        load_task_with_analysis=repo.get_task_with_analysis,
        is_membership_allowed=lambda membership_level: membership_level
        in {MembershipLevel.PRO, MembershipLevel.ENTERPRISE},
        make_not_found_error=RuntimeError,
        make_access_denied_error=PermissionError,
        make_not_ready_error=ValueError,
    )


@pytest.mark.asyncio
async def test_load_report_request_context_returns_task_analysis_and_cache_key() -> None:
    task_id = uuid4()
    user_id = uuid4()
    task = _FakeTask(
        id=task_id,
        user_id=user_id,
        status=TaskStatus.COMPLETED,
        analysis=_FakeAnalysis(report=SimpleNamespace(generated_at=None)),
        user=_FakeUser(membership_level=MembershipLevel.PRO),
    )
    context = await load_report_request_context(
        task_id=task_id,
        user_id=user_id,
        deps=_deps(_FakeRepository(task)),
    )

    assert context.task is task
    assert context.analysis is task.analysis
    assert context.cache_key == f"report:{task_id}:{user_id}"


@pytest.mark.asyncio
async def test_load_report_request_context_rejects_disallowed_membership() -> None:
    task_id = uuid4()
    user_id = uuid4()
    task = _FakeTask(
        id=task_id,
        user_id=user_id,
        status=TaskStatus.COMPLETED,
        analysis=_FakeAnalysis(report=SimpleNamespace(generated_at=None)),
        user=_FakeUser(membership_level=MembershipLevel.FREE),
    )

    with pytest.raises(PermissionError, match="subscription tier"):
        await load_report_request_context(
            task_id=task_id,
            user_id=user_id,
            deps=_deps(_FakeRepository(task)),
        )


@pytest.mark.asyncio
async def test_load_report_request_context_rejects_missing_report() -> None:
    task_id = uuid4()
    user_id = uuid4()
    task = _FakeTask(
        id=task_id,
        user_id=user_id,
        status=TaskStatus.COMPLETED,
        analysis=_FakeAnalysis(report=None),
        user=_FakeUser(membership_level=MembershipLevel.PRO),
    )

    with pytest.raises(RuntimeError, match="Report not found"):
        await load_report_request_context(
            task_id=task_id,
            user_id=user_id,
            deps=_deps(_FakeRepository(task)),
        )
