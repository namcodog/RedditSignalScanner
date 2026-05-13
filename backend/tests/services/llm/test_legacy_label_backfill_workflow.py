from __future__ import annotations

from typing import Any

import pytest

from app.services.llm.legacy_label_backfill_workflow import (
    LegacyLabelBackfillWorkflowDeps,
    LegacyLabelBackfillWorkflowInput,
    run_legacy_label_backfill_workflow,
)


class _FakeMappingsResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> "_FakeMappingsResult":
        return self

    def all(self) -> list[dict[str, Any]]:
        return list(self._rows)


class _FakeSession:
    def __init__(
        self,
        *,
        post_rows: list[dict[str, Any]],
        comment_rows: list[dict[str, Any]],
    ) -> None:
        self._post_rows = post_rows
        self._comment_rows = comment_rows
        self._execute_calls = 0
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, *_args: Any, **_kwargs: Any) -> _FakeMappingsResult:
        self._execute_calls += 1
        if self._execute_calls == 1:
            return _FakeMappingsResult(self._post_rows)
        return _FakeMappingsResult(self._comment_rows)

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False


def _post_row(post_id: int = 11) -> dict[str, Any]:
    return {
        "post_id": post_id,
        "llm_version": "legacy-model",
        "tags_analysis": {"pain_tags": ["fees"]},
        "entities_extracted": {"known": ["shopify"], "new": []},
        "value_score": 8.5,
        "opportunity_score": 6.2,
        "business_pool": "core",
        "sentiment": -0.3,
        "purchase_intent_score": 0.4,
        "text_norm_hash": "hash-post",
    }


def _comment_row(comment_id: int = 21) -> dict[str, Any]:
    return {
        "comment_id": comment_id,
        "llm_version": "legacy-model",
        "tags_analysis": {"aspect_tags": ["pricing"]},
        "entities_extracted": {"known": ["stripe"], "new": []},
        "value_score": 7.5,
        "opportunity_score": 5.4,
        "business_pool": "lab",
        "sentiment": 0.1,
        "purchase_intent_score": 0.2,
    }


@pytest.mark.asyncio
async def test_legacy_label_backfill_workflow_completed() -> None:
    fake_session = _FakeSession(post_rows=[_post_row()], comment_rows=[_comment_row()])
    post_calls: list[dict[str, Any]] = []
    comment_calls: list[dict[str, Any]] = []
    sync_calls: list[dict[str, Any]] = []

    async def _upsert_post_label(**kwargs: Any) -> None:
        post_calls.append(kwargs)

    async def _upsert_comment_label(**kwargs: Any) -> None:
        comment_calls.append(kwargs)

    async def _sync_llm_terms(_session: Any, **kwargs: Any) -> dict[str, int]:
        sync_calls.append(kwargs)
        return {"pain_point": 1, "feature": 0, "brand": 1}

    result = await run_legacy_label_backfill_workflow(
        workflow_input=LegacyLabelBackfillWorkflowInput(limit=50),
        deps=LegacyLabelBackfillWorkflowDeps(
            session_factory=lambda: _FakeSessionContext(fake_session),
            upsert_post_label=_upsert_post_label,
            upsert_comment_label=_upsert_comment_label,
            sync_llm_terms=_sync_llm_terms,
            json_sanitize=lambda value: value,
        ),
    )

    assert result["status"] == "completed"
    assert result["processed"] == 2
    assert result["post_processed"] == 1
    assert result["comment_processed"] == 1
    assert result["persist_failures"] == 0
    assert result["sync_failures"] == 0
    assert len(post_calls) == 1
    assert len(comment_calls) == 1
    assert len(sync_calls) == 2
    assert fake_session.commits >= 2


@pytest.mark.asyncio
async def test_legacy_label_backfill_workflow_marks_degraded_when_sync_fails() -> None:
    fake_session = _FakeSession(post_rows=[_post_row()], comment_rows=[])

    async def _upsert_post_label(**_kwargs: Any) -> None:
        return None

    async def _upsert_comment_label(**_kwargs: Any) -> None:
        return None

    async def _sync_llm_terms(_session: Any, **_kwargs: Any) -> dict[str, int]:
        raise RuntimeError("sync down")

    result = await run_legacy_label_backfill_workflow(
        workflow_input=LegacyLabelBackfillWorkflowInput(limit=10),
        deps=LegacyLabelBackfillWorkflowDeps(
            session_factory=lambda: _FakeSessionContext(fake_session),
            upsert_post_label=_upsert_post_label,
            upsert_comment_label=_upsert_comment_label,
            sync_llm_terms=_sync_llm_terms,
            json_sanitize=lambda value: value,
        ),
    )

    assert result["status"] == "degraded"
    assert result["processed"] == 1
    assert result["post_processed"] == 1
    assert result["comment_processed"] == 0
    assert result["persist_failures"] == 0
    assert result["sync_failures"] == 1
