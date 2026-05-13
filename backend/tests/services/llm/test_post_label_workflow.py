from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.services.llm.interfaces import LLMClientError
from app.services.llm.post_label_workflow import (
    IncrementalPostLabelWorkflowDeps,
    IncrementalPostLabelWorkflowInput,
    run_incremental_post_label_workflow,
)


class _FakeScore:
    def __init__(
        self,
        *,
        value_score: float = 8.0,
        opportunity_score: float = 6.0,
        business_pool: str = "core",
    ) -> None:
        self.value_score = value_score
        self.opportunity_score = opportunity_score
        self.business_pool = business_pool


class _NestedSession:
    async def __aenter__(self) -> "_NestedSession":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False


class _FakeSession:
    def begin_nested(self) -> _NestedSession:
        return _NestedSession()

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class _FakeSessionContext:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session

    async def __aenter__(self) -> _FakeSession:
        return self._session

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        gemini_api_key="test-key",
        llm_label_body_chars=200,
        llm_label_comment_chars=80,
        llm_label_model_name="gemini-test",
        llm_label_prompt_version="v-test",
    )


def _candidate_row() -> dict[str, Any]:
    return {
        "id": 101,
        "title": "Need a better payment tool",
        "body": "fees are too high",
        "subreddit": "ecommerce",
        "value_score": 9.5,
        "business_pool": "core",
        "source": "reddit",
        "source_post_id": "abc123",
        "text_norm_hash": "hash-101",
    }


def _workflow_input() -> IncrementalPostLabelWorkflowInput:
    return IncrementalPostLabelWorkflowInput(
        settings=_settings(),
        limit=10,
        lookback_days=30,
        llm_batch_size=2,
        low_score_max=0.0,
        high_score_ratio=0.3,
        mid_score_min=5.0,
        mid_score_max=7.0,
        lab_long_sample_rate=0.15,
        lab_body_ratio=0.6,
        lab_comment_ratio=0.6,
    )


@pytest.mark.asyncio
async def test_run_incremental_post_label_workflow_marks_degraded_when_batch_falls_back() -> None:
    session = _FakeSession()

    class _FakeLabeler:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.model_name = str(kwargs.get("model") or "gemini-test")
            self.prompt_version = str(kwargs.get("prompt_version") or "v-test")

        async def label_posts_batch(self, *, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return []

        async def label_post(self, **_kwargs: Any) -> tuple[dict[str, Any], _FakeScore, int, int]:
            return (
                {"sentiment": 0.1, "entities": {"known": ["shopify"], "new": []}},
                _FakeScore(),
                120,
                60,
            )

    async def _fetch_post_candidates(**_kwargs: Any) -> list[dict[str, Any]]:
        return [_candidate_row()]

    async def _fetch_top_comments(*_args: Any, **_kwargs: Any) -> list[str]:
        return []

    async def _persist_post_analysis(**_kwargs: Any) -> None:
        return None

    result = await run_incremental_post_label_workflow(
        workflow_input=_workflow_input(),
        deps=IncrementalPostLabelWorkflowDeps(
            session_factory=lambda: _FakeSessionContext(session),
            labeler_factory=_FakeLabeler,
            fetch_post_candidates=_fetch_post_candidates,
            fetch_top_comments=_fetch_top_comments,
            persist_post_analysis=_persist_post_analysis,
        ),
    )

    assert result["status"] == "degraded"
    assert result["processed"] == 1
    assert result["fallback_batches"] == 1
    assert "batch_empty_fallback" in result["degraded_reasons"]


@pytest.mark.asyncio
async def test_run_incremental_post_label_workflow_marks_failed_when_llm_requests_keep_failing() -> None:
    session = _FakeSession()

    class _FailingLabeler:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.model_name = str(kwargs.get("model") or "gemini-test")
            self.prompt_version = str(kwargs.get("prompt_version") or "v-test")

        async def label_posts_batch(self, *, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            raise LLMClientError("gemini", "batch down")

        async def label_post(self, **_kwargs: Any) -> tuple[dict[str, Any], _FakeScore, int, int]:
            raise LLMClientError("gemini", "single down")

    async def _fetch_post_candidates(**_kwargs: Any) -> list[dict[str, Any]]:
        return [_candidate_row()]

    async def _fetch_top_comments(*_args: Any, **_kwargs: Any) -> list[str]:
        return []

    async def _persist_post_analysis(**_kwargs: Any) -> None:
        return None

    result = await run_incremental_post_label_workflow(
        workflow_input=_workflow_input(),
        deps=IncrementalPostLabelWorkflowDeps(
            session_factory=lambda: _FakeSessionContext(session),
            labeler_factory=_FailingLabeler,
            fetch_post_candidates=_fetch_post_candidates,
            fetch_top_comments=_fetch_top_comments,
            persist_post_analysis=_persist_post_analysis,
        ),
    )

    assert result["status"] == "failed"
    assert result["processed"] == 0
    assert result["llm_failures"] == 2
    assert result["fallback_batches"] == 1
    assert "batch_llm_request_failed" in result["degraded_reasons"]
    assert "single_llm_request_failed" in result["degraded_reasons"]
