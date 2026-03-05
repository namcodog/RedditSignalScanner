from app.services.report.report_service import ReportService
from app.core import config


def test_is_market_mode_enabled_with_flag(monkeypatch):
    monkeypatch.setattr(config.settings, "enable_market_report", True)
    monkeypatch.setattr(config.settings, "report_mode", "technical")
    assert ReportService._is_market_mode_enabled() is True


def test_is_market_mode_enabled_with_mode(monkeypatch):
    monkeypatch.setattr(config.settings, "enable_market_report", False)
    monkeypatch.setattr(config.settings, "report_mode", "market")
    assert ReportService._is_market_mode_enabled() is True


def test_is_market_mode_disabled(monkeypatch):
    monkeypatch.setattr(config.settings, "enable_market_report", False)
    monkeypatch.setattr(config.settings, "report_mode", "technical")
    assert ReportService._is_market_mode_enabled() is False
