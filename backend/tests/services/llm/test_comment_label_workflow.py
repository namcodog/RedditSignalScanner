from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.services.llm.comment_label_planner import (
    build_incremental_comment_label_plan_from_rows,
)
from app.services.llm.comment_label_workflow import (
    IncrementalCommentLabelWorkflowDeps,
    IncrementalCommentLabelWorkflowInput,
    run_incremental_comment_label_workflow,
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
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def begin_nested(self) -> _NestedSession:
        return _NestedSession()

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


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        gemini_api_key="test-key",
        llm_label_body_chars=200,
        llm_label_comment_chars=80,
        llm_label_model_name="gemini-test",
        llm_label_prompt_version="v-test",
    )


def _comment_row(
    *,
    comment_id: int = 201,
    body: str = "This product is amazing and solved my problem completely",
    value_score: float = 9.5,
    business_pool: str = "core",
) -> dict[str, Any]:
    return {
        "id": comment_id,
        "body": body,
        "subreddit": "ecommerce",
        "score": 10,
        "source": "reddit",
        "source_post_id": "abc999",
        "post_title": "Best product",
        "value_score": value_score,
        "business_pool": business_pool,
    }


def _workflow_input(
    *,
    rows: list[dict[str, Any]],
    online_budget_cap: int = 10,
) -> IncrementalCommentLabelWorkflowInput:
    return IncrementalCommentLabelWorkflowInput(
        settings=_settings(),
        plan=build_incremental_comment_label_plan_from_rows(rows),
        online_budget_cap=online_budget_cap,
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
async def test_incremental_comment_label_workflow_returns_no_candidates_after_rules() -> None:
    fake_session = _FakeSession()

    class _NoopLabeler:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.model_name = "gemini-test"
            self.prompt_version = "v-test"

        async def label_comments_batch(self, *, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return []

        async def label_comment(self, **_kwargs: Any) -> tuple[dict[str, Any], _FakeScore, int, int]:
            return ({}, _FakeScore(), 0, 0)

    async def _persist_comment_analysis(**_kwargs: Any) -> None:
        return None

    result = await run_incremental_comment_label_workflow(
        workflow_input=_workflow_input(rows=[_comment_row(body="ok!!")]),
        deps=IncrementalCommentLabelWorkflowDeps(
            session_factory=lambda: _FakeSessionContext(fake_session),
            labeler_factory=_NoopLabeler,
            persist_comment_analysis=_persist_comment_analysis,
        ),
    )

    assert result["status"] == "no_candidates"
    assert result["processed"] == 0
    assert result["rule_filtered"] == 1
    assert result["task_scope"] == "incremental_only"


@pytest.mark.asyncio
async def test_incremental_comment_label_workflow_marks_budget_cap_degraded() -> None:
    fake_session = _FakeSession()

    class _NoopLabeler:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.model_name = "gemini-test"
            self.prompt_version = "v-test"

        async def label_comments_batch(self, *, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return []

        async def label_comment(self, **_kwargs: Any) -> tuple[dict[str, Any], _FakeScore, int, int]:
            return ({"sentiment": 0.1}, _FakeScore(), 50, 20)

    async def _persist_comment_analysis(**_kwargs: Any) -> None:
        return None

    rows = [
        _comment_row(
            comment_id=300 + i,
            body=f"Unique high-value comment number {i} with enough text to pass the length filter here",
            value_score=9.5,
        )
        for i in range(16)
    ]

    result = await run_incremental_comment_label_workflow(
        workflow_input=_workflow_input(rows=rows, online_budget_cap=6),
        deps=IncrementalCommentLabelWorkflowDeps(
            session_factory=lambda: _FakeSessionContext(fake_session),
            labeler_factory=_NoopLabeler,
            persist_comment_analysis=_persist_comment_analysis,
        ),
    )

    assert result["status"] == "degraded"
    assert result["attempted"] <= 6
    assert "budget_capped" in result["degraded_reasons"]
    assert result["task_scope"] == "incremental_only"
    assert fake_session.commits >= 1
