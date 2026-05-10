from __future__ import annotations

import asyncio

from app.scripts_support.env_loader import load_backend_env


def test_materialize_breakdown_drafts_run_honors_scope_and_limit(monkeypatch) -> None:
    load_backend_env()
    import scripts.hotpost.materialize_breakdown_drafts as mod

    calls: list[tuple[str | None, int]] = []

    async def _fake_materialize(*, source_scope_id=None, limit=20):
        calls.append((source_scope_id, limit))
        return []

    monkeypatch.setattr(mod, "materialize_breakdown_drafts", _fake_materialize)

    args = type("Args", (), {"scope": "business-growth-ops", "limit": 3})()
    payload = asyncio.run(mod._run(args))

    assert calls == [("business-growth-ops", 3)]
    assert payload["count"] == 0
    assert payload["materialized"] == 0
