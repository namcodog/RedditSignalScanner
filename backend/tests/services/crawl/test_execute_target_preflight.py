from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.services.crawl.execute_target_preflight import (
    ExecuteTargetPreflightDeps,
    ExecuteTargetPreflightInput,
    prepare_execute_target_preflight,
)


class _ScalarResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value


class _MappingsResult:
    def __init__(self, row: Any) -> None:
        self._row = row

    def mappings(self) -> "_MappingsResult":
        return self

    def first(self) -> Any:
        return self._row


class _UpdateResult:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class _FakeSession:
    def __init__(self, *, record: dict[str, Any] | None, update_rowcount: int = 1) -> None:
        self._record = record
        self._update_rowcount = update_rowcount

    async def connection(self) -> None:
        return None

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Any:
        sql = str(statement)
        if "to_regclass('public.crawler_run_targets')" in sql:
            return _ScalarResult("crawler_run_targets")
        if "SELECT id, crawl_run_id, subreddit, status, config, metrics" in sql:
            return _MappingsResult(self._record)
        if "UPDATE crawler_run_targets" in sql:
            return _UpdateResult(self._update_rowcount)
        if "SELECT status" in sql:
            return _ScalarResult("running")
        raise AssertionError(f"unexpected SQL: {sql} params={params}")


def _record(*, status: str = "queued") -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "id": "target-1",
        "crawl_run_id": "run-1",
        "subreddit": "r/demo",
        "status": status,
        "config": {
            "plan_kind": "patrol",
            "target_type": "subreddit",
            "target_value": "r/demo",
            "reason": "cache_expired",
            "limits": {"posts_limit": 50},
            "window": {
                "since": (now - timedelta(days=1)).isoformat(),
                "until": now.isoformat(),
            },
        },
        "metrics": {"existing": True},
        "idempotency_key": "idem-1",
    }


def _deps(calls: dict[str, Any], *, lock_acquired: bool = True) -> ExecuteTargetPreflightDeps:
    async def _audit_missing_target(*, session: Any, target_id: str, attempts: int) -> None:
        calls.setdefault("audit", []).append({"target_id": target_id, "attempts": attempts})

    async def _apply_session_change(session: Any, *, context: str, change: Any) -> bool:
        calls.setdefault("apply", []).append(context)
        await change()
        return True

    async def _commit_session(_session: Any, *, context: str) -> bool:
        calls.setdefault("commit", []).append(context)
        return True

    async def _rollback_session_quietly(_session: Any, *, context: str) -> None:
        calls.setdefault("rollback", []).append(context)

    async def _set_target_failed(*args: Any, **kwargs: Any) -> bool:
        calls.setdefault("failed", []).append(kwargs)
        return True

    async def _set_target_partial(*args: Any, **kwargs: Any) -> bool:
        calls.setdefault("partial", []).append(kwargs)
        return True

    async def _load_community_blacklist_status(*args: Any, **kwargs: Any) -> bool | None:
        return None

    async def _try_acquire_community_lock(*args: Any, **kwargs: Any) -> bool:
        return lock_acquired

    async def _enqueue_compensation_target(**kwargs: Any) -> str | None:
        calls.setdefault("compensation", []).append(kwargs)
        return "comp-1"

    async def _mark_backfill_running(*args: Any, **kwargs: Any) -> None:
        calls.setdefault("backfill_running", []).append(kwargs)

    return ExecuteTargetPreflightDeps(
        ensure_dict=lambda value: value if isinstance(value, dict) else {},
        audit_missing_target=_audit_missing_target,
        apply_session_change=_apply_session_change,
        commit_session=_commit_session,
        rollback_session_quietly=_rollback_session_quietly,
        set_target_failed=_set_target_failed,
        set_target_partial=_set_target_partial,
        load_community_blacklist_status=_load_community_blacklist_status,
        needs_community_lock=lambda _kind: True,
        try_acquire_community_lock=_try_acquire_community_lock,
        enqueue_compensation_target=_enqueue_compensation_target,
        mark_backfill_running=_mark_backfill_running,
    )


@pytest.mark.asyncio
async def test_prepare_execute_target_preflight_missing_target_audits_and_fails() -> None:
    calls: dict[str, Any] = {}
    session = _FakeSession(record=None)

    result = await prepare_execute_target_preflight(
        preflight_input=ExecuteTargetPreflightInput(
            session=session,
            target_id="missing-target",
        ),
        deps=_deps(calls),
    )

    assert result.early_payload == {
        "status": "failed",
        "reason": "target_missing",
        "target_id": "missing-target",
    }
    assert result.context is None
    assert calls["audit"] == [{"target_id": "missing-target", "attempts": 3}]


@pytest.mark.asyncio
async def test_prepare_execute_target_preflight_returns_partial_when_community_lock_busy() -> None:
    calls: dict[str, Any] = {}
    session = _FakeSession(record=_record())

    result = await prepare_execute_target_preflight(
        preflight_input=ExecuteTargetPreflightInput(
            session=session,
            target_id="target-1",
        ),
        deps=_deps(calls, lock_acquired=False),
    )

    assert result.context is None
    assert result.early_payload is not None
    assert result.early_payload["status"] == "partial"
    assert result.early_payload["reason"] == "community_locked"
    assert result.early_payload["compensation_target_id"] == "comp-1"
    assert calls["commit"] == ["claim_target", "community_locked_compensation"]
    assert len(calls["partial"]) == 1
