from __future__ import annotations

"""
Testing utilities for fault injection (Day14).

Features:
- Redis down simulation
- PostgreSQL slow query simulation
- Celery worker crash simulation

Usage (pytest):
    from backend.tests.utils.fault_injection import (
        simulate_redis_down,
        simulate_postgres_slow_query,
        simulate_celery_worker_crash,
    )

    def test_something(monkeypatch):
        with simulate_redis_down(monkeypatch):
            ...

        with simulate_postgres_slow_query(monkeypatch, delay_seconds=0.3):
            ...

        with simulate_celery_worker_crash(monkeypatch):
            ...
"""

import asyncio
import contextlib
from typing import Any, Callable, Coroutine, Optional


@contextlib.contextmanager
def simulate_redis_down(monkeypatch: Any):
    """Patch CacheManager's Redis client to raise connection errors.

    Targets app.services.cache_manager.redis.Redis.from_url and returns a stub
    whose methods raise redis.exceptions.ConnectionError.
    """
    try:
        import redis  # type: ignore
        RedisError = redis.exceptions.ConnectionError  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - redis always present in env
        class RedisError(Exception):
            pass

    class _DownRedis:
        def get(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
            raise RedisError("Simulated Redis outage")

        def setex(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
            raise RedisError("Simulated Redis outage")

        def exists(self, *args: Any, **kwargs: Any) -> int:  # noqa: D401
            raise RedisError("Simulated Redis outage")

        def delete(self, *args: Any, **kwargs: Any) -> int:  # noqa: D401
            raise RedisError("Simulated Redis outage")

    def _from_url(_url: str) -> Any:
        return _DownRedis()

    m = monkeypatch
    mctx = contextlib.ExitStack()
    mctx.enter_context(m.context())  # type: ignore[attr-defined]
    m.setattr("app.services.cache_manager.redis.Redis.from_url", _from_url, raising=True)
    try:
        yield
    finally:
        mctx.close()


@contextlib.contextmanager
def simulate_postgres_slow_query(
    monkeypatch: Any,
    *,
    delay_seconds: float = 0.2,
    target_method: str = "execute",
):
    """Inject artificial delay into AsyncSession.execute/Scalar methods.

    delay_seconds: Added await asyncio.sleep before original call.
    target_method: One of {"execute", "scalar", "scalars"}.
    """
    from sqlalchemy.ext.asyncio import AsyncSession  # type: ignore

    original = getattr(AsyncSession, target_method)

    async def _slow(self: Any, *args: Any, **kwargs: Any):  # type: ignore[override]
        await asyncio.sleep(max(0.0, delay_seconds))
        return await original(self, *args, **kwargs)

    m = monkeypatch
    mctx = contextlib.ExitStack()
    mctx.enter_context(m.context())  # type: ignore[attr-defined]
    m.setattr(AsyncSession, target_method, _slow, raising=True)
    try:
        yield
    finally:
        mctx.close()


@contextlib.contextmanager
def simulate_celery_worker_crash(monkeypatch: Any, *, on_send: bool = True, on_inspect: bool = True):
    """Simulate Celery worker unavailability.

    on_send: Raise when dispatching tasks via send_task.
    on_inspect: Return an inspector that indicates no active workers.
    """
    from app.core.celery_app import celery_app  # type: ignore

    m = monkeypatch
    mctx = contextlib.ExitStack()
    mctx.enter_context(m.context())  # type: ignore[attr-defined]

    if on_send:
        def _raise_send_task(*_args: Any, **_kwargs: Any):  # noqa: D401
            raise RuntimeError("Simulated Celery send_task failure (worker crash)")

        m.setattr(celery_app, "send_task", _raise_send_task, raising=True)

    if on_inspect:
        class _DeadInspector:
            def active(self) -> Optional[dict[str, Any]]:  # type: ignore[override]
                return None

            def stats(self) -> Optional[dict[str, Any]]:  # type: ignore[override]
                return None

            def ping(self) -> Optional[dict[str, Any]]:  # type: ignore[override]
                return None

        class _Ctl:
            def inspect(self) -> _DeadInspector:  # type: ignore[override]
                return _DeadInspector()

        m.setattr(celery_app, "control", _Ctl(), raising=True)

    try:
        yield
    finally:
        mctx.close()

