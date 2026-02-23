from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.services.analysis_engine import AnalysisResult


@pytest.mark.asyncio
async def test_auto_rerun_impl_does_not_mutate_frozen_analysis_result(
    db_session: AsyncSession,
    test_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Phase106: warmup auto_rerun 不能因为 AnalysisResult(frozen) 而崩。
    过去这里会对 result.sources 直接赋值触发 FrozenInstanceError。
    """
    import app.tasks.analysis_task as analysis_task_module

    task_id = uuid.uuid4()
    db_session.add(
        Task(
            id=task_id,
            user_id=test_user.id,
            product_description="demo product description for auto rerun test",
            status=TaskStatus.PENDING,
        )
    )
    await db_session.commit()

    async def _fake_run_analysis(*_: object, **__: object) -> AnalysisResult:
        return AnalysisResult(
            insights={"pain_points": [], "competitors": [], "opportunities": []},
            sources={"report_tier": "C_scouting"},
            report_html="",
            action_items=[],
            confidence_score=0.0,
        )

    async def _noop_async(*_: object, **__: object) -> None:
        return None

    def _never_rerun(*_: object, **__: object) -> tuple[bool, str]:
        return False, ""

    monkeypatch.setattr(analysis_task_module, "run_analysis", _fake_run_analysis)
    monkeypatch.setattr(analysis_task_module, "_store_analysis_results", _noop_async)
    monkeypatch.setattr(analysis_task_module, "_cache_status", _noop_async)
    monkeypatch.setattr(analysis_task_module, "_warmup_auto_rerun_needed", _never_rerun)

    res = await analysis_task_module._auto_rerun_impl(
        task_id=task_id,
        user_id=test_user.id,
        attempt=1,
    )
    assert res.get("status") == "ok"

