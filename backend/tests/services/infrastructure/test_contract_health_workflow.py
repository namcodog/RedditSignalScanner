from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.schemas.monitoring import (
    ContractHealthResult,
    MonitoringAlertPayload,
    MonitoringDegradedCheck,
)
from app.services.infrastructure import contract_health_workflow as chw


async def test_build_contract_health_result_uses_shared_rows_and_alerts(
    monkeypatch,
) -> None:
    now = datetime(2026, 3, 15, tzinfo=timezone.utc)
    rows = [SimpleNamespace(task_id="task-1")]

    async def _fake_load_rows(*, cutoff, now):  # type: ignore[no-untyped-def]
        assert cutoff == datetime(2026, 3, 14, tzinfo=timezone.utc)
        assert now == datetime(2026, 3, 15, tzinfo=timezone.utc)
        return rows

    monkeypatch.setattr(chw, "load_contract_health_rows", _fake_load_rows)
    monkeypatch.setattr(chw, "compute_contract_health", lambda rows, now, window: {"total": len(rows)})
    monkeypatch.setattr(
        chw,
        "evaluate_contract_health_alerts",
        lambda report, thresholds: [
            SimpleNamespace(level="warning", code="demo", message="demo warning", details={"count": report["total"]})
        ],
    )

    result = await chw.build_contract_health_result(
        window_hours=24,
        now=now,
        window=timedelta(hours=24),
        cutoff=now - timedelta(hours=24),
        thresholds=SimpleNamespace(),
    )

    assert result.status == "ok"
    assert result.window_hours == 24
    assert result.report == {"total": 1}
    assert result.alerts[0].code == "demo"


def test_finalize_contract_health_result_marks_degraded_on_audit_write_failure() -> None:
    sent: list[tuple[str, str]] = []
    dashboard_payloads: list[dict[str, object]] = []

    result = ContractHealthResult(
        status="ok",
        generated_at=datetime(2026, 3, 15, tzinfo=timezone.utc),
        window_hours=24,
        report={"total": 1},
        alerts=[
            MonitoringAlertPayload(
                level="warning",
                code="demo",
                message="demo warning",
                details={},
            )
        ],
    )

    finalized = chw.finalize_contract_health_result(
        result,
        settings=SimpleNamespace(),
        update_dashboard=lambda settings, values: dashboard_payloads.append(values),
        send_alert=lambda level, message: sent.append((level, message)),
        write_audit_events=lambda payload, alerts: (_ for _ in ()).throw(RuntimeError("audit down")),
    )

    assert dashboard_payloads
    assert sent == [("warning", "contract_health[demo]: demo warning")]
    assert finalized.status == "degraded"
    assert finalized.degraded_checks == [
        MonitoringDegradedCheck(code="audit_event_write_failed", message="audit down")
    ]

