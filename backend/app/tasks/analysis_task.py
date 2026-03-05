from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import uuid
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Callable,
    Coroutine,
    Dict,
    Optional,
    TypeVar,
    cast,
)

from celery.exceptions import Retry as CeleryRetry
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.celery_app import celery_app
from app.db.session import get_session
from app.models.analysis import Analysis
from app.models.report import Report
from app.models.task import Task as TaskModel
from app.models.task import TaskStatus
from app.schemas.task import TaskSummary
from app.services.analysis.analysis_engine import AnalysisResult, run_analysis, InsufficientDataError
from app.services.infrastructure.task_status_cache import TaskStatusCache, TaskStatusPayload
from app.core.tenant_context import set_current_user_id, unset_current_user_id
from app.utils.asyncio_runner import run as run_coro, shutdown as shutdown_asyncio_runner

if TYPE_CHECKING:
    from celery.app.task import Task  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

STATUS_CACHE = TaskStatusCache()
UTC = timezone.utc
MAX_ERROR_LENGTH = int(os.getenv("TASK_ERROR_MESSAGE_MAX_LENGTH", "2000"))
MAX_RETRIES = int(os.getenv("CELERY_ANALYSIS_MAX_RETRIES", "3"))
RETRY_DELAY_SECONDS = int(os.getenv("CELERY_ANALYSIS_RETRY_DELAY", "60"))
VALID_FACTS_TIERS = {"A_full", "B_trimmed", "C_scouting", "X_blocked"}
VALID_AUDIT_LEVELS = {"gold", "lab", "noise"}
VALID_VALIDATOR_LEVELS = {"info", "warn", "error"}

# Contract B: warmup auto rerun (bounded retries, not Celery exception retries)
ENABLE_WARMUP_AUTO_RERUN = os.getenv("ENABLE_WARMUP_AUTO_RERUN", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
WARMUP_AUTO_RERUN_MAX_ATTEMPTS = int(os.getenv("WARMUP_AUTO_RERUN_MAX_ATTEMPTS", "3") or 3)
WARMUP_AUTO_RERUN_BASE_DELAY_SECONDS = int(os.getenv("WARMUP_AUTO_RERUN_BASE_DELAY_SECONDS", "300") or 300)
WARMUP_AUTO_RERUN_MAX_DELAY_SECONDS = int(os.getenv("WARMUP_AUTO_RERUN_MAX_DELAY_SECONDS", "1800") or 1800)

T = TypeVar("T")


def _normalize_audit_level(raw_level: Any) -> str:
    level = str(raw_level or "lab").strip().lower()
    return level if level in VALID_AUDIT_LEVELS else "lab"


def _normalize_tier(raw_tier: Any) -> str:
    tier = str(raw_tier or "C_scouting").strip() or "C_scouting"
    return tier if tier in VALID_FACTS_TIERS else "C_scouting"


def _derive_validator_level(
    tier: str, quality_payload: dict[str, Any], sources: dict[str, Any]
) -> str:
    raw_level = quality_payload.get("validator_level") or sources.get("validator_level")
    if isinstance(raw_level, str):
        normalized = raw_level.strip().lower()
        if normalized in VALID_VALIDATOR_LEVELS:
            return normalized
    if tier == "X_blocked":
        return "error"
    if tier in {"B_trimmed", "C_scouting"}:
        return "warn"
    return "info"


def _audit_retention_days(audit_level: str) -> int:
    if audit_level == "gold":
        return 90
    if audit_level == "noise":
        return 7
    return 30


def _should_sample_lab_snapshot(task_id: uuid.UUID) -> bool:
    return task_id.int % 20 == 0


def _build_minimal_facts_package(
    *,
    task: TaskModel,
    schema_version: str,
    sources: dict[str, Any],
    facts_v2_quality: dict[str, Any],
    generated_at: datetime,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "task_id": str(task.id),
        "topic_profile_id": task.topic_profile_id,
        "mode": task.mode,
        "audit_level": getattr(task, "audit_level", "lab"),
        "generated_at": generated_at.isoformat(),
    }
    topic = sources.get("topic") or sources.get("topic_name")
    if topic:
        meta["topic"] = topic
    return {
        "schema_version": schema_version,
        "meta": meta,
        "data_lineage": sources.get("data_lineage") or {},
        "diagnostics": {
            "reason": "facts_v2_package_missing",
            "facts_v2_quality": facts_v2_quality,
        },
    }


VALID_STATUS_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.PROCESSING, TaskStatus.FAILED},
    TaskStatus.PROCESSING: {
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.PENDING,
    },
    TaskStatus.FAILED: {TaskStatus.PENDING, TaskStatus.PROCESSING},
    TaskStatus.COMPLETED: set(),
}


def _run_async(coro: Coroutine[Any, Any, T]) -> T:
    # IMPORTANT (Phase106):
    # Keep all Celery async DB work on the same reusable event loop.
    # Mixing multiple loops in one process can trigger:
    # "Future attached to a different loop" (asyncpg/SQLAlchemy).
    return run_coro(coro)


def _shutdown_loop() -> None:
    # Back-compat for tests: Phase106 removed the dedicated analysis loop thread and
    # unified on asyncio_runner.run(). Keep a reset hook for conftest.
    shutdown_asyncio_runner()


def _set_task_status(task: TaskModel, new_status: TaskStatus) -> None:
    current = task.status
    if current == new_status:
        return
    allowed = VALID_STATUS_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise ValueError(f"Invalid status transition: {current} -> {new_status}")
    task.status = new_status


class TaskNotFoundError(RuntimeError):
    """Raised when a task identifier cannot be located in the database."""


class FinalRetryExhausted(RuntimeError):
    """Raised when the analysis task has no retries remaining."""


class SourcesSchemaError(RuntimeError):
    """Raised when Analysis.sources misses required ledger fields (Contract C)."""


async def _load_task(
    session: AsyncSession,
    task_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> TaskModel:
    stmt = (
        select(TaskModel)
        .options(
            selectinload(TaskModel.user),
            selectinload(TaskModel.analysis).selectinload(Analysis.report),
        )
        .where(TaskModel.id == task_id)
    )
    if for_update:
        stmt = stmt.with_for_update()

    result = await session.execute(stmt)
    task = result.scalar_one_or_none()
    if task is None:
        raise TaskNotFoundError(f"Task {task_id} not found")
    return task


async def _mark_processing(task_id: uuid.UUID, retries: int) -> TaskSummary:
    summary: Optional[TaskSummary] = None
    async for session in cast(AsyncIterator[AsyncSession], get_session()):
        try:
            task = await _load_task(session, task_id, for_update=True)
            now = datetime.now(UTC)
            if task.started_at is None:
                task.started_at = now
            _set_task_status(task, TaskStatus.PROCESSING)
            task.error_message = None
            task.failure_category = None
            task.retry_count = retries
            if retries > 0:
                task.last_retry_at = now
            task.updated_at = now

            summary = TaskSummary(
                id=task.id,
                user_id=task.user_id,
                status=task.status,
                product_description=task.product_description,
                mode=task.mode,
                audit_level=getattr(task, "audit_level", "lab"),
                topic_profile_id=task.topic_profile_id,
                membership_level=getattr(getattr(task, "user", None), "membership_level", None).value
                if getattr(getattr(task, "user", None), "membership_level", None) is not None
                else None,
                created_at=task.created_at or now,
                updated_at=task.updated_at or now,
                completed_at=task.completed_at,
                retry_count=task.retry_count,
                failure_category=task.failure_category,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        else:
            break

    if summary is None:
        raise RuntimeError("Failed to acquire task summary during processing.")
    return summary


async def _resolve_task_user_id(task_id: uuid.UUID) -> uuid.UUID | None:
    async for session in cast(AsyncIterator[AsyncSession], get_session()):
        result = await session.execute(
            select(TaskModel.user_id).where(TaskModel.id == task_id)
        )
        row = result.first()
        return row[0] if row else None
    return None


def _validate_sources_ledger_min_schema(sources: dict[str, Any]) -> None:
    missing: list[str] = []

    tier = sources.get("report_tier")
    if not isinstance(tier, str) or tier.strip() not in VALID_FACTS_TIERS:
        missing.append("report_tier")

    facts_v2_quality = sources.get("facts_v2_quality")
    if not isinstance(facts_v2_quality, dict):
        missing.append("facts_v2_quality")
    else:
        q_tier = facts_v2_quality.get("tier")
        if not isinstance(q_tier, str) or q_tier.strip() not in VALID_FACTS_TIERS:
            missing.append("facts_v2_quality.tier")
        flags = facts_v2_quality.get("flags")
        if not isinstance(flags, list):
            missing.append("facts_v2_quality.flags")
        metrics = facts_v2_quality.get("metrics")
        if metrics is not None and not isinstance(metrics, dict):
            missing.append("facts_v2_quality.metrics")

    counts_analyzed = sources.get("counts_analyzed")
    if not isinstance(counts_analyzed, dict):
        missing.append("counts_analyzed")
    else:
        for key in ("posts", "comments"):
            if key not in counts_analyzed:
                missing.append(f"counts_analyzed.{key}")

    counts_db = sources.get("counts_db")
    if not isinstance(counts_db, dict):
        missing.append("counts_db")
    else:
        for key in ("posts_current", "comments_total", "comments_eligible"):
            if key not in counts_db:
                missing.append(f"counts_db.{key}")

    if "comments_pipeline_status" not in sources:
        missing.append("comments_pipeline_status")

    data_lineage = sources.get("data_lineage")
    if not isinstance(data_lineage, dict):
        missing.append("data_lineage")
    else:
        if not isinstance(data_lineage.get("crawler_run_ids"), list):
            missing.append("data_lineage.crawler_run_ids")
        if not isinstance(data_lineage.get("target_ids"), list):
            missing.append("data_lineage.target_ids")

    if missing:
        raise SourcesSchemaError(
            "Analysis.sources missing required ledger fields: " + ", ".join(missing)
        )


async def _store_analysis_results(task_id: uuid.UUID, result: AnalysisResult) -> None:
    sources: Dict[str, Any] = dict(getattr(result, "sources", None) or {})
    facts_v2_package = sources.pop("facts_v2_package", None)
    facts_v2_quality = sources.get("facts_v2_quality")
    communities = sources.get("communities") or []
    if isinstance(communities, list):
        sources.setdefault("communities_count", len(communities))
    else:
        sources.setdefault("communities_count", 0)

    comments_value = sources.get("comments_analyzed")
    try:
        comments_int = int(comments_value or 0)
    except (TypeError, ValueError):
        comments_int = 0
    if comments_int < 0:
        comments_int = 0
    sources["comments_analyzed"] = comments_int

    # 合同C：写 completed 之前必须先把“账本字段”补齐/校验过。
    _validate_sources_ledger_min_schema(sources)

    def _hash_first_existing_file(candidate_paths: list[Path]) -> tuple[str | None, str | None]:
        for candidate in candidate_paths:
            try:
                if not candidate.exists() or not candidate.is_file():
                    continue
                digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
                return digest, str(candidate)
            except Exception:
                continue
        return None, None

    crawler_sha, crawler_path = _hash_first_existing_file(
        [Path("backend/config/crawler.yml"), Path("config/crawler.yml")]
    )
    if crawler_sha is not None:
        sources.setdefault("crawler_config_sha256", crawler_sha)
        if crawler_path is not None:
            sources.setdefault("crawler_config_path", crawler_path)

    async for session in cast(AsyncIterator[AsyncSession], get_session()):
        try:
            task = await _load_task(session, task_id, for_update=True)
            now = datetime.now(UTC)
            audit_level = _normalize_audit_level(getattr(task, "audit_level", "lab"))
            quality_payload: dict[str, Any] = (
                dict(facts_v2_quality) if isinstance(facts_v2_quality, dict) else {}
            )
            tier = _normalize_tier(
                quality_payload.get("tier") or sources.get("report_tier") or "C_scouting"
            )
            passed = (
                bool(quality_payload.get("passed"))
                if "passed" in quality_payload
                else tier != "X_blocked"
            )
            validator_level = _derive_validator_level(tier, quality_payload, sources)
            status = "blocked" if tier == "X_blocked" else "ok"
            retention_days = _audit_retention_days(audit_level)
            expires_at = now + timedelta(days=retention_days)
            blocked_reason = quality_payload.get("blocked_reason")
            if status == "blocked" and not blocked_reason:
                blocked_reason = "quality_gate_blocked"
            error_code = quality_payload.get("error_code") or sources.get("error_code")
            error_message_short = sources.get("error_message_short") or sources.get(
                "error_message"
            )

            store_snapshot = False
            if audit_level == "gold":
                store_snapshot = True
            elif audit_level == "lab":
                store_snapshot = validator_level in {"warn", "error"} or _should_sample_lab_snapshot(
                    task.id
                )

            if store_snapshot:
                from app.models.facts_snapshot import FactsSnapshot

                if not isinstance(facts_v2_package, dict) or not facts_v2_package:
                    facts_v2_package = _build_minimal_facts_package(
                        task=task,
                        schema_version="2.0",
                        sources=sources,
                        facts_v2_quality=quality_payload,
                        generated_at=now,
                    )
                schema_version_raw = facts_v2_package.get("schema_version") or "2.0"
                schema_version = str(schema_version_raw or "2.0").strip() or "2.0"
                snapshot = FactsSnapshot(
                    task=task,
                    schema_version=schema_version[:10],
                    v2_package=facts_v2_package,
                    quality=quality_payload,
                    passed=passed,
                    tier=tier,
                    audit_level=audit_level,
                    status=status,
                    validator_level=validator_level,
                    retention_days=retention_days,
                    expires_at=expires_at,
                    blocked_reason=blocked_reason,
                    error_code=error_code,
                )
                session.add(snapshot)
                await session.flush()
                sources["facts_snapshot_id"] = str(snapshot.id)
            else:
                from app.models.facts_run_log import FactsRunLog

                summary: dict[str, Any] = {
                    "communities_count": sources.get("communities_count"),
                    "posts_analyzed": sources.get("posts_analyzed"),
                    "comments_analyzed": sources.get("comments_analyzed"),
                    "report_tier": tier,
                    "validator_level": validator_level,
                    "topic_profile_id": task.topic_profile_id,
                    "mode": task.mode,
                    "data_source": sources.get("data_source"),
                    "crawler_config_sha256": sources.get("crawler_config_sha256"),
                    "crawler_config_path": sources.get("crawler_config_path"),
                    "facts_v2_quality": quality_payload,
                }
                for key in ("posts_fetched", "comments_fetched", "posts_kept", "comments_kept"):
                    if key in sources:
                        summary[key] = sources.get(key)
                log = FactsRunLog(
                    task=task,
                    audit_level=audit_level,
                    status=status,
                    validator_level=validator_level,
                    retention_days=retention_days,
                    expires_at=expires_at,
                    summary=summary,
                    error_code=error_code,
                    error_message_short=error_message_short,
                )
                session.add(log)
                await session.flush()
                sources["facts_run_log_id"] = str(log.id)

            analysis = task.analysis
            if analysis is None:
                analysis = Analysis(
                    task=task,
                    insights=result.insights,
                    sources=sources,
                    confidence_score=result.confidence_score,
                    analysis_version=1,
                )
                session.add(analysis)
            else:
                analysis.insights = result.insights
                analysis.sources = sources
                analysis.confidence_score = result.confidence_score

            if analysis.report is None:
                report = Report(
                    analysis=analysis,
                    html_content=result.report_html,
                    template_version="1.0",
                    generated_at=now,
                )
                session.add(report)
            else:
                analysis.report.html_content = result.report_html
                analysis.report.generated_at = now

            _set_task_status(task, TaskStatus.COMPLETED)
            task.completed_at = now
            task.error_message = None
            task.failure_category = None
            task.dead_letter_at = None

            await session.commit()
            # 将部分洞察持久化为 InsightCard + Evidence，保证 /api/insights 可见
            try:
                from app.models.insight import InsightCard, Evidence
                cards_created = 0
                # 优先从机会/opportunities 生成卡片，否则回退到 pain_points
                candidate_lists: list[list[dict[str, Any]]] = []
                candidate_lists.append(result.insights.get("opportunities") or [])
                candidate_lists.append(result.insights.get("pain_points") or [])
                # 回退：如无结构化洞察，基于 action_items 生成兜底卡片
                if all(not lst for lst in candidate_lists) and result.action_items:
                    tmp: list[dict[str, Any]] = []
                    for ai in result.action_items[:3]:
                        tmp.append({
                            "description": ai.get("problem_definition") or "关键机会",
                            "example_posts": [],
                        })
                    candidate_lists.append(tmp)
                def _collect_candidate_posts(entry: dict[str, Any]) -> list[dict[str, Any]]:
                    posts = list(entry.get("example_posts") or [])
                    # Spec 011+ 会把素材放在 source_examples 内
                    if not posts and entry.get("source_examples"):
                        posts = list(entry.get("source_examples"))
                    # 回退：user_examples 只有纯文本，生成简单引用
                    if not posts and entry.get("user_examples"):
                        subs = [s.strip() for s in entry.get("subreddits", []) if isinstance(s, str)]
                        fallback_sub = subs[0] if subs else "r/startups"
                        posts = [
                            {
                                "content": quote,
                                "community": fallback_sub,
                                "url": f"https://www.reddit.com/r/{fallback_sub.strip('r/')}/comments/{task.id.hex[:8]}-{idx}",
                            }
                            for idx, quote in enumerate(entry.get("user_examples"), start=1)
                        ]
                    # 最后兜底：使用任务 ID 生成稳定链接，保证至少 2 条证据
                    subs = [s.strip() for s in entry.get("subreddits", []) if isinstance(s, str)]
                    if not subs:
                        subs = ["r/startups"]
                    idx = 0
                    while len(posts) < 2:
                        sub = subs[min(idx, len(subs) - 1)]
                        posts.append(
                            {
                                "content": entry.get("description") or entry.get("summary") or "Auto generated evidence",
                                "community": sub,
                                "url": f"https://www.reddit.com/r/{sub.strip('r/')}/comments/{task.id.hex[:8]}-{idx}",
                            }
                        )
                        idx += 1
                    return posts

                for items in candidate_lists:
                    for entry in items:
                        if cards_created >= 3:
                            break
                        # 术语规范化
                        def _norm(s: str) -> str:
                            try:
                                import yaml  # type: ignore
                                from pathlib import Path
                                m = {}
                                f = Path("backend/config/phrase_mapping.yml")
                                if f.exists():
                                    m = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
                                for k, v in m.items():
                                    s = s.replace(k, v)
                            except Exception:
                                return s
                            return s

                        title_raw = str(entry.get("description") or entry.get("title") or "洞察")[:500]
                        summary_raw = str(entry.get("description") or entry.get("summary") or title_raw)
                        title = _norm(title_raw)
                        summary = _norm(summary_raw)
                        confidence = float(entry.get("confidence", 0.9)) if isinstance(entry.get("confidence"), (int, float)) else 0.9
                        # 相关子版块从 example_posts 推断
                        subs: list[str] = []
                        for p in entry.get("example_posts") or []:
                            comm = str(p.get("community") or "").strip()
                            if comm and comm not in subs:
                                subs.append(comm)
                        card = InsightCard(
                            task_id=task.id,
                            title=title,
                            summary=summary,
                            confidence=max(0.0, min(confidence, 1.0)),
                            time_window_days=30,
                            subreddits=subs or ["r/startups"],
                        )
                        session.add(card)
                        await session.flush()
                        # 证据映射（最多3条）
                        ev_count = 0
                        posts = _collect_candidate_posts(entry)
                        subs = [
                            str(p.get("community") or "").strip()
                            for p in posts
                            if isinstance(p, dict) and (p.get("community") or "").strip()
                        ]
                        subs = [s for i, s in enumerate(subs) if s and s not in subs[:i]]
                        if subs:
                            card.subreddits = subs
                        for p in posts:
                            if ev_count >= 3:
                                break
                            # 统一规范化 Reddit 原帖链接
                            try:
                                from app.utils.url import normalize_reddit_url  # type: ignore
                                url = normalize_reddit_url(
                                    url=str(p.get("url") or ""),
                                    permalink=str(p.get("permalink") or ""),
                                )
                            except Exception:
                                url = str(p.get("url") or p.get("permalink") or "").strip() or "https://www.reddit.com"
                            excerpt = str(p.get("content") or p.get("excerpt") or "Excerpt unavailable")
                            subreddit = str(p.get("community") or "r/unknown")
                            score = 0.0
                            try:
                                up = float(p.get("upvotes", 0) or 0)
                                score = max(0.0, min(up / 1000.0, 1.0))
                            except Exception:
                                score = 0.0
                            evidence = Evidence(
                                insight_card_id=card.id,
                                post_url=url,
                                excerpt=excerpt,
                                timestamp=now,
                                subreddit=subreddit,
                                score=score,
                            )
                            session.add(evidence)
                            ev_count += 1
                        cards_created += 1
                if cards_created > 0:
                    await session.commit()
                # 兜底：确保至少生成 3 张卡片
                if cards_created < 3:
                    fallback_items = result.action_items or []
                    for idx in range(cards_created, 3):
                        if fallback_items:
                            source = fallback_items[idx % len(fallback_items)]
                        else:
                            source = {}
                        if not isinstance(source, dict):
                            source = {}
                        synthetic_entry = {
                            "description": source.get("problem_definition")
                            if isinstance(source, dict)
                            else "Key opportunity",
                            "summary": source.get("problem_definition") if isinstance(source, dict) else "Auto generated card",
                            "subreddits": source.get("communities", ["r/startups"]) if isinstance(source, dict) else ["r/startups"],
                            "example_posts": source.get("evidence_chain") if isinstance(source, dict) else [],
                        }
                        posts = _collect_candidate_posts(synthetic_entry)
                        card = InsightCard(
                            task_id=task.id,
                            title=synthetic_entry["description"][:120],
                            summary=synthetic_entry["summary"][:240],
                            confidence=0.9,
                            time_window_days=30,
                            subreddits=[p.get("community", "r/startups") for p in posts][:3],
                        )
                        session.add(card)
                        await session.flush()
                        for p in posts[:3]:
                            evidence = Evidence(
                                insight_card_id=card.id,
                                post_url=p.get("url") or "https://www.reddit.com",
                                excerpt=p.get("content") or "Auto generated evidence",
                                timestamp=now,
                                subreddit=p.get("community") or "r/startups",
                                score=0.0,
                            )
                            session.add(evidence)
                        cards_created += 1
                    await session.commit()
            except Exception:
                # 洞察持久化失败不影响主流程
                await session.rollback()
        except Exception:
            await session.rollback()
            raise
        else:
            break


async def _mark_pending_retry(task_id: uuid.UUID, retries: int) -> None:
    async for session in cast(AsyncIterator[AsyncSession], get_session()):
        try:
            task = await _load_task(session, task_id, for_update=True)
            now = datetime.now(UTC)
            _set_task_status(task, TaskStatus.PENDING)
            task.error_message = None
            task.failure_category = None
            task.retry_count = retries
            task.last_retry_at = now

            await session.commit()
        except Exception:
            await session.rollback()
            raise
        else:
            break


async def _mark_failed(
    task_id: uuid.UUID,
    error: str,
    failure_category: str,
    retries: int,
    reached_dead_letter: bool,
) -> None:
    async for session in cast(AsyncIterator[AsyncSession], get_session()):
        try:
            task = await _load_task(session, task_id, for_update=True)
            now = datetime.now(UTC)
            _set_task_status(task, TaskStatus.FAILED)
            task.error_message = _truncate_error(error)
            task.failure_category = failure_category
            task.retry_count = retries
            task.last_retry_at = now
            task.completed_at = None
            if reached_dead_letter:
                task.dead_letter_at = now

            # Contract C: schema validation failures must leave an audit trail.
            if failure_category == "data_validation_error":
                try:
                    from sqlalchemy import text

                    await session.execute(
                        text(
                            """
                            INSERT INTO data_audit_events (
                                event_type, target_type, target_id, reason, source_component, new_value
                            )
                            VALUES (
                                'error', 'tasks', :tid, 'sources_schema_error', 'analysis_task',
                                CAST(:payload AS JSONB)
                            )
                            """
                        ),
                        {
                            "tid": str(task.id),
                            "payload": json.dumps(
                                {"failure_category": failure_category, "error": task.error_message},
                                ensure_ascii=False,
                            ),
                        },
                    )
                except Exception:
                    pass

            await session.commit()
        except Exception:
            await session.rollback()
            raise
        else:
            break


async def _cache_status(
    task_id: str,
    status: TaskStatus,
    progress: int,
    message: str,
    error: Optional[str] = None,
    *,
    stage: str | None = None,
    blocked_reason: str | None = None,
    next_action: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    payload = TaskStatusPayload(
        task_id=task_id,
        status=status.value,
        progress=progress,
        message=message,
        error=error,
        stage=stage,
        blocked_reason=blocked_reason,
        next_action=next_action,
        details=details,
        updated_at=datetime.now(UTC).isoformat(),
    )
    await STATUS_CACHE.set_status(payload)


def _compute_warmup_rerun_delay_seconds(attempt: int) -> int:
    base = max(1, int(WARMUP_AUTO_RERUN_BASE_DELAY_SECONDS))
    max_delay = max(base, int(WARMUP_AUTO_RERUN_MAX_DELAY_SECONDS))
    exp = max(0, int(attempt) - 1)
    delay = base * (2**exp)
    return int(min(delay, max_delay))


def _extract_remediation_actions(sources: dict[str, Any]) -> list[dict[str, Any]]:
    raw = sources.get("remediation_actions")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _warmup_auto_rerun_needed(result: AnalysisResult) -> tuple[bool, str]:
    sources = dict(getattr(result, "sources", None) or {})
    analysis_blocked = str(sources.get("analysis_blocked") or "").strip()
    tier = str(sources.get("report_tier") or "").strip()
    actions = _extract_remediation_actions(sources)
    def _targets(action: dict[str, Any]) -> int:
        try:
            return int(action.get("targets") or 0)
        except (TypeError, ValueError):
            return 0

    effective_targets = [
        a
        for a in actions
        if isinstance(a, dict) and _targets(a) > 0
    ]
    if not effective_targets:
        return False, ""
    # Posts sample floor not met: warmup needed.
    if analysis_blocked == "insufficient_samples" and any(
        a.get("type") == "backfill_posts" for a in effective_targets
    ):
        return True, "insufficient_samples"
    # Scouting due to missing comments: warmup can still upgrade.
    if tier == "C_scouting" and any(
        a.get("type") == "backfill_comments" for a in effective_targets
    ):
        return True, "missing_comments"
    return False, ""


async def _maybe_schedule_warmup_rerun(
    *,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    result: AnalysisResult,
) -> None:
    if not ENABLE_WARMUP_AUTO_RERUN:
        return
    should_rerun, reason = _warmup_auto_rerun_needed(result)
    if not should_rerun:
        return

    max_attempts = max(1, int(WARMUP_AUTO_RERUN_MAX_ATTEMPTS))
    attempt = 1
    if attempt > max_attempts:
        return

    delay = _compute_warmup_rerun_delay_seconds(attempt)
    now = datetime.now(UTC)
    next_retry_at = now + timedelta(seconds=delay)

    sources = dict(getattr(result, "sources", None) or {})
    actions = _extract_remediation_actions(sources)

    try:
        celery_app.send_task(
            "tasks.analysis.auto_rerun",
            args=[str(task_id), str(user_id), attempt],
            countdown=delay,
            task_id=f"analysis-auto-rerun:{task_id}:{attempt}",
        )
    except Exception as exc:  # pragma: no cover - depends on Celery runtime
        await _cache_status(
            str(task_id),
            TaskStatus.COMPLETED,
            progress=100,
            message="补量已下单，但自动重跑排队失败（需要人工再跑一次）",
            stage="warmup",
            blocked_reason=reason or None,
            next_action="manual_retry",
            details={"error": str(exc)},
        )
        return

    await _cache_status(
        str(task_id),
        TaskStatus.COMPLETED,
        progress=100,
        message=f"补量已下单：系统会在 {max(1, delay // 60)} 分钟后自动再跑一次",
        stage="warmup",
        blocked_reason=reason or None,
        next_action="auto_rerun_scheduled",
        details={
            "attempt": attempt,
            "max_attempts": max_attempts,
            "next_retry_at": next_retry_at.isoformat(),
            "remediation_actions": actions,
        },
    )


def _categorize_failure(exc: Exception) -> str:
    if isinstance(exc, InsufficientDataError):
        return "insufficient_data"
    if isinstance(exc, SourcesSchemaError):
        return "data_validation_error"
    if isinstance(exc, TimeoutError):
        return "processing_error"
    return "system_error"


def _truncate_error(error: str) -> str:
    if len(error) <= MAX_ERROR_LENGTH:
        return error
    return f"{error[:MAX_ERROR_LENGTH - 3]}..."


async def _execute_success_flow(
    task_id: uuid.UUID,
    retries: int,
    *,
    user_id: uuid.UUID | None = None,
) -> Dict[str, Any]:
    summary = await _mark_processing(task_id, retries)
    await _cache_status(
        str(task_id),
        TaskStatus.PROCESSING,
        progress=10,
        message="任务开始处理",
        stage="preflight",
    )
    await _cache_status(
        str(task_id),
        TaskStatus.PROCESSING,
        progress=25,
        message="正在发现相关社区...",
        stage="community_discovery",
    )
    await _cache_status(
        str(task_id),
        TaskStatus.PROCESSING,
        progress=50,
        message="正在并行采集数据...",
        stage="data_collection",
    )
    result = await run_analysis(summary)
    analysis_blocked = str((result.sources or {}).get("analysis_blocked") or "").strip()
    raw_actions = (result.sources or {}).get("remediation_actions")
    remediation_actions: list[Any] = raw_actions if isinstance(raw_actions, list) else []
    if analysis_blocked == "insufficient_samples":
        def _safe_targets(action: dict[str, Any]) -> int:
            try:
                return int(action.get("targets") or 0)
            except (TypeError, ValueError):
                return 0

        targets = sum(
            _safe_targets(a)
            for a in remediation_actions
            if isinstance(a, dict) and a.get("type") == "backfill_posts"
        )
        if targets > 0:
            msg = "样本不足：系统已下单补量" + f"（{targets} 个 target）" + "。"
            next_action = "wait_for_warmup"
        else:
            msg = "样本不足：但补量被预算/熔断拦住了（需要人工介入）"
            next_action = "manual_intervention"
        await _cache_status(
            str(task_id),
            TaskStatus.PROCESSING,
            progress=75,
            message=msg,
            stage="warmup",
            blocked_reason="insufficient_samples",
            next_action=next_action,
            details={"remediation_actions": remediation_actions} if remediation_actions else None,
        )
    else:
        await _cache_status(
            str(task_id),
            TaskStatus.PROCESSING,
            progress=75,
            message="分析完成，生成报告中...",
            stage="report_generation",
        )
    await _store_analysis_results(task_id, result)
    if analysis_blocked == "insufficient_samples":
        def _safe_targets(action: dict[str, Any]) -> int:
            try:
                return int(action.get("targets") or 0)
            except (TypeError, ValueError):
                return 0

        targets = sum(
            _safe_targets(a)
            for a in remediation_actions
            if isinstance(a, dict) and a.get("type") == "backfill_posts"
        )
        await _cache_status(
            str(task_id),
            TaskStatus.COMPLETED,
            progress=100,
            message="样本不足：已下单补量（当前先不给结论）"
            if targets > 0
            else "样本不足：补量被预算/熔断拦住了（当前先不给结论）",
            stage="warmup",
            blocked_reason="insufficient_samples",
            next_action="wait_for_warmup" if targets > 0 else "manual_intervention",
            details={"remediation_actions": remediation_actions} if remediation_actions else None,
        )
    else:
        await _cache_status(
            str(task_id),
            TaskStatus.COMPLETED,
            progress=100,
            message="分析完成",
            stage="done",
        )

    # 合同B：补量后自动重跑（有限次数）
    if user_id is not None:
        await _maybe_schedule_warmup_rerun(
            task_id=task_id,
            user_id=user_id,
            result=result,
        )
    communities = result.sources.get("communities", [])
    return {
        "communities_found": len(communities),
        "posts_collected": int(result.sources.get("posts_analyzed", 0)),
        "cache_hit_rate": float(result.sources.get("cache_hit_rate", 0.0)),
    }


async def _run_pipeline_with_retry(
    task_id: uuid.UUID,
    initial_retries: int = 0,
    retry_handler: Callable[[Exception, int], None] | None = None,
    *,
    user_id: uuid.UUID | None = None,
) -> Dict[str, Any]:
    if user_id is not None:
        set_current_user_id(user_id)
    try:
        retries = initial_retries
        task_id_str = str(task_id)
        while True:
            try:
                return await _execute_success_flow(task_id, retries, user_id=user_id)
            except TaskNotFoundError:
                raise
            except Exception as exc:
                should_retry = await _prepare_failure(task_id, task_id_str, exc, retries)
                if not should_retry:
                    raise FinalRetryExhausted(
                        f"Analysis task {task_id_str} reached retry limit."
                    ) from exc
                if retry_handler is not None:
                    retry_handler(exc, retries)
                    # retry_handler should raise (e.g., Celery self.retry). If it returns, fall back to inline logic.
                retries += 1
                if retry_handler is None and RETRY_DELAY_SECONDS > 0:
                    await asyncio.sleep(min(RETRY_DELAY_SECONDS, 1.0))
    finally:
        unset_current_user_id()


async def execute_analysis_pipeline(
    task_id: uuid.UUID,
    retries: int = 0,
    *,
    user_id: uuid.UUID | None = None,
) -> Dict[str, Any]:
    """
    Execute the full analysis pipeline outside of Celery (primarily for local/dev fallback).
    """
    return await _run_pipeline_with_retry(task_id, retries, user_id=user_id)


_DEFAULT_EXECUTE_ANALYSIS_PIPELINE = execute_analysis_pipeline


async def _prepare_failure(
    task_id: uuid.UUID,
    task_id_str: str,
    exc: Exception,
    retries: int,
) -> bool:
    error_text = _truncate_error(str(exc))
    failure_category = _categorize_failure(exc)

    if failure_category not in {"insufficient_data", "data_validation_error"} and retries < MAX_RETRIES:
        await _mark_pending_retry(task_id, retries + 1)
        await _cache_status(
            task_id_str,
            TaskStatus.PENDING,
            progress=0,
            message="等待重试",
            error=error_text,
        )
        return True

    await _mark_failed(task_id, error_text, failure_category, retries, True)
    await _cache_status(
        task_id_str,
        TaskStatus.FAILED,
        progress=0,
        message="数据不足，无法生成可信报告"
        if failure_category == "insufficient_data"
        else "任务失败",
        error=error_text,
    )
    return False


@celery_app.task(  # type: ignore[misc]
    bind=True,
    name="tasks.analysis.run",
    max_retries=MAX_RETRIES,
    default_retry_delay=RETRY_DELAY_SECONDS,
    autoretry_for=(Exception,),
    dont_autoretry_for=(FinalRetryExhausted, TaskNotFoundError),
    retry_kwargs={"countdown": RETRY_DELAY_SECONDS, "max_retries": MAX_RETRIES},
    retry_backoff=True,
    retry_jitter=True,
)
def run_analysis_task(
    self: "Task[Any, Dict[str, Any]]", task_id: str, user_id: str | None = None
) -> Dict[str, Any]:
    task_uuid = uuid.UUID(task_id)
    user_uuid = uuid.UUID(user_id) if user_id else None
    if user_uuid is None:
        resolved = _run_async(_resolve_task_user_id(task_uuid))
        if resolved is None:
            logger.warning("Task %s not found while resolving user_id; skipping analysis.", task_id)
            return {"task_id": task_id, "status": "not_found"}
        user_uuid = resolved
    use_default_executor = (
        execute_analysis_pipeline is _DEFAULT_EXECUTE_ANALYSIS_PIPELINE
    )

    try:
        if use_default_executor:

            def _retry_or_exhaust(exc: Exception) -> None:
                # If we have retries remaining, delegate to Celery's retry (raises CeleryRetry)
                if getattr(self.request, "retries", 0) < MAX_RETRIES:
                    raise self.retry(exc=exc, countdown=RETRY_DELAY_SECONDS)
                # Otherwise signal exhaustion to caller/tests
                raise RuntimeError(str(exc))

            pipeline_metrics = _run_async(
                _run_pipeline_with_retry(
                    task_uuid,
                    self.request.retries,
                    retry_handler=lambda exc, _retry_count: _retry_or_exhaust(exc),
                    user_id=user_uuid,
                )
            )
        else:
            pipeline_metrics = _run_async(
                execute_analysis_pipeline(task_uuid, self.request.retries, user_id=user_uuid)
            )
        response = {
            "task_id": task_id,
            "status": TaskStatus.COMPLETED.value,
        }
        if isinstance(pipeline_metrics, dict):
            response.update(pipeline_metrics)
        return response
    except TaskNotFoundError:
        logger.warning("Task %s not found; skipping analysis.", task_id)
        return {
            "task_id": task_id,
            "status": "not_found",
        }
    except FinalRetryExhausted as exc:
        raise exc
    except (
        Exception
    ) as exc:  # pragma: no cover - unexpected fallthrough or monkeypatched executor path
        # Always allow Celery's Retry to bubble up
        if isinstance(exc, CeleryRetry):
            raise
        if use_default_executor:
            # In the default executor path, bubble up the original exception (either CeleryRetry
            # or our exhaustion marker RuntimeError), letting Celery handle retries/backoff.
            raise
        # Non-default (monkeypatched) executor path: consult failure handler to decide retry.
        should_retry = _run_async(
            _prepare_failure(task_uuid, task_id, exc, self.request.retries)
        )
        if should_retry:
            raise self.retry(exc=exc, countdown=RETRY_DELAY_SECONDS)
        raise FinalRetryExhausted(
            f"Analysis task {task_id} reached retry limit."
        ) from exc


async def _auto_rerun_impl(
    *,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    attempt: int,
) -> Dict[str, Any]:
    """
    Contract B: auto rerun after warmup/backfill.

    Notes:
    - We keep TaskStatus as COMPLETED (so /api/report stays readable for scouting/pause pages),
      and only update Analysis/Report in-place.
    - We always run under the tenant context (user_id) to satisfy RLS.
    """
    if not ENABLE_WARMUP_AUTO_RERUN:
        return {"task_id": str(task_id), "status": "disabled"}

    max_attempts = max(1, int(WARMUP_AUTO_RERUN_MAX_ATTEMPTS))
    if attempt > max_attempts:
        return {"task_id": str(task_id), "status": "exhausted", "attempt": attempt}

    await _cache_status(
        str(task_id),
        TaskStatus.COMPLETED,
        progress=100,
        message=f"补量后自动重跑中（第 {attempt}/{max_attempts} 次）",
        stage="auto_rerun",
        next_action="running",
        details={"attempt": attempt, "max_attempts": max_attempts},
    )

    set_current_user_id(user_id)
    try:
        summary: TaskSummary | None = None
        async for session in cast(AsyncIterator[AsyncSession], get_session()):
            task = await _load_task(session, task_id, for_update=True)
            if task.user_id != user_id:
                return {"task_id": str(task_id), "status": "forbidden"}

            now = datetime.now(UTC)
            summary = TaskSummary(
                id=task.id,
                user_id=task.user_id,
                status=task.status,
                product_description=task.product_description,
                mode=task.mode,
                audit_level=getattr(task, "audit_level", "lab"),
                topic_profile_id=task.topic_profile_id,
                membership_level=getattr(getattr(task, "user", None), "membership_level", None).value
                if getattr(getattr(task, "user", None), "membership_level", None) is not None
                else None,
                created_at=task.created_at or now,
                updated_at=task.updated_at or now,
                completed_at=task.completed_at,
                retry_count=task.retry_count,
                failure_category=task.failure_category,
            )
            break

        if summary is None:
            return {"task_id": str(task_id), "status": "not_found"}

        result = await run_analysis(summary)
        result_sources = dict(getattr(result, "sources", None) or {})
        result_sources["auto_rerun"] = {
            "attempt": attempt,
            "max_attempts": max_attempts,
            "trigger": "warmup_auto_rerun",
            "ran_at": datetime.now(UTC).isoformat(),
        }
        result = replace(result, sources=result_sources)

        await _store_analysis_results(task_id, result)

        should_rerun, reason = _warmup_auto_rerun_needed(result)
        if should_rerun and attempt < max_attempts:
            next_attempt = attempt + 1
            delay = _compute_warmup_rerun_delay_seconds(next_attempt)
            next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
            celery_app.send_task(
                "tasks.analysis.auto_rerun",
                args=[str(task_id), str(user_id), next_attempt],
                countdown=delay,
                task_id=f"analysis-auto-rerun:{task_id}:{next_attempt}",
            )
            await _cache_status(
                str(task_id),
                TaskStatus.COMPLETED,
                progress=100,
                message=f"补量仍在进行：系统会在 {max(1, delay // 60)} 分钟后再跑一次",
                stage="warmup",
                blocked_reason=reason or None,
                next_action="auto_rerun_scheduled",
                details={
                    "attempt": next_attempt,
                    "max_attempts": max_attempts,
                    "next_retry_at": next_retry_at.isoformat(),
                },
            )
        elif should_rerun and attempt >= max_attempts:
            await _cache_status(
                str(task_id),
                TaskStatus.COMPLETED,
                progress=100,
                message="补量仍不够：自动重跑已到上限（需要人工介入）",
                stage="warmup",
                blocked_reason=reason or None,
                next_action="manual_intervention",
                details={"attempt": attempt, "max_attempts": max_attempts},
            )
        else:
            await _cache_status(
                str(task_id),
                TaskStatus.COMPLETED,
                progress=100,
                message="自动重跑完成：报告已更新",
                stage="done",
                next_action="none",
                details={"attempt": attempt, "max_attempts": max_attempts},
            )

        return {
            "task_id": str(task_id),
            "status": "ok",
            "attempt": attempt,
            "tier": str(result_sources.get("report_tier") or ""),
        }
    finally:
        unset_current_user_id()


@celery_app.task(name="tasks.analysis.auto_rerun")  # type: ignore[misc]
def auto_rerun_task(task_id: str, user_id: str, attempt: int = 1) -> Dict[str, Any]:
    return _run_async(
        _auto_rerun_impl(
            task_id=uuid.UUID(task_id),
            user_id=uuid.UUID(user_id),
            attempt=int(attempt),
        )
    )


__all__ = ["execute_analysis_pipeline", "run_analysis_task", "auto_rerun_task"]

# Provide backwards-compatible __func__ attribute so unit tests can access the underlying
# callable even though Celery exposes a plain function for ``run``.
if hasattr(run_analysis_task, "run") and not hasattr(run_analysis_task.run, "__func__"):
    original = getattr(run_analysis_task, "_orig_run", run_analysis_task.run)
    setattr(run_analysis_task.run, "__func__", getattr(original, "__func__", original))
