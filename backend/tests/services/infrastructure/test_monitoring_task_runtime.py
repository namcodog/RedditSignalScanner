from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.middleware.route_metrics import DEFAULT_ROUTE_METRICS_KEY_PREFIX
from app.services.infrastructure.monitoring_task_runtime import (
    build_monitoring_runtime_dependencies,
    run_collect_test_logs,
    run_monitor_api_calls,
    run_update_performance_dashboard,
)
from app.services.infrastructure.monitoring_task_support import (
    load_route_call_metrics,
)


class _FakeRedis:
    def __init__(self, values: dict[str, Any] | None = None) -> None:
        self.values = values or {}
        self.hashes: dict[str, dict[str, Any]] = {}

    def get(self, key: str) -> Any:
        value = self.values.get(key)
        if value is None:
            return None
        return str(value)

    def hset(
        self,
        name: str,
        key: str | None = None,
        value: Any | None = None,
        mapping: dict[str, Any] | None = None,
    ) -> int:
        if name not in self.hashes:
            self.hashes[name] = {}
        if mapping is not None:
            self.hashes[name].update(mapping)
        elif key is not None:
            self.hashes[name][str(key)] = value
        return 1

    def hgetall(self, name: str) -> dict[str, Any]:
        return self.hashes.get(name, {})

    def delete(self, key: str) -> int:
        self.values.pop(key, None)
        return 1

    def rpush(self, key: str, *values: Any) -> int:
        self.values[key] = list(values)
        return len(values)

    def ltrim(self, key: str, start: int, end: int) -> None:
        current = self.values.get(key)
        if isinstance(current, list):
            self.values[key] = current[start : end + 1]

    def expire(self, key: str, ttl: int) -> None:
        self.values[f"{key}:ttl"] = ttl


def test_run_monitor_api_calls_uses_injected_threshold() -> None:
    alerts: list[tuple[str, str]] = []
    fake = _FakeRedis({"api_calls_per_minute": 61})

    payload = run_monitor_api_calls(
        settings=object(),
        api_call_threshold=55,
        get_metrics_redis=lambda _settings: fake,
        send_alert=lambda level, message: alerts.append((level, message)),
    )

    assert payload == {"api_calls_last_minute": 61, "threshold": 55}
    assert alerts == [("warning", "API 调用接近限制: 61/60")]


def test_run_update_performance_dashboard_writes_legacy_top_paths() -> None:
    fake = _FakeRedis()
    fake.hashes[f"{DEFAULT_ROUTE_METRICS_KEY_PREFIX}:123"] = {
        "golden|_total": "2",
        "legacy|_total": "5",
        "legacy|GET|/api/auth/me": "3",
        "legacy|GET|/api/reports": "2",
    }
    dashboards: list[dict[str, Any]] = []

    payload = run_update_performance_dashboard(
        settings=object(),
        load_e2e_metrics=lambda: {"runs": [{"status": "success", "id": "demo"}]},
        get_metrics_redis=lambda _settings: fake,
        route_metrics_bucket=lambda: 123,
        load_route_call_metrics=load_route_call_metrics,
        update_dashboard=lambda _settings, values: dashboards.append(values),
        route_metrics_top_n=5,
    )

    assert payload["golden_calls_last_minute"] == 2
    assert payload["legacy_calls_last_minute"] == 5
    assert payload["legacy_top_paths_last_minute"][0]["route"] == "GET /api/auth/me"
    assert dashboards and dashboards[0]["legacy_calls_last_minute"] == 5


def test_run_collect_test_logs_persists_tail(tmp_path: Path) -> None:
    log_path = tmp_path / "e2e.log"
    log_path.write_text("a\nb\nc\n", encoding="utf-8")
    fake = _FakeRedis()

    payload = run_collect_test_logs(
        settings=object(),
        test_log_path=log_path,
        max_lines=2,
        get_metrics_redis=lambda _settings: fake,
        send_alert=lambda _level, _message: None,
    )

    assert payload == {"status": "ok", "lines": 2}
    assert fake.values["logs:test_e2e"] == ["b", "c"]
    assert fake.values["logs:test_e2e:ttl"] == 3600


def test_build_monitoring_runtime_dependencies_keeps_injected_callables() -> None:
    marker = datetime(2026, 3, 17, tzinfo=timezone.utc)
    deps = build_monitoring_runtime_dependencies(
        get_metrics_redis=lambda _settings: _FakeRedis(),
        send_alert=lambda _level, _message: None,
        load_e2e_metrics=lambda: {"runs": []},
        update_dashboard=lambda _settings, _values: None,
        route_metrics_bucket=lambda: 123,
        load_route_call_metrics=lambda *_args, **_kwargs: (0, 0, []),
        cache_manager_factory=lambda **_kwargs: object(),
        run_coro=lambda coro: None,
        calculate_cache_health=lambda **_kwargs: None,
        build_error_result=lambda **_kwargs: {"status": "error"},
        serialize_result=lambda result: result,
        as_int=lambda value, default: int(value or default),
        as_float=lambda value, default: float(value or default),
        utc_now=lambda: marker,
        build_contract_health_thresholds=lambda **_kwargs: {},
        build_contract_health_result=lambda **_kwargs: None,
        finalize_contract_health_result=lambda **_kwargs: None,
        write_contract_health_audit_events=lambda *_args, **_kwargs: None,
        load_community_pool_size=lambda: None,
    )

    assert deps.route_metrics_bucket() == 123
    assert deps.utc_now() == marker
