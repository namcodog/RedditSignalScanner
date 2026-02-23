import os
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.report_service import ReportService
from app.services.report_service import ReportServiceConfig

# 避免 session 级 DB reset（baseline smoke）
os.environ.setdefault("SKIP_DB_RESET", "1")


@pytest.mark.asyncio
async def test_report_service_market_mode_flag(monkeypatch):
    # 最小 smoke：开启 market 模式时 _is_market_mode_enabled 返回 True
    monkeypatch.setattr("app.services.report_service.settings.enable_market_report", True)
    svc = ReportService(db=None, repository=MagicMock(), cache=MagicMock(), config=ReportServiceConfig({}, 60, "1.0"))
    assert svc._is_market_mode_enabled() is True  # type: ignore[attr-defined]
