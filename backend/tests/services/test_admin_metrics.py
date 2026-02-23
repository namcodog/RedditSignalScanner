import pytest
from unittest.mock import MagicMock

from app.api.admin import metrics
from app.interfaces.semantic_provider import SemanticMetrics


class DummyProvider:
    async def load(self):
        return {}

    async def get_metrics(self) -> SemanticMetrics:
        return SemanticMetrics(
            db_hits=1,
            yaml_fallbacks=0,
            cache_hit_rate=1.0,
            last_refresh="2025-11-23T00:00:00Z",
            total_terms=10,
            load_latency_p95_ms=5.0,
        )

    async def reload(self) -> None:
        return None


@pytest.mark.asyncio
async def test_get_semantic_metrics():
    payload = MagicMock()
    data = await metrics.get_semantic_metrics(provider=DummyProvider(), payload=payload)
    assert data["db_hits"] == 1
    assert data["total_terms"] == 10


class _FakeMonitoringRedis:
    def __init__(self, *, contract_health: dict | None, updated_at: str | None = None) -> None:
        self._contract_health = contract_health
        self._updated_at = updated_at

    async def hget(self, name: str, key: str):  # type: ignore[override]
        if key == "updated_at":
            return (self._updated_at or "").encode("utf-8") if self._updated_at else None
        if key == "contract_health":
            if self._contract_health is None:
                return None
            import json

            return json.dumps(self._contract_health).encode("utf-8")
        return None


@pytest.mark.asyncio
async def test_get_contract_health_reads_dashboard(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeMonitoringRedis(
        contract_health={"status": "ok", "report": {"tasks": {"total": 1}}},
        updated_at="2025-12-29T00:00:00Z",
    )
    monkeypatch.setattr(metrics, "get_monitoring_redis", lambda request: fake)

    request = MagicMock()
    payload = MagicMock()
    data = await metrics.get_contract_health(request=request, payload=payload)
    assert data["enabled"] is True
    assert data["contract_health"]["status"] == "ok"
