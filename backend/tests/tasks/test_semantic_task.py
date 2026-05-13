from __future__ import annotations

import pytest

from app.tasks import semantic_task


def test_extract_semantic_candidates_weekly_adds_contract_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run(coro):
        coro.close()
        return {
            "total_candidates": 2,
            "top_terms": ["shipping"],
            "extraction_source": "posts_fallback",
            "extraction_status": "posts_fallback",
            "status": "degraded",
            "degraded_reasons": ["posts_fallback"],
        }

    monkeypatch.setattr(semantic_task.asyncio, "run", _fake_run)

    result = semantic_task.extract_semantic_candidates_weekly()

    assert result["status"] == "degraded"
    assert result["task_scope"] == "semantic_candidate_extract"
    assert result["extraction_source"] == "posts_fallback"
    assert result["degraded_reasons"] == ["posts_fallback"]


def test_extract_semantic_candidates_weekly_returns_failed_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(coro):
        coro.close()
        raise RuntimeError("extract failed")

    monkeypatch.setattr(semantic_task.asyncio, "run", _boom)

    result = semantic_task.extract_semantic_candidates_weekly()

    assert result["status"] == "failed"
    assert result["task_scope"] == "semantic_candidate_extract"
    assert result["error"] == "extraction_failed"
    assert result["degraded_reasons"] == []


def test_sync_llm_candidates_adds_contract_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run(coro):
        coro.close()
        return {
            "candidates": 0,
            "auto_approved": 0,
            "pending": 0,
            "candidate_source": "llm_labels",
            "sync_status": "no_candidates",
        }

    monkeypatch.setattr(semantic_task.asyncio, "run", _fake_run)

    result = semantic_task.sync_llm_candidates()

    assert result["status"] == "completed"
    assert result["task_scope"] == "semantic_candidate_sync"
    assert result["candidate_source"] == "llm_labels"
    assert result["sync_status"] == "no_candidates"
    assert result["degraded_reasons"] == []


def test_sync_llm_candidates_returns_failed_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(coro):
        coro.close()
        raise RuntimeError("sync failed")

    monkeypatch.setattr(semantic_task.asyncio, "run", _boom)

    result = semantic_task.sync_llm_candidates()

    assert result["status"] == "failed"
    assert result["task_scope"] == "semantic_candidate_sync"
    assert result["candidate_source"] == "llm_labels"
    assert result["sync_status"] == "failed"
    assert result["error"] == "sync_failed"
    assert result["degraded_reasons"] == []
