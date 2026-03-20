from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.crawl import crawler_task_support as mod


def test_env_helpers_respect_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLAG_A", "yes")
    monkeypatch.setenv("INT_A", "12")

    assert mod.env_truthy("FLAG_A") is True
    assert mod.env_truthy("MISSING_FLAG", "0") is False
    assert mod.env_int("INT_A", 3) == 12
    assert mod.env_int("INT_BAD", 7) == 7


def test_tier_settings_for_delegates_to_config() -> None:
    profile = SimpleNamespace(tier="t2")

    class _Config:
        def resolve_tier(self, tier: str) -> str:
            return f"tier:{tier}"

    assert mod.tier_settings_for(profile, crawler_config=_Config()) == "tier:t2"
    assert mod.tier_settings_for(None, crawler_config=_Config()) is None


@pytest.mark.asyncio
async def test_commit_with_warning_rolls_back_on_failure() -> None:
    events: list[str] = []

    class _Session:
        async def commit(self) -> None:
            raise RuntimeError("boom")

        async def rollback(self) -> None:
            events.append("rollback")

    async def _rollback(session):  # type: ignore[no-untyped-def]
        await mod.rollback_with_warning(
            session,
            context="ctx",
            log_swallowed_exception_func=lambda *_args, **_kwargs: None,
        )

    ok = await mod.commit_with_warning(
        _Session(),
        context="ctx",
        rollback_with_warning_func=_rollback,
        log_swallowed_exception_func=lambda *_args, **_kwargs: None,
    )

    assert ok is False
    assert events == ["rollback"]


@pytest.mark.asyncio
async def test_maybe_trigger_probe_hot_fallback_dispatches_when_due_below_min() -> None:
    calls: list[dict[str, object]] = []

    class _Session:
        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aexit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
            return False

    async def _table_exists(_session):  # type: ignore[no-untyped-def]
        return True

    async def _last_started(_session):  # type: ignore[no-untyped-def]
        return datetime.now(timezone.utc) - timedelta(hours=24)

    def _send_task(name: str, **kwargs):  # type: ignore[no-untyped-def]
        calls.append({"name": name, **kwargs})

    triggered = await mod.maybe_trigger_probe_hot_fallback(
        due_count=1,
        total_pool_count=10,
        session_factory=lambda: _Session(),
        crawler_run_targets_table_exists_func=_table_exists,
        load_last_probe_hot_started_at_func=_last_started,
        env_truthy_func=lambda *_args, **_kwargs: True,
        env_int_func=lambda name, default: {"PROBE_HOT_FALLBACK_MIN_DUE": 3}.get(
            name, default
        ),
        send_task=_send_task,
        module_logger=SimpleNamespace(
            info=lambda *args, **kwargs: None,
            exception=lambda *args, **kwargs: None,
        ),
    )

    assert triggered is True
    assert calls[0]["name"] == "tasks.probe.run_hot_probe"
