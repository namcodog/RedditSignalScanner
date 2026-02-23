from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import pytest

from app.tasks import monitoring_task as mt
from app.middleware.route_metrics import DEFAULT_ROUTE_METRICS_KEY_PREFIX


class _FakeRedis:
    def __init__(self, values: Dict[str, Any] | None = None) -> None:
        self.values = values or {}
        self.hashes: Dict[str, Dict[str, Any]] = {}

    # simple kv get
    def get(self, key: str) -> bytes | str | None:
        v = self.values.get(key)
        if v is None:
            return None
        return str(v)

    # partial hash ops used in _update_dashboard
    def hset(self, name: str, key: str | None = None, value: Any | None = None, mapping: Dict[str, Any] | None = None):  # type: ignore[override]
        if name not in self.hashes:
            self.hashes[name] = {}
        if mapping is not None:
            self.hashes[name].update(mapping)
        elif key is not None:
            self.hashes[name][str(key)] = value
        return 1

    def hget(self, name: str, key: str) -> Any | None:
        return self.hashes.get(name, {}).get(str(key))

    def hgetall(self, name: str) -> Dict[str, Any]:
        return self.hashes.get(name, {})

    # used in collect_test_logs
    def delete(self, key: str) -> int:
        self.values.pop(key, None)
        return 1

    def rpush(self, key: str, *values: Any) -> int:
        self.values[key] = list(values)
        return len(values)

    def ltrim(self, key: str, start: int, end: int) -> None:
        arr = self.values.get(key)
        if isinstance(arr, list):
            self.values[key] = arr[start : end + 1]

    def expire(self, key: str, ttl: int) -> None:
        # ignore in tests
        pass


@pytest.mark.parametrize("calls, expect_alert", [(10, False), (60, True)])
def test_monitor_api_calls_threshold(monkeypatch: pytest.MonkeyPatch, calls: int, expect_alert: bool) -> None:
    fake = _FakeRedis({"api_calls_per_minute": calls})
    monkeypatch.setenv("MONITOR_API_THRESHOLD", "55")
    monkeypatch.setattr(mt, "_get_metrics_redis", lambda settings: fake)

    result = mt.monitor_api_calls()
    assert "api_calls_last_minute" in result
    assert result["threshold"] == 55


def test_update_performance_dashboard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Prepare a small metrics file for monitor_e2e_tests
    metrics_path = tmp_path / "e2e.json"
    metrics_path.write_text(json.dumps({"runs": [{"status": "success", "duration_seconds": 1.2}]}), encoding="utf-8")
    monkeypatch.setenv("TEST_METRICS_PATH", str(metrics_path))

    fake = _FakeRedis()
    monkeypatch.setattr(mt, "_route_metrics_bucket", lambda: 123)
    fake.hashes[f"{DEFAULT_ROUTE_METRICS_KEY_PREFIX}:123"] = {
        "golden|_total": "2",
        "legacy|_total": "5",
        "legacy|GET|/api/auth/me": "3",
        "legacy|GET|/api/guidance/input": "2",
    }
    monkeypatch.setattr(mt, "_get_metrics_redis", lambda settings: fake)

    payload = mt.update_performance_dashboard()
    assert "report_generated_at" in payload
    # dashboard content should be written as a hash
    assert "last_e2e_run" in payload
    assert payload["golden_calls_last_minute"] == 2
    assert payload["legacy_calls_last_minute"] == 5
    assert payload["legacy_top_paths_last_minute"][0]["route"] == "GET /api/auth/me"
