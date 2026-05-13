from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.services.report.report_runtime import (
    ReportRequestDepsFactoryInput,
    build_report_request_workflow_deps,
)


@pytest.mark.asyncio
async def test_report_request_deps_factory_load_context_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    expected = SimpleNamespace(cache_key="report:key")
    assembly_deps = SimpleNamespace(name="assembly")

    async def _fake_loader(*, task_id, user_id, deps):
        captured["task_id"] = task_id
        captured["user_id"] = user_id
        captured["deps"] = deps
        return expected

    monkeypatch.setattr(
        "app.services.report.report_runtime_factory.load_report_request_context",
        _fake_loader,
    )

    factory_input = ReportRequestDepsFactoryInput(
        load_task_with_analysis=AsyncMock(),
        is_membership_allowed=lambda _: True,
        make_not_found_error=RuntimeError,
        make_access_denied_error=PermissionError,
        make_not_ready_error=ValueError,
        cache_get=None,
        cache_set=None,
        validate_analysis_payload=Mock(),
        assembly_deps=assembly_deps,
        prefer_market_report=False,
    )

    deps = build_report_request_workflow_deps(factory_input)
    task_id = uuid4()
    user_id = uuid4()

    result = await deps.load_context(task_id, user_id)

    assert result is expected
    assert captured["task_id"] == task_id
    assert captured["user_id"] == user_id


@pytest.mark.asyncio
async def test_report_request_deps_factory_assemble_payload_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    expected = SimpleNamespace(payload=SimpleNamespace(generated_at="now"))
    assembly_deps = SimpleNamespace(name="assembly")

    async def _fake_assemble(*, assembly_input, deps):
        captured["assembly_input"] = assembly_input
        captured["deps"] = deps
        return expected

    monkeypatch.setattr(
        "app.services.report.report_runtime_factory.assemble_report_payload",
        _fake_assemble,
    )

    factory_input = ReportRequestDepsFactoryInput(
        load_task_with_analysis=AsyncMock(),
        is_membership_allowed=lambda _: True,
        make_not_found_error=RuntimeError,
        make_access_denied_error=PermissionError,
        make_not_ready_error=ValueError,
        cache_get=None,
        cache_set=None,
        validate_analysis_payload=Mock(),
        assembly_deps=assembly_deps,
        prefer_market_report=True,
    )

    deps = build_report_request_workflow_deps(factory_input)
    task = SimpleNamespace(product_description="demo")
    analysis = SimpleNamespace(
        sources=SimpleNamespace(report_structured={}, product_description="", facts_slice={}),
        insights=SimpleNamespace(pain_points=[]),
    )

    result = await deps.assemble_payload(task, analysis, True)

    assert result is expected
    assert captured["assembly_input"].task is task
    assert captured["assembly_input"].analysis is analysis
    assert captured["assembly_input"].inline_llm_enabled is True
    assert captured["assembly_input"].prefer_market_report is True
    assert captured["deps"] is assembly_deps
