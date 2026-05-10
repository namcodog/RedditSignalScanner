from __future__ import annotations

import asyncio

from app.scripts_support.env_loader import load_backend_env


def test_daily_collect_defaults_to_all_scope(monkeypatch) -> None:
    load_backend_env()
    import scripts.hotpost.daily_collect as mod

    captured: dict[str, object] = {}

    async def _fake_run(*, scope, mode, max_candidates, dry_cycle_limit):
        captured.update(
            {
                "scope": scope,
                "mode": mode,
                "max_candidates": max_candidates,
                "dry_cycle_limit": dry_cycle_limit,
            }
        )
        return {"scope": scope}

    monkeypatch.setattr(mod, "run_quota_aware_collect", _fake_run)
    monkeypatch.setattr(
        mod.argparse.ArgumentParser,
        "parse_args",
        lambda self: type(
            "Args",
            (),
            {
                "scope": None,
                "all_scope": False,
                "mode": "safe",
                "max_candidates": 12,
                "dry_cycle": 3,
            },
        )(),
    )

    asyncio.run(mod.main())

    assert captured["scope"] is None


def test_daily_collect_scope_flag_still_allows_local_repair(monkeypatch) -> None:
    load_backend_env()
    import scripts.hotpost.daily_collect as mod

    captured: dict[str, object] = {}

    async def _fake_run(*, scope, mode, max_candidates, dry_cycle_limit):
        captured["scope"] = scope
        return {"scope": scope}

    monkeypatch.setattr(mod, "run_quota_aware_collect", _fake_run)
    monkeypatch.setattr(
        mod.argparse.ArgumentParser,
        "parse_args",
        lambda self: type(
            "Args",
            (),
            {
                "scope": "business-growth-ops",
                "all_scope": False,
                "mode": "safe",
                "max_candidates": 12,
                "dry_cycle": 3,
            },
        )(),
    )

    asyncio.run(mod.main())

    assert captured["scope"] == "business-growth-ops"
