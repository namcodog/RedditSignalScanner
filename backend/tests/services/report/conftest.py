from __future__ import annotations

import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def _isolate_report_mode_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "enable_market_report", False, raising=False)
    monkeypatch.setattr(settings, "report_mode", "executive", raising=False)
    monkeypatch.setattr(
        settings,
        "market_report_template_path",
        "backend/config/report_templates/market_insight_v1.md",
        raising=False,
    )
