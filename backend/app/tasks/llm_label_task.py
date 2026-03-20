from __future__ import annotations

import logging
from typing import Any

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.llm.comment_label_planner import (
    HIGH_SCORE_MIN as _HIGH_SCORE_MIN,
    LOW_SCORE_MAX as _LOW_SCORE_MAX,
    MIN_COMMENT_CHARS as _MIN_COMMENT_CHARS,
    build_incremental_comment_label_plan,
)
from app.services.llm.post_label_planner import (
    fetch_incremental_post_candidates,
    fetch_post_top_comments,
)
from app.services.llm.comment_label_workflow import (
    run_incremental_comment_label_workflow,
)
from app.services.llm.llm_label_task_runtime import (
    LLMLabelTaskRuntimeConfig,
    LLMLabelTaskRuntimeDeps,
    run_backfill_legacy_labels_task,
    run_label_comments_task,
    run_label_posts_task,
)
from app.services.llm.post_label_workflow import (
    run_incremental_post_label_workflow,
)
from app.services.llm.label_batch_support import json_sanitize
from app.services.llm.legacy_label_persistence import (
    upsert_legacy_comment_label,
    upsert_legacy_post_label,
)
from app.services.llm.label_result_persistence import (
    persist_incremental_comment_analysis,
    persist_incremental_post_analysis,
)
from app.services.llm.legacy_label_backfill_workflow import (
    run_legacy_label_backfill_workflow,
)
from app.services.llm.labeling import LLMLabeler
from app.services.semantic.llm_term_sync import sync_llm_terms
from app.utils.asyncio_runner import run as run_coro

logger = logging.getLogger(__name__)

_LAB_LONG_SAMPLE_RATE = 0.15
_MID_SCORE_MIN = 5.0
_MID_SCORE_MAX = 7.0
_HIGH_SCORE_RATIO = 0.3
_LAB_BODY_RATIO = 0.6
_LAB_COMMENT_RATIO = 0.6
_LLM_BATCH_SIZE = 2
# --- Phase A: 在线链路规则层止血 ---
# 短评论阈值: 规范化后 body 长度 < 此值的评论不送 LLM，直接跳过
# 在线链路单次任务最大评论处理上限，超出后显式返回 degraded
_ONLINE_COMMENT_BUDGET_CAP = 500

_RUNTIME_CONFIG = LLMLabelTaskRuntimeConfig(
    llm_batch_size=_LLM_BATCH_SIZE,
    low_score_max=_LOW_SCORE_MAX,
    high_score_min=_HIGH_SCORE_MIN,
    high_score_ratio=_HIGH_SCORE_RATIO,
    mid_score_min=_MID_SCORE_MIN,
    mid_score_max=_MID_SCORE_MAX,
    lab_long_sample_rate=_LAB_LONG_SAMPLE_RATE,
    lab_body_ratio=_LAB_BODY_RATIO,
    lab_comment_ratio=_LAB_COMMENT_RATIO,
    online_comment_budget_cap=_ONLINE_COMMENT_BUDGET_CAP,
)


async def _fetch_post_candidates(limit: int, lookback_days: int) -> list[dict[str, Any]]:
    return await fetch_incremental_post_candidates(
        limit=limit,
        lookback_days=lookback_days,
        session_factory=SessionFactory,
        low_score_max=_LOW_SCORE_MAX,
        high_score_min=_HIGH_SCORE_MIN,
        high_score_ratio=_HIGH_SCORE_RATIO,
    )


async def _fetch_top_comments(
    source: str, source_post_id: str, limit: int
) -> list[str]:
    return await fetch_post_top_comments(
        source=source,
        source_post_id=source_post_id,
        limit=limit,
        session_factory=SessionFactory,
    )


def _build_runtime_deps() -> LLMLabelTaskRuntimeDeps:
    return LLMLabelTaskRuntimeDeps(
        get_settings=get_settings,
        session_factory=SessionFactory,
        labeler_factory=LLMLabeler,
        fetch_post_candidates=_fetch_post_candidates,
        fetch_top_comments=_fetch_top_comments,
        build_incremental_comment_label_plan=build_incremental_comment_label_plan,
        persist_post_analysis=persist_incremental_post_analysis,
        persist_comment_analysis=persist_incremental_comment_analysis,
        upsert_legacy_post_label=upsert_legacy_post_label,
        upsert_legacy_comment_label=upsert_legacy_comment_label,
        sync_llm_terms=sync_llm_terms,
        json_sanitize=json_sanitize,
        run_incremental_post_label_workflow=run_incremental_post_label_workflow,
        run_incremental_comment_label_workflow=run_incremental_comment_label_workflow,
        run_legacy_label_backfill_workflow=run_legacy_label_backfill_workflow,
    )


async def _label_posts_batch(limit: int, lookback_days: int) -> dict[str, Any]:
    return await run_label_posts_task(
        limit=limit,
        lookback_days=lookback_days,
        deps=_build_runtime_deps(),
        config=_RUNTIME_CONFIG,
    )


async def _label_comments_batch(limit: int, lookback_days: int) -> dict[str, Any]:
    return await run_label_comments_task(
        limit=limit,
        lookback_days=lookback_days,
        deps=_build_runtime_deps(),
        config=_RUNTIME_CONFIG,
    )


async def _backfill_legacy_labels(limit: int) -> dict[str, Any]:
    return await run_backfill_legacy_labels_task(
        limit=limit,
        deps=_build_runtime_deps(),
    )


@celery_app.task(name="tasks.llm.label_posts_batch")  # type: ignore[misc]
def label_posts_batch(limit: int | None = None) -> dict[str, Any]:
    settings = get_settings()
    limit_value = int(limit or settings.llm_label_post_limit)
    days = int(settings.llm_label_lookback_days)
    result = run_coro(_label_posts_batch(limit_value, days))
    logger.info(
        "label_posts_batch status=%s processed=%s attempted=%s",
        result.get("status"),
        result.get("processed"),
        result.get("attempted"),
    )
    return result


@celery_app.task(name="tasks.llm.label_comments_batch")  # type: ignore[misc]
def label_comments_batch(limit: int | None = None) -> dict[str, Any]:
    settings = get_settings()
    limit_value = int(limit or settings.llm_label_comment_limit)
    days = int(settings.llm_label_lookback_days)
    result = run_coro(_label_comments_batch(limit_value, days))
    logger.info(
        "label_comments_batch status=%s processed=%s attempted=%s",
        result.get("status"),
        result.get("processed"),
        result.get("attempted"),
    )
    return result


@celery_app.task(name="tasks.llm.backfill_legacy_labels")  # type: ignore[misc]
def backfill_legacy_labels(limit: int = 2000) -> dict[str, Any]:
    result = run_coro(_backfill_legacy_labels(limit))
    logger.info(
        "backfill_legacy_labels status=%s processed=%s persist_failures=%s sync_failures=%s",
        result.get("status"),
        result.get("processed"),
        result.get("persist_failures"),
        result.get("sync_failures"),
    )
    return result


__all__ = ["label_posts_batch", "label_comments_batch", "backfill_legacy_labels"]
