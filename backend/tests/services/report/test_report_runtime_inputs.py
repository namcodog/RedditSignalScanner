from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.report.report_runtime_inputs import (
    build_runtime_assembly_factory_input,
    build_runtime_request_factory_input,
)


def _build_runtime() -> SimpleNamespace:
    repository = SimpleNamespace(
        get_task_with_analysis=AsyncMock(),
        persist_report_structured=AsyncMock(return_value=True),
    )
    return SimpleNamespace(
        db=object(),
        repository=repository,
        config=SimpleNamespace(
            target_analysis_version="1.0",
            community_members={"r/demo": 123},
        ),
        cache_get=AsyncMock(),
        cache_set=AsyncMock(),
        controlled_build_context=Mock(),
        controlled_render_report=Mock(),
        quality_level=lambda: "standard",
        is_market_mode_enabled=lambda: True,
        fetch_community_member_count=AsyncMock(return_value=123),
        coerce_report_html=lambda raw: raw or "",
        validate_analysis_payload=Mock(return_value="validated"),
        build_assembly_deps=Mock(return_value="assembly-deps"),
    )


def test_build_runtime_assembly_factory_input_uses_runtime_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.services.report.report_runtime_inputs as mod

    runtime = _build_runtime()

    factory_input = build_runtime_assembly_factory_input(runtime)

    assert factory_input.quality_level == "standard"
    assert factory_input.product_description == getattr(
        mod.settings,
        "report_product_description",
        "跨境电商支付解决方案",
    )
    assert factory_input.prefer_market_report is True
    assert factory_input.fetch_member_count is runtime.fetch_community_member_count
    assert factory_input.reasoning_model_name == "deepseek/deepseek-v4-pro"


def test_build_runtime_request_factory_input_wraps_validate_and_builds_assembly() -> None:
    runtime = _build_runtime()

    factory_input = build_runtime_request_factory_input(
        runtime,
        not_found_error=RuntimeError,
        access_denied_error=PermissionError,
        not_ready_error=ValueError,
        validation_error=TypeError,
    )

    assert factory_input.assembly_deps == "assembly-deps"
    assert factory_input.prefer_market_report is True
    assert factory_input.validate_analysis_payload("analysis") == "validated"
    runtime.validate_analysis_payload.assert_called_once_with("analysis", error_cls=TypeError)
