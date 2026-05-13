from __future__ import annotations

import json

import pytest


class _FakeCollectClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get_collect_stats(self) -> dict[str, int]:
        return {}


@pytest.mark.asyncio
async def test_scope_collect_defaults_to_experimental_off(monkeypatch) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    flags: list[bool] = []

    def _fake_specs(scope_id: str, *, include_experimental: bool = False) -> list[object]:
        flags.append(include_experimental)
        return []

    monkeypatch.setattr(collector, "build_reddit_search_specs", _fake_specs)
    monkeypatch.setattr(collector, "build_collect_reddit_client", lambda **kwargs: _FakeCollectClient())
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)

    summary = await collector.collect_scope_candidates_with_summary("ai-automation", max_candidates=1)

    assert flags == [False]
    assert summary["experimental_probe_enabled"] is False
    assert summary["persisted_to_formal_candidates"] is True


@pytest.mark.asyncio
async def test_scope_collect_can_explicitly_enable_experimental(monkeypatch) -> None:
    from app.services.hotpost import source_scope_candidate_collector as collector

    flags: list[bool] = []

    def _fake_specs(scope_id: str, *, include_experimental: bool = False) -> list[object]:
        flags.append(include_experimental)
        return []

    monkeypatch.setattr(collector, "build_reddit_search_specs", _fake_specs)
    monkeypatch.setattr(collector, "build_collect_reddit_client", lambda **kwargs: _FakeCollectClient())
    monkeypatch.setattr(collector, "replace_scope_candidates", lambda scope_id, items: items)

    summary = await collector.collect_scope_candidates_with_summary(
        "ai-automation",
        max_candidates=1,
        include_experimental=True,
    )

    assert flags == [True]
    assert summary["experimental_probe_enabled"] is True


@pytest.mark.asyncio
async def test_probe_entry_always_uses_explicit_experimental_flag(monkeypatch) -> None:
    from app.services.hotpost import community_probe_collect as probe

    captured: dict[str, object] = {}
    writes: list[tuple[str, list[object]]] = []

    async def _fake_collect(scope_id: str, **kwargs):
        captured.update(kwargs)
        return {"scope_id": scope_id, "items": ["candidate-a"]}

    monkeypatch.setattr(probe, "collect_scope_candidates_with_summary", _fake_collect)
    monkeypatch.setattr(
        probe,
        "replace_experimental_scope_candidates",
        lambda scope_id, items: writes.append((scope_id, list(items))) or {"path": "experimental.json", "candidate_count": len(items)},
    )

    summary = await probe.collect_experimental_scope_probe("ai-automation", max_candidates=2)

    assert summary["scope_id"] == "ai-automation"
    assert captured["include_experimental"] is True
    assert captured["experimental_only"] is True
    assert captured["persist"] is False
    assert captured["max_candidates"] == 2
    assert writes == [("ai-automation", ["candidate-a"])]
    assert summary["experimental_candidate_store"] == {"path": "experimental.json", "candidate_count": 1}


def test_probe_script_summary_is_json_serializable() -> None:
    from scripts.hotpost.probe_community_discovery import _jsonable_summary

    class _Candidate:
        def model_dump(self, *, mode: str) -> dict[str, object]:
            return {
                "candidate_id": "cand-1",
                "source_scope_id": "ai-automation",
                "topic_pack_id": "tools-efficiency",
                "topic_cluster_id": "workflow-friction",
                "matched_subreddit": "CursorAI",
                "title": "Cursor workflow issue",
            }

    payload = _jsonable_summary(
        {
            "scope_id": "ai-automation",
            "items": [_Candidate()],
            "experimental_candidate_store": {
                "path": "backend/data/hotpost/experimental_candidates/ai-automation.json",
                "candidate_count": 1,
            },
        }
    )

    json.dumps(payload, ensure_ascii=False)
    assert payload["item_count"] == 1
    assert payload["experimental_candidate_path"] == "backend/data/hotpost/experimental_candidates/ai-automation.json"
    assert payload["experimental_candidate_count"] == 1
    assert payload["items"] == [
        {
            "candidate_id": "cand-1",
            "source_scope_id": "ai-automation",
            "topic_pack_id": "tools-efficiency",
            "topic_cluster_id": "workflow-friction",
            "matched_subreddit": "CursorAI",
            "title": "Cursor workflow issue",
        }
    ]
