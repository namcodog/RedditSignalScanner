from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from app.tasks import maintenance_task, monitoring_task


@pytest.mark.parametrize(
    "task_name",
    [
        "refresh_posts_latest",
        "cleanup_expired_posts_hot",
        "collect_storage_metrics",
    ],
)
def test_maintenance_tasks_delegate_to_async_impl(monkeypatch: pytest.MonkeyPatch, task_name: str) -> None:
    expected = {"status": "ok", "task": task_name}
    called: dict[str, bool] = {"impl": False, "run": False}

    async def fake_impl(*_: Any, **__: Any) -> dict[str, Any]:
        called["impl"] = True
        return expected

    def fake_run(coro: Any) -> dict[str, Any]:
        called["run"] = True
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    monkeypatch.setattr(maintenance_task, f"{task_name}_impl", fake_impl)
    monkeypatch.setattr(asyncio, "run", fake_run)

    task_callable = getattr(maintenance_task, task_name)
    result = task_callable()

    assert result == expected
    assert called["impl"] and called["run"]


def test_monitor_api_calls_uses_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyRedis:
        def __init__(self, value: bytes) -> None:
            self._value = value

        def get(self, key: str) -> bytes:
            assert key == "api_calls_per_minute"
            return self._value

    alerts: list[tuple[str, str]] = []

    monkeypatch.setattr(
        monitoring_task,
        "_get_metrics_redis",
        lambda settings: DummyRedis(b"60"),
    )
    monkeypatch.setattr(
        monitoring_task,
        "_send_alert",
        lambda level, message: alerts.append((level, message)),
    )

    result = monitoring_task.monitor_api_calls()

    assert result["api_calls_last_minute"] == 60
    assert result["threshold"] == monitoring_task.API_CALL_THRESHOLD
    assert alerts, "Rate limit warning should be triggered when value exceeds threshold"


def test_monitor_e2e_tests_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_path = tmp_path / "metrics.json"
    monkeypatch.setattr(monitoring_task, "TEST_METRICS_PATH", fake_path)

    result = monitoring_task.monitor_e2e_tests()

    assert result == {"status": "missing"}


def test_monitor_e2e_tests_parses_metrics(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    metrics_payload = {
        "runs": [
            {"status": "success", "duration_seconds": 120},
            {"status": "failed", "duration_seconds": 310},
        ]
    }
    metrics_file = tmp_path / "metrics.json"
    metrics_file.write_text(json.dumps(metrics_payload), encoding="utf-8")

    alerts: list[tuple[str, str]] = []
    monkeypatch.setattr(monitoring_task, "TEST_METRICS_PATH", metrics_file)
    monkeypatch.setattr(monitoring_task, "_update_dashboard", lambda settings, values: None)
    monkeypatch.setattr(monitoring_task, "_send_alert", lambda level, message: alerts.append((level, message)))
    monkeypatch.setattr(
        monitoring_task,
        "_get_metrics_redis",
        lambda settings: type("DummyDashboardRedis", (), {"hset": lambda *_, **__: None})(),
    )

    result = monitoring_task.monitor_e2e_tests()

    assert result["runs"] == 2
    assert result["failed"] == 1
    assert isinstance(result["failure_rate"], float)
    assert alerts, "Failure rate should trigger alert when exceeding threshold"
