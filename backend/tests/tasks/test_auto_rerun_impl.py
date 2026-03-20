from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus
from app.services.analysis.analysis_engine import AnalysisResult


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


@pytest.mark.asyncio
async def test_auto_rerun_impl_schedules_inline_followup_in_dev_mode(
    db_session: AsyncSession,
    test_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """开发环境 inline 模式下，follow-up 必须继续 inline，而不是退回 Celery send_task。"""
    import app.tasks.analysis_task as analysis_task_module

    task_id = uuid.uuid4()
    db_session.add(
        Task(
            id=task_id,
            user_id=test_user.id,
            product_description="demo product description for inline followup",
            status=TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()

    async def _fake_run_analysis(*_: object, **__: object) -> AnalysisResult:
        return AnalysisResult(
            insights={"pain_points": [], "competitors": [], "opportunities": []},
            sources={
                "report_tier": "C_scouting",
                "analysis_blocked": "insufficient_samples",
                "remediation_actions": [{"type": "backfill_posts", "targets": 5}],
            },
            report_html="",
            action_items=[],
            confidence_score=0.0,
        )

    async def _noop_async(*_: object, **__: object) -> None:
        return None

    cached_status_payloads: list[dict[str, Any]] = []

    async def _fake_cache_status(*args: object, **kwargs: object) -> None:
        task_id_raw = args[0] if len(args) > 0 else kwargs.get("task_id")
        status_raw = args[1] if len(args) > 1 else kwargs.get("status")
        progress_raw = args[2] if len(args) > 2 else kwargs.get("progress", 0)
        message_raw = args[3] if len(args) > 3 else kwargs.get("message", "")
        cached_status_payloads.append(
            {
                "task_id": str(task_id_raw),
                "status": str(status_raw),
                "progress": int(progress_raw),
                "message": str(message_raw),
                "stage": kwargs.get("stage"),
                "next_action": kwargs.get("next_action"),
                "details": kwargs.get("details"),
            }
        )

    monkeypatch.setattr(analysis_task_module, "run_analysis", _fake_run_analysis)
    monkeypatch.setattr(analysis_task_module, "_store_analysis_results", _noop_async)
    monkeypatch.setattr(analysis_task_module, "_cache_status", _fake_cache_status)
    monkeypatch.setattr(analysis_task_module, "_warmup_inline_dispatch_enabled", lambda: True)
    monkeypatch.setattr(analysis_task_module, "_INLINE_WARMUP_TASKS", set())

    celery_calls: list[dict[str, Any]] = []

    def _fake_send_task(*args: object, **kwargs: object) -> None:  # noqa: ANN401
        celery_calls.append({"args": args, "kwargs": kwargs})
        return None

    monkeypatch.setattr(analysis_task_module.celery_app, "send_task", _fake_send_task)

    scheduled_coroutines: list[Any] = []  # noqa: ANN401

    class _FakeTask:
        def add_done_callback(self, _cb: object) -> None:
            return None

    def _fake_create_task(coro: Any) -> _FakeTask:  # noqa: ANN401
        scheduled_coroutines.append(coro)
        return _FakeTask()

    monkeypatch.setattr(analysis_task_module.asyncio, "create_task", _fake_create_task)

    try:
        res = await analysis_task_module._auto_rerun_impl(
            task_id=task_id,
            user_id=test_user.id,
            attempt=1,
        )
    finally:
        for coro in scheduled_coroutines:
            close = getattr(coro, "close", None)
            if callable(close):
                close()

    assert res.get("status") == "ok"
    assert celery_calls == []
    assert scheduled_coroutines, "Expected inline follow-up coroutine to be scheduled"
    assert scheduled_coroutines[0].cr_code.co_name == "_dispatch_auto_rerun_inline"

    followup_status = [
        payload
        for payload in cached_status_payloads
        if payload.get("next_action") == "auto_rerun_scheduled"
    ]
    assert followup_status, "Expected warmup follow-up status payload"
    details = followup_status[-1].get("details") or {}
    assert isinstance(details, dict)
    assert details.get("dispatch_mode") == "inline"
