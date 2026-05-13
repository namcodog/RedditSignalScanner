from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.services.llm.comment_label_planner import (
    build_incremental_comment_label_plan_from_rows,
)
from app.services.llm.interfaces import LLMClientError
from app.tasks import llm_label_task as task_mod


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
        llm_label_post_limit=10,
        llm_label_comment_limit=10,
        llm_label_lookback_days=30,
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


@pytest.mark.asyncio
async def test_label_posts_batch_marks_degraded_when_batch_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = _FakeSession()

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

    monkeypatch.setattr(task_mod, "get_settings", _settings)
    monkeypatch.setattr(task_mod, "LLMLabeler", _FakeLabeler)

    async def _fake_fetch_post_candidates(**_kwargs: Any) -> list[dict[str, Any]]:
        return [_candidate_row()]

    async def _fake_fetch_top_comments(*_args: Any, **_kwargs: Any) -> list[str]:
        return []

    monkeypatch.setattr(task_mod, "_fetch_post_candidates", _fake_fetch_post_candidates)
    monkeypatch.setattr(task_mod, "_fetch_top_comments", _fake_fetch_top_comments)
    monkeypatch.setattr(
        task_mod,
        "SessionFactory",
        lambda: _FakeSessionContext(fake_session),
    )

    async def _noop(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(task_mod, "persist_incremental_post_analysis", _noop)

    result = await task_mod._label_posts_batch(limit=10, lookback_days=30)

    assert result["status"] == "degraded"
    assert result["processed"] == 1
    assert result["fallback_batches"] == 1
    assert "batch_empty_fallback" in result["degraded_reasons"]
    assert fake_session.commits >= 1


@pytest.mark.asyncio
async def test_label_posts_batch_marks_failed_when_llm_requests_keep_failing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_session = _FakeSession()

    class _FailingLabeler:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.model_name = str(kwargs.get("model") or "gemini-test")
            self.prompt_version = str(kwargs.get("prompt_version") or "v-test")

        async def label_posts_batch(self, *, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            raise LLMClientError("gemini", "batch down")

        async def label_post(self, **_kwargs: Any) -> tuple[dict[str, Any], _FakeScore, int, int]:
            raise LLMClientError("gemini", "single down")

    monkeypatch.setattr(task_mod, "get_settings", _settings)
    monkeypatch.setattr(task_mod, "LLMLabeler", _FailingLabeler)

    async def _fake_fetch_post_candidates(**_kwargs: Any) -> list[dict[str, Any]]:
        return [_candidate_row()]

    async def _fake_fetch_top_comments(*_args: Any, **_kwargs: Any) -> list[str]:
        return []

    monkeypatch.setattr(task_mod, "_fetch_post_candidates", _fake_fetch_post_candidates)
    monkeypatch.setattr(task_mod, "_fetch_top_comments", _fake_fetch_top_comments)
    monkeypatch.setattr(
        task_mod,
        "SessionFactory",
        lambda: _FakeSessionContext(fake_session),
    )

    async def _noop(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(task_mod, "persist_incremental_post_analysis", _noop)

    result = await task_mod._label_posts_batch(limit=10, lookback_days=30)

    assert result["status"] == "failed"
    assert result["processed"] == 0
    assert result["llm_failures"] == 2
    assert result["fallback_batches"] == 1
    assert "batch_llm_request_failed" in result["degraded_reasons"]
    assert "single_llm_request_failed" in result["degraded_reasons"]


# ── Phase A: 评论规则层专项测试 ──────────────────────────────────────────

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


def _comment_noop_patches(monkeypatch: pytest.MonkeyPatch, fake_session: _FakeSession) -> None:
    """Apply common monkeypatches for _label_comments_batch tests."""
    monkeypatch.setattr(task_mod, "get_settings", _settings)

    class _NoopLabeler:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.model_name = "gemini-test"
            self.prompt_version = "v-test"

        async def label_comments_batch(self, *, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return []

        async def label_comment(self, **_kwargs: Any) -> tuple[dict[str, Any], _FakeScore, int, int]:
            return ({"sentiment": 0.1, "entities": {}}, _FakeScore(), 50, 20)

    monkeypatch.setattr(task_mod, "LLMLabeler", _NoopLabeler)
    monkeypatch.setattr(task_mod, "SessionFactory", lambda: _FakeSessionContext(fake_session))

    async def _noop(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(task_mod, "persist_incremental_comment_analysis", _noop)


@pytest.mark.asyncio
async def test_label_comments_batch_short_body_is_rule_filtered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """短评论（body 长度 < _MIN_COMMENT_CHARS=20）应被规则层过滤，不进 LLM。"""
    fake_session = _FakeSession()
    _comment_noop_patches(monkeypatch, fake_session)

    short_row = _comment_row(body="ok!!", value_score=9.5)

    async def _fake_plan(limit: int, lookback_days: int) -> Any:
        return build_incremental_comment_label_plan_from_rows([short_row])

    monkeypatch.setattr(task_mod, "build_incremental_comment_label_plan", _fake_plan)

    result = await task_mod._label_comments_batch(limit=10, lookback_days=30)

    assert result["status"] == "no_candidates"
    assert result["processed"] == 0
    assert result["task_scope"] == "incremental_only"


@pytest.mark.asyncio
async def test_label_comments_batch_duplicate_body_is_deduped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """body 完全相同的两条评论，第二条应被 hash 去重，只有一条进 LLM。"""
    fake_session = _FakeSession()
    _comment_noop_patches(monkeypatch, fake_session)

    body = "This product is amazing and solved my problem completely"
    row1 = _comment_row(comment_id=201, body=body)
    row2 = _comment_row(comment_id=202, body=body)

    async def _fake_plan(limit: int, lookback_days: int) -> Any:
        return build_incremental_comment_label_plan_from_rows([row1, row2])

    monkeypatch.setattr(task_mod, "build_incremental_comment_label_plan", _fake_plan)

    result = await task_mod._label_comments_batch(limit=10, lookback_days=30)

    assert result["attempted"] == 1
    assert result["task_scope"] == "incremental_only"


@pytest.mark.asyncio
async def test_label_comments_batch_budget_cap_triggers_degraded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """候选评论数超过 _ONLINE_COMMENT_BUDGET_CAP 时，应截断并返回 degraded。"""
    fake_session = _FakeSession()
    _comment_noop_patches(monkeypatch, fake_session)

    cap = task_mod._ONLINE_COMMENT_BUDGET_CAP
    rows = [
        _comment_row(
            comment_id=300 + i,
            body=f"Unique high-value comment number {i} with enough text to pass the length filter here",
            value_score=9.5,
        )
        for i in range(cap + 10)
    ]

    async def _fake_plan(limit: int, lookback_days: int) -> Any:
        return build_incremental_comment_label_plan_from_rows(rows)

    monkeypatch.setattr(task_mod, "build_incremental_comment_label_plan", _fake_plan)

    result = await task_mod._label_comments_batch(limit=cap + 10, lookback_days=30)

    assert result["status"] == "degraded"
    assert result["attempted"] <= cap
    assert "budget_capped" in result["degraded_reasons"]
    assert result["task_scope"] == "incremental_only"


@pytest.mark.asyncio
async def test_label_comments_batch_delegates_to_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_plan(limit: int, lookback_days: int) -> Any:
        return build_incremental_comment_label_plan_from_rows([_comment_row()])

    captured: dict[str, Any] = {}

    async def _fake_workflow(*, workflow_input: Any, deps: Any) -> dict[str, Any]:
        captured["plan_candidates"] = len(workflow_input.plan.candidates)
        captured["online_budget_cap"] = workflow_input.online_budget_cap
        captured["deps"] = deps
        return {"processed": 3, "status": "completed", "task_scope": "incremental_only"}

    monkeypatch.setattr(task_mod, "get_settings", _settings)
    monkeypatch.setattr(task_mod, "build_incremental_comment_label_plan", _fake_plan)
    monkeypatch.setattr(task_mod, "run_incremental_comment_label_workflow", _fake_workflow)

    result = await task_mod._label_comments_batch(limit=10, lookback_days=30)

    assert result == {
        "processed": 3,
        "status": "completed",
        "task_scope": "incremental_only",
    }
    assert captured["plan_candidates"] == 1
    assert captured["online_budget_cap"] == task_mod._ONLINE_COMMENT_BUDGET_CAP


@pytest.mark.asyncio
async def test_backfill_legacy_labels_delegates_to_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def _fake_workflow(*, workflow_input: Any, deps: Any) -> dict[str, Any]:
        captured["workflow_input"] = workflow_input
        captured["deps"] = deps
        return {
            "processed": 3,
            "post_processed": 1,
            "comment_processed": 2,
            "persist_failures": 0,
            "sync_failures": 0,
            "status": "completed",
        }

    monkeypatch.setattr(task_mod, "run_legacy_label_backfill_workflow", _fake_workflow)

    result = await task_mod._backfill_legacy_labels(limit=123)

    assert captured["workflow_input"].limit == 123
    assert captured["workflow_input"].prompt_version == "legacy_v2"
    assert result["processed"] == 3
    assert result["status"] == "completed"
