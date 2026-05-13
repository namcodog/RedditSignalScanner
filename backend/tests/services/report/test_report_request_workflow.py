from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.report.report_request_workflow import (
    ReportRequestWorkflowDeps,
    ReportRequestWorkflowInput,
    run_report_request_workflow,
)


def _build_context() -> SimpleNamespace:
    generated_at = datetime.now(timezone.utc)
    payload = SimpleNamespace(generated_at=generated_at)
    analysis = SimpleNamespace(report=SimpleNamespace(generated_at=generated_at))
    task = SimpleNamespace(id=uuid4(), status="completed")
    return SimpleNamespace(task=task, analysis=analysis, cache_key="report:key"), payload


@pytest.mark.asyncio
async def test_report_request_workflow_returns_cache_hit_without_validation() -> None:
    context, payload = _build_context()
    load_context = AsyncMock(return_value=context)
    cache_get = AsyncMock(return_value=payload)
    validate = Mock()
    assemble = AsyncMock()

    result = await run_report_request_workflow(
        workflow_input=ReportRequestWorkflowInput(
            task_id=uuid4(),
            user_id=uuid4(),
            inline_llm_enabled=True,
        ),
        deps=ReportRequestWorkflowDeps(
            load_context=load_context,
            cache_get=cache_get,
            cache_set=AsyncMock(),
            validate_analysis_payload=validate,
            assemble_payload=assemble,
        ),
    )

    assert result.payload is payload
    assert result.cache_hit is True
    validate.assert_not_called()
    assemble.assert_not_awaited()


@pytest.mark.asyncio
async def test_report_request_workflow_builds_and_sets_cache_on_miss() -> None:
    context, cached_payload = _build_context()
    final_payload = SimpleNamespace(generated_at=cached_payload.generated_at)
    load_context = AsyncMock(return_value=context)
    cache_get = AsyncMock(return_value=None)
    cache_set = AsyncMock()
    validated = object()
    validate = Mock(return_value=validated)
    assemble = AsyncMock(return_value=SimpleNamespace(payload=final_payload))

    result = await run_report_request_workflow(
        workflow_input=ReportRequestWorkflowInput(
            task_id=uuid4(),
            user_id=uuid4(),
            inline_llm_enabled=False,
        ),
        deps=ReportRequestWorkflowDeps(
            load_context=load_context,
            cache_get=cache_get,
            cache_set=cache_set,
            validate_analysis_payload=validate,
            assemble_payload=assemble,
        ),
    )

    assert result.payload is final_payload
    assert result.cache_hit is False
    validate.assert_called_once_with(context.analysis)
    assemble.assert_awaited_once_with(context.task, validated, False)
    cache_set.assert_awaited_once_with(context.cache_key, final_payload)
