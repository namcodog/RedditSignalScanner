from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from app.schemas.monitoring import (
    ContractHealthResult,
    MonitoringAlertPayload,
    MonitoringDegradedCheck,
)
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


def test_monitor_cache_health_marks_degraded_on_partial_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeCacheManager:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        async def calculate_cache_hit_rate(self, _seed_names: list[str]) -> float:
            return 0.45

    async def _fake_seed_names() -> list[str]:
        return ["r/python"]

    async def _fake_entity_metrics(*, cutoff: Any) -> Dict[str, Any]:
        raise RuntimeError(f"boom@{cutoff}")

    async def _fake_maintenance() -> Dict[str, Dict[str, Any] | None]:
        return {
            "cleanup": {"deleted_count": 3},
            "metrics_snapshot": {"id": 42},
        }

    monkeypatch.setattr(
        mt,
        "get_settings",
        lambda: SimpleNamespace(reddit_cache_redis_url="redis://test", reddit_cache_ttl_seconds=60),
    )
    monkeypatch.setattr(mt, "CacheManager", _FakeCacheManager)
    monkeypatch.setattr(mt, "_load_cache_seed_names", _fake_seed_names)
    monkeypatch.setattr(mt, "_load_entity_extraction_metrics", _fake_entity_metrics)
    monkeypatch.setattr(mt, "_run_cache_maintenance_tasks", _fake_maintenance)
    monkeypatch.setattr(mt, "run_coro", lambda coro: asyncio.run(coro))

    payload = mt.monitor_cache_health()

    assert payload["status"] == "degraded"
    assert "generated_at" in payload
    assert payload["cleanup_deleted"] == 3
    assert payload["storage_metrics_id"] == 42
    assert payload["degraded_checks"][0]["code"] == "entity_rate_unavailable"


def test_monitor_contract_health_serializes_finalized_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_build(**_kwargs: Any) -> ContractHealthResult:
        return ContractHealthResult(
            status="ok",
            generated_at=datetime(2026, 3, 14, tzinfo=timezone.utc),
            window_hours=24,
            report={},
            alerts=[
                MonitoringAlertPayload(
                    level="warning",
                    code="demo",
                    message="demo warning",
                    details={},
                )
            ],
        )

    def _fake_finalize(**kwargs: Any) -> ContractHealthResult:
        result: ContractHealthResult = kwargs["result"]
        result.status = "degraded"
        result.degraded_checks.append(
            MonitoringDegradedCheck(
                code="audit_event_write_failed",
                message="audit down",
            )
        )
        return result

    monkeypatch.setattr(mt, "_build_contract_health_result", _fake_build)
    monkeypatch.setattr(mt, "_finalize_contract_health_result", _fake_finalize)
    monkeypatch.setattr(mt, "run_coro", lambda coro: asyncio.run(coro))
    monkeypatch.setattr(mt, "get_settings", lambda: SimpleNamespace())

    result = mt.monitor_contract_health()

    assert result["status"] == "degraded"
    assert result["generated_at"] == "2026-03-14T00:00:00Z"
    assert result["degraded_checks"][0]["code"] == "audit_event_write_failed"


def test_monitor_cache_health_error_payload_uses_shared_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        mt,
        "get_settings",
        lambda: SimpleNamespace(reddit_cache_redis_url="redis://test", reddit_cache_ttl_seconds=60),
    )
    monkeypatch.setattr(
        mt,
        "CacheManager",
        lambda *_args, **_kwargs: SimpleNamespace(),
    )
    def _boom(coro: Any) -> Any:
        coro.close()
        raise RuntimeError("cache down")

    monkeypatch.setattr(mt, "run_coro", _boom)

    payload = mt.monitor_cache_health()

    assert payload["status"] == "error"
    assert payload["message"] == "cache down"
    assert "generated_at" in payload
