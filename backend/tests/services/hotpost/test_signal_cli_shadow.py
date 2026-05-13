from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.services.hotpost import signal_cli_shadow as mod


def test_load_signal_shadow_candidates_filters_non_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "snapshot_id": "queue-test",
        "candidates": [
            {"candidate_id": "cand-signal"},
            {"candidate_id": "cand-hot"},
        ],
    }

    class _FakePack:
        def __init__(self, candidate_id: str) -> None:
            self.candidate_id = candidate_id

    class _FakeCandidatePack:
        @staticmethod
        def model_validate(item: dict[str, Any]) -> _FakePack:
            return _FakePack(item["candidate_id"])

    def _fake_seed(candidate: _FakePack) -> SimpleNamespace:
        lane = "signal" if candidate.candidate_id == "cand-signal" else "hot"
        return SimpleNamespace(lane=lane)

    monkeypatch.setattr(mod, "load_review_queue_snapshot", lambda _snapshot_id=None: payload)
    monkeypatch.setattr(mod, "CandidatePack", _FakeCandidatePack)
    monkeypatch.setattr(mod, "seed_validation_draft", _fake_seed)

    result = mod.load_signal_shadow_candidates(limit=5)

    assert [item.candidate_id for item in result] == ["cand-signal"]


@pytest.mark.asyncio
async def test_generate_signal_shadow_from_candidate_uses_gemini_cli_client(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    candidate = SimpleNamespace(candidate_id="cand-1")
    seeded = SimpleNamespace(
        candidate_id="cand-1",
        lane="signal",
        source_scope_id="ai-automation",
        source_scope_name="AI 与自动化",
        topic_pack_id="upstream-winds",
    )
    generated = SimpleNamespace(
        candidate_id="cand-1",
        lane="signal",
        source_scope_id="ai-automation",
        source_scope_name="AI 与自动化",
        topic_pack_id="upstream-winds",
        title="title",
        summary_line="summary",
        audience="audience",
        why_now="why",
        detail=SimpleNamespace(model_dump=lambda mode="json": {"why_test_now": "证据变硬了"}),
    )

    monkeypatch.setattr(mod, "seed_validation_draft", lambda _candidate: seeded)

    async def _fake_generate(draft: Any, *, allow_breakdown: bool, client_factory: Any) -> Any:
        client = client_factory("google/gemini-3-flash-preview", 12.0)
        assert isinstance(client, mod.GeminiCLIChatClient)
        assert client.model == "gemini-3.1-pro-preview"
        assert client.timeout_seconds == 180.0
        assert client.cwd == tmp_path
        assert draft is seeded
        assert allow_breakdown is False
        return generated

    monkeypatch.setattr(mod, "generate_card_content", _fake_generate)

    row = await mod.generate_signal_shadow_from_candidate(
        candidate,
        client_factory=mod.build_signal_cli_shadow_client_factory(
            model="gemini-3.1-pro-preview",
            cwd=tmp_path,
            min_timeout_seconds=180.0,
        ),
    )

    assert row["candidate_id"] == "cand-1"
    assert row["title"] == "title"
    assert row["detail"]["why_test_now"] == "证据变硬了"


def test_build_signal_api_shadow_client_factory_uses_router(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[tuple[str, float]] = []

    def _fake_build(model: str, *, timeout: float) -> object:
        captured.append((model, timeout))
        return object()

    monkeypatch.setattr(mod, "build_card_content_client", _fake_build)

    factory = mod.build_signal_api_shadow_client_factory()
    factory("deepseek/deepseek-v4-pro", 18.0)

    assert captured == [("deepseek/deepseek-v4-pro", 18.0)]


def test_build_signal_codex_shadow_client_factory_uses_codex_cli(tmp_path) -> None:
    factory = mod.build_signal_codex_shadow_client_factory(
        model="gpt-5.4-mini",
        cwd=tmp_path,
        min_timeout_seconds=180.0,
    )

    client = factory("deepseek/deepseek-v4-pro", 12.0)

    assert isinstance(client, mod.CodexCLIChatClient)
    assert client.model == "gpt-5.4-mini"
    assert client.timeout_seconds == 180.0
    assert client.cwd == tmp_path
