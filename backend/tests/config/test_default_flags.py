from __future__ import annotations

import importlib
from typing import Any

import pytest

from app.services.crawl.plan_contract import CrawlPlanContract, CrawlPlanLimits


def test_probe_hot_beat_default_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROBE_HOT_BEAT_ENABLED", raising=False)

    from app.core import celery_app as celery_module

    celery_module = importlib.reload(celery_module)

    assert "probe-hot-12h" in celery_module.celery_app.conf.beat_schedule


@pytest.mark.asyncio
async def test_probe_hot_fallback_default_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.tasks import crawler_task

    monkeypatch.delenv("PROBE_HOT_FALLBACK_ENABLED", raising=False)
    monkeypatch.setenv("PROBE_HOT_FALLBACK_MIN_DUE", "3")
    monkeypatch.setenv("PROBE_HOT_FALLBACK_COOLDOWN_MINUTES", "0")
    monkeypatch.setenv("PROBE_HOT_FALLBACK_POSTS_PER_SOURCE", "5")

    sent: list[dict[str, Any]] = []

    def fake_send_task(task_name: str, *_: Any, **kwargs: Any) -> None:
        sent.append({"task_name": task_name, "kwargs": kwargs})

    async def fake_table_exists(_: Any) -> bool:
        return True

    async def fake_last_started(_: Any) -> None:
        return None

    class DummySession:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *_: Any) -> bool:
            return False

    monkeypatch.setattr(crawler_task.celery_app, "send_task", fake_send_task)
    monkeypatch.setattr(crawler_task, "_crawler_run_targets_table_exists", fake_table_exists)
    monkeypatch.setattr(crawler_task, "_load_last_probe_hot_started_at", fake_last_started)
    monkeypatch.setattr(crawler_task, "SessionFactory", lambda: DummySession())

    triggered = await crawler_task._maybe_trigger_probe_hot_fallback(
        due_count=0,
        total_pool_count=10,
    )

    assert triggered is True
    assert any(call["task_name"] == "tasks.probe.run_hot_probe" for call in sent)


def test_probe_auto_evaluate_default_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROBE_AUTO_EVALUATE_ENABLED", raising=False)

    from app.tasks.crawl_execute_task import _should_auto_trigger_evaluator

    plan = CrawlPlanContract(
        plan_kind="probe",
        target_type="subreddit",
        target_value="r/test_probe",
        reason="default_flag_check",
        limits=CrawlPlanLimits(posts_limit=10),
        meta={"source": "hot"},
    )

    outcome = {"discovered_communities_upserted": 1}

    assert _should_auto_trigger_evaluator(plan=plan, outcome=outcome) is True


@pytest.mark.asyncio
async def test_cron_discovery_default_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CRON_DISCOVERY_ENABLED", raising=False)

    from app.tasks import discovery_task

    async def fake_discovery() -> list[str]:
        return ["r/test_discovery"]

    async def fake_evaluation() -> list[dict[str, str]]:
        return [{"status": "approved"}]

    monkeypatch.setattr(discovery_task, "_run_semantic_discovery", fake_discovery)
    monkeypatch.setattr(discovery_task, "_run_community_evaluation", fake_evaluation)

    result = await discovery_task._run_weekly_discovery()

    assert result["status"] == "completed"
    assert result["discovered"] == 1
    assert result["approved"] == 1


@pytest.mark.asyncio
async def test_community_pool_from_db_default_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COMMUNITY_POOL_FROM_DB", raising=False)

    from app.services.analysis import community_discovery

    called = {"loader": False}

    class DummySession:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *_: Any) -> bool:
            return False

    class DummyLoader:
        def __init__(self, _: Any) -> None:
            called["loader"] = True

        async def load_community_pool(self) -> list[str]:
            return ["r/db_default"]

    monkeypatch.setattr("app.db.session.SessionFactory", lambda: DummySession())
    monkeypatch.setattr("app.services.community.community_pool_loader.CommunityPoolLoader", DummyLoader)

    result = await community_discovery._load_community_pool()

    assert result == ["r/db_default"]
    assert called["loader"] is True


def test_incremental_comments_backfill_default_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("INCREMENTAL_COMMENTS_BACKFILL_ENABLED", raising=False)

    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.incremental_comments_backfill_enabled is True
    get_settings.cache_clear()


def test_incremental_comments_preview_defaults_to_enable_comments_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("INCREMENTAL_COMMENTS_PREVIEW_ENABLED", raising=False)
    monkeypatch.setenv("ENABLE_COMMENTS_SYNC", "false")

    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.incremental_comments_preview_enabled is False
    get_settings.cache_clear()


def test_incremental_comments_preview_override_takes_priority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENABLE_COMMENTS_SYNC", "false")
    monkeypatch.setenv("INCREMENTAL_COMMENTS_PREVIEW_ENABLED", "true")

    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.incremental_comments_preview_enabled is True
    get_settings.cache_clear()


def test_incremental_comments_backfill_not_tied_to_preview_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENABLE_COMMENTS_SYNC", "false")
    monkeypatch.setenv("INCREMENTAL_COMMENTS_BACKFILL_ENABLED", "true")

    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.incremental_comments_backfill_enabled is True
    get_settings.cache_clear()


def test_incremental_duplicate_mode_default_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("INCREMENTAL_DUPLICATE_MODE", raising=False)

    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    assert settings.incremental_duplicate_mode == "tag"
    get_settings.cache_clear()
