from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.services.llm.llm_label_task_runtime import (
    LLMLabelTaskRuntimeConfig,
    LLMLabelTaskRuntimeDeps,
    run_backfill_legacy_labels_task,
    run_label_comments_task,
    run_label_posts_task,
)


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        llm_label_post_limit=10,
        llm_label_comment_limit=12,
        llm_label_lookback_days=30,
        llm_label_model_name="gemini-test",
        llm_label_prompt_version="v-test",
        llm_label_body_chars=200,
        llm_label_comment_chars=80,
    )


def _config() -> LLMLabelTaskRuntimeConfig:
    return LLMLabelTaskRuntimeConfig(
        llm_batch_size=2,
        low_score_max=2.0,
        high_score_min=7.0,
        high_score_ratio=0.3,
        mid_score_min=5.0,
        mid_score_max=7.0,
        lab_long_sample_rate=0.15,
        lab_body_ratio=0.6,
        lab_comment_ratio=0.6,
        online_comment_budget_cap=500,
    )


@pytest.mark.asyncio
async def test_run_label_posts_task_builds_workflow_inputs() -> None:
    captured: dict[str, Any] = {}

    async def _fake_workflow(*, workflow_input: Any, deps: Any) -> dict[str, Any]:
        captured["workflow_input"] = workflow_input
        captured["deps"] = deps
        return {"status": "completed", "processed": 2}

    async def _fake_fetch_post_candidates(**_kwargs: Any) -> list[dict[str, Any]]:
        return []

    async def _fake_fetch_top_comments(**_kwargs: Any) -> list[str]:
        return []

    result = await run_label_posts_task(
        limit=11,
        lookback_days=45,
        deps=LLMLabelTaskRuntimeDeps(
            get_settings=_settings,
            session_factory=lambda: None,
            labeler_factory=object,
            fetch_post_candidates=_fake_fetch_post_candidates,
            fetch_top_comments=_fake_fetch_top_comments,
            build_incremental_comment_label_plan=lambda **_kwargs: None,
            persist_post_analysis=lambda **_kwargs: None,
            persist_comment_analysis=lambda **_kwargs: None,
            upsert_legacy_post_label=lambda **_kwargs: None,
            upsert_legacy_comment_label=lambda **_kwargs: None,
            sync_llm_terms=lambda *_args, **_kwargs: None,
            json_sanitize=lambda value: value,
            run_incremental_post_label_workflow=_fake_workflow,
            run_incremental_comment_label_workflow=lambda **_kwargs: None,
            run_legacy_label_backfill_workflow=lambda **_kwargs: None,
        ),
        config=_config(),
    )

    assert result["status"] == "completed"
    assert captured["workflow_input"].limit == 11
    assert captured["workflow_input"].lookback_days == 45
    assert captured["workflow_input"].llm_batch_size == 2
    assert callable(captured["deps"].fetch_post_candidates)
    assert callable(captured["deps"].fetch_top_comments)


@pytest.mark.asyncio
async def test_run_label_comments_task_builds_plan_and_budget_cap() -> None:
    captured: dict[str, Any] = {}

    async def _fake_plan(*, limit: int, lookback_days: int) -> Any:
        captured["plan_limit"] = limit
        captured["plan_days"] = lookback_days
        return SimpleNamespace(candidates=[1, 2, 3])

    async def _fake_workflow(*, workflow_input: Any, deps: Any) -> dict[str, Any]:
        captured["workflow_input"] = workflow_input
        captured["deps"] = deps
        return {"status": "completed", "processed": 3}

    result = await run_label_comments_task(
        limit=22,
        lookback_days=60,
        deps=LLMLabelTaskRuntimeDeps(
            get_settings=_settings,
            session_factory=lambda: None,
            labeler_factory=object,
            fetch_post_candidates=lambda **_kwargs: None,
            fetch_top_comments=lambda **_kwargs: None,
            build_incremental_comment_label_plan=_fake_plan,
            persist_post_analysis=lambda **_kwargs: None,
            persist_comment_analysis=lambda **_kwargs: None,
            upsert_legacy_post_label=lambda **_kwargs: None,
            upsert_legacy_comment_label=lambda **_kwargs: None,
            sync_llm_terms=lambda *_args, **_kwargs: None,
            json_sanitize=lambda value: value,
            run_incremental_post_label_workflow=lambda **_kwargs: None,
            run_incremental_comment_label_workflow=_fake_workflow,
            run_legacy_label_backfill_workflow=lambda **_kwargs: None,
        ),
        config=_config(),
    )

    assert result["processed"] == 3
    assert captured["plan_limit"] == 22
    assert captured["plan_days"] == 60
    assert captured["workflow_input"].online_budget_cap == 500
    assert len(captured["workflow_input"].plan.candidates) == 3


@pytest.mark.asyncio
async def test_run_backfill_legacy_labels_task_builds_workflow_deps() -> None:
    captured: dict[str, Any] = {}

    async def _fake_workflow(*, workflow_input: Any, deps: Any) -> dict[str, Any]:
        captured["workflow_input"] = workflow_input
        captured["deps"] = deps
        return {"status": "completed", "processed": 4}

    result = await run_backfill_legacy_labels_task(
        limit=123,
        deps=LLMLabelTaskRuntimeDeps(
            get_settings=_settings,
            session_factory=lambda: None,
            labeler_factory=object,
            fetch_post_candidates=lambda **_kwargs: None,
            fetch_top_comments=lambda **_kwargs: None,
            build_incremental_comment_label_plan=lambda **_kwargs: None,
            persist_post_analysis=lambda **_kwargs: None,
            persist_comment_analysis=lambda **_kwargs: None,
            upsert_legacy_post_label=lambda **_kwargs: None,
            upsert_legacy_comment_label=lambda **_kwargs: None,
            sync_llm_terms=lambda *_args, **_kwargs: None,
            json_sanitize=lambda value: {"wrapped": value},
            run_incremental_post_label_workflow=lambda **_kwargs: None,
            run_incremental_comment_label_workflow=lambda **_kwargs: None,
            run_legacy_label_backfill_workflow=_fake_workflow,
        ),
    )

    assert result["processed"] == 4
    assert captured["workflow_input"].limit == 123
    assert captured["workflow_input"].prompt_version == "legacy_v2"
    assert captured["deps"].json_sanitize("ok") == {"wrapped": "ok"}
