from __future__ import annotations

import json
from pathlib import Path

from app.tasks.monitoring_task import monitor_warmup_metrics


def test_warmup_cycle_end_to_end_smoke(tmp_path: Path) -> None:
    """
    A lightweight E2E smoke test that validates the warmup cycle surfaces metrics and
    can be exported to a JSON report. This avoids external service calls.
    """
    # 1) Collect warmup metrics (ensures crawler/monitoring stack is importable and callable)
    metrics = monitor_warmup_metrics()
    assert isinstance(metrics, dict)
    for key in [
        "timestamp",
        "api_calls_per_minute",
        "cache_hit_rate",
        "community_pool_size",
        "stale_communities_count",
    ]:
        assert key in metrics

    # 2) Serialize a report-like payload
    payload = {"warmup_metrics": metrics}
    out = tmp_path / "warmup-report.json"
    out.write_text(json.dumps(payload), encoding="utf-8")

    # 3) Validate the JSON file exists and is parseable
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert "warmup_metrics" in parsed

