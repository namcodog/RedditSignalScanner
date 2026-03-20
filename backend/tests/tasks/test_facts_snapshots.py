from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.facts_run_log import FactsRunLog
from app.models.facts_snapshot import FactsSnapshot
from app.models.insight import Evidence, InsightCard
from app.models.task import Task
from app.models.user import User
from app.services.analysis.analysis_engine import AnalysisResult


pytestmark = pytest.mark.asyncio


def _analysis_sources(
    *,
    facts_v2_quality: dict[str, object],
    report_tier: str,
    facts_v2_package: dict[str, object] | None = None,
    communities: list[str] | None = None,
    posts_analyzed: int = 1,
    comments_analyzed: int = 0,
) -> dict[str, object]:
    data_lineage = (
        dict(facts_v2_package.get("data_lineage") or {})
        if isinstance(facts_v2_package, dict)
        else {}
    )
    data_lineage.setdefault("source_range", {"posts": posts_analyzed, "comments": comments_analyzed})
    data_lineage.setdefault("crawler_run_ids", [])
    data_lineage.setdefault("target_ids", [])
    return {
        "communities": communities or ["r/test"],
        "posts_analyzed": posts_analyzed,
        "comments_analyzed": comments_analyzed,
        "counts_analyzed": {"posts": posts_analyzed, "comments": comments_analyzed},
        "counts_db": {
            "posts_current": posts_analyzed,
            "comments_total": comments_analyzed,
            "comments_eligible": comments_analyzed,
        },
        "comments_pipeline_status": "ok" if comments_analyzed > 0 else "disabled",
        "data_lineage": data_lineage,
        "cache_hit_rate": 1.0,
        "analysis_duration_seconds": 1,
        "reddit_api_calls": 0,
        "data_source": "synthetic",
        "facts_v2_quality": facts_v2_quality,
        "report_tier": report_tier,
        **({"facts_v2_package": facts_v2_package} if facts_v2_package is not None else {}),
    }


async def test_analysis_pipeline_persists_facts_snapshot(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    大白话：跑完一次分析，必须把 facts_v2 审计包落库一份，方便追溯/复现。
    """

    user = User(
        email=f"facts-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("SecurePass123!"),
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="Test product description long enough.",
        mode="market_insight",
        audit_level="gold",
    )
    db_session.add(task)
    await db_session.commit()

    from app.tasks import analysis_task as analysis_task_module

    class _NoopStatusCache:
        async def set_status(self, payload: object, ttl_seconds: int = 3600) -> None:
            return None

    monkeypatch.setattr(analysis_task_module, "STATUS_CACHE", _NoopStatusCache())

    async def stub_run_analysis(_summary) -> AnalysisResult:
        facts_v2_package = {
            "schema_version": "2.0",
            "meta": {
                "topic": "test-topic",
                "topic_profile_id": "tp_test",
                "report_id": str(task.id),
                "snapshot_id": "snap_test",
            },
            "data_lineage": {"source_range": {"posts": 1, "comments": 0}},
            "aggregates": {
                "communities": [{"name": "r/test", "posts": 1, "comments": 0}],
            },
            "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
            "sample_posts_db": [{"title": "hello world", "text": "hello world"}],
            "sample_comments_db": [],
        }
        facts_v2_quality = {
            "passed": True,
            "tier": "A_full",
            "flags": [],
            "metrics": {"on_topic_ratio": 1.0},
        }
        return AnalysisResult(
            insights={
                "pain_points": [
                    {
                        "description": "Onboarding takes too long and users drop off.",
                        "frequency": 42,
                        "sentiment_score": -0.3,
                        "severity": "high",
                        "example_posts": [
                            {
                                "community": "r/test",
                                "content": "Onboarding is confusing.",
                                "upvotes": 123,
                                "url": "https://www.reddit.com/r/test/comments/abc123/test/",
                                "author": "test_user",
                                "permalink": "/r/test/comments/abc123/test/",
                                "duplicate_ids": [],
                                "evidence_count": 1,
                            }
                        ],
                        "user_examples": ["Onboarding feels like homework."],
                    }
                ],
                "competitors": [],
                "opportunities": [],
            },
            sources=_analysis_sources(
                facts_v2_package=facts_v2_package,
                facts_v2_quality=facts_v2_quality,
                report_tier="A_full",
            ),
            report_html="<html><body>stub report</body></html>",
            action_items=[],
            confidence_score=0.9,
        )

    monkeypatch.setattr(analysis_task_module, "run_analysis", stub_run_analysis)

    await analysis_task_module.execute_analysis_pipeline(task.id)

    result = await db_session.execute(
        select(FactsSnapshot).where(FactsSnapshot.task_id == task.id)
    )
    snapshot = result.scalars().one()
    assert snapshot.passed is True
    assert snapshot.tier == "A_full"
    assert snapshot.schema_version == "2.0"
    assert snapshot.v2_package.get("schema_version") == "2.0"


async def test_gold_task_persists_snapshot_without_package(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(
        email=f"facts-gold-nopkg-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("SecurePass123!"),
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="Gold task should still persist a snapshot.",
        mode="market_insight",
        audit_level="gold",
    )
    db_session.add(task)
    await db_session.commit()

    from app.tasks import analysis_task as analysis_task_module

    class _NoopStatusCache:
        async def set_status(self, payload: object, ttl_seconds: int = 3600) -> None:
            return None

    monkeypatch.setattr(analysis_task_module, "STATUS_CACHE", _NoopStatusCache())

    async def stub_run_analysis(_summary) -> AnalysisResult:
        return AnalysisResult(
            insights={"pain_points": [], "competitors": [], "opportunities": []},
            sources=_analysis_sources(
                facts_v2_quality={"passed": True, "tier": "C_scouting", "flags": []},
                report_tier="C_scouting",
                posts_analyzed=0,
            ),
            report_html="<html><body>stub report</body></html>",
            action_items=[],
            confidence_score=0.5,
        )

    monkeypatch.setattr(analysis_task_module, "run_analysis", stub_run_analysis)

    await analysis_task_module.execute_analysis_pipeline(task.id)

    result = await db_session.execute(
        select(FactsSnapshot).where(FactsSnapshot.task_id == task.id)
    )
    snapshot = result.scalars().one()
    assert snapshot.audit_level == "gold"
    assert snapshot.schema_version == "2.0"
    assert snapshot.v2_package.get("schema_version") == "2.0"


async def test_analysis_pipeline_persists_only_real_insight_evidence(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(
        email=f"facts-real-evidence-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("SecurePass123!"),
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="Task with real evidence should persist insight cards.",
        mode="market_insight",
        audit_level="gold",
    )
    db_session.add(task)
    await db_session.commit()

    from app.tasks import analysis_task as analysis_task_module

    class _NoopStatusCache:
        async def set_status(self, payload: object, ttl_seconds: int = 3600) -> None:
            return None

    monkeypatch.setattr(analysis_task_module, "STATUS_CACHE", _NoopStatusCache())

    async def stub_run_analysis(_summary) -> AnalysisResult:
        facts_v2_package = {
            "schema_version": "2.0",
            "meta": {"topic": "real-evidence-topic"},
            "data_lineage": {"source_range": {"posts": 1, "comments": 0}},
            "aggregates": {"communities": [{"name": "r/test", "posts": 1, "comments": 0}]},
            "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
            "sample_posts_db": [{"title": "hello world", "text": "hello world"}],
            "sample_comments_db": [],
        }
        return AnalysisResult(
            insights={
                "pain_points": [
                    {
                        "description": "Checkout is confusing.",
                        "summary": "Checkout keeps confusing buyers.",
                        "confidence": 0.8,
                        "example_posts": [
                            {
                                "community": "r/test",
                                "content": "Checkout is confusing for first-time buyers.",
                                "url": "https://www.reddit.com/r/test/comments/abc123/test/",
                                "permalink": "/r/test/comments/abc123/test/",
                                "upvotes": 50,
                            }
                        ],
                    }
                ],
                "competitors": [],
                "opportunities": [],
            },
            sources=_analysis_sources(
                facts_v2_package=facts_v2_package,
                facts_v2_quality={"passed": True, "tier": "A_full", "flags": []},
                report_tier="A_full",
            ),
            report_html="<html><body>stub report</body></html>",
            action_items=[],
            confidence_score=0.8,
        )

    monkeypatch.setattr(analysis_task_module, "run_analysis", stub_run_analysis)

    await analysis_task_module.execute_analysis_pipeline(task.id)

    card_result = await db_session.execute(select(InsightCard).where(InsightCard.task_id == task.id))
    cards = card_result.scalars().all()
    assert len(cards) == 1

    evidence_result = await db_session.execute(
        select(Evidence).where(Evidence.insight_card_id == cards[0].id)
    )
    evidences = evidence_result.scalars().all()
    assert len(evidences) == 1
    assert evidences[0].post_url.endswith("/abc123/test/")


async def test_analysis_pipeline_clears_old_cards_and_skips_synthetic_only_entries(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(
        email=f"facts-synthetic-skip-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("SecurePass123!"),
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="Synthetic-only fallback should not persist cards.",
        mode="market_insight",
        audit_level="gold",
    )
    db_session.add(task)
    await db_session.flush()

    stale_card = InsightCard(
        task_id=task.id,
        title="Old synthetic card",
        summary="Should be removed on rerun.",
        confidence=0.5,
        time_window_days=30,
        subreddits=["r/test"],
    )
    db_session.add(stale_card)
    await db_session.flush()
    db_session.add(
        Evidence(
            insight_card_id=stale_card.id,
            post_url="https://www.reddit.com/r/test/comments/stale/",
            excerpt="old stale evidence",
            timestamp=datetime.now(timezone.utc),
            subreddit="r/test",
            score=0.0,
        )
    )
    await db_session.commit()

    from app.tasks import analysis_task as analysis_task_module

    class _NoopStatusCache:
        async def set_status(self, payload: object, ttl_seconds: int = 3600) -> None:
            return None

    monkeypatch.setattr(analysis_task_module, "STATUS_CACHE", _NoopStatusCache())

    async def stub_run_analysis(_summary) -> AnalysisResult:
        facts_v2_package = {
            "schema_version": "2.0",
            "meta": {"topic": "synthetic-only-topic"},
            "data_lineage": {"source_range": {"posts": 1, "comments": 0}},
            "aggregates": {"communities": [{"name": "r/test", "posts": 1, "comments": 0}]},
            "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
            "sample_posts_db": [{"title": "hello world", "text": "hello world"}],
            "sample_comments_db": [],
        }
        return AnalysisResult(
            insights={
                "pain_points": [
                    {
                        "description": "Need a better onboarding flow.",
                        "user_examples": ["Onboarding feels like homework."],
                    }
                ],
                "competitors": [],
                "opportunities": [],
            },
            sources=_analysis_sources(
                facts_v2_package=facts_v2_package,
                facts_v2_quality={"passed": True, "tier": "A_full", "flags": []},
                report_tier="A_full",
            ),
            report_html="<html><body>stub report</body></html>",
            action_items=[
                {
                    "problem_definition": "Improve onboarding",
                    "communities": ["r/test"],
                    "evidence_chain": [],
                }
            ],
            confidence_score=0.6,
        )

    monkeypatch.setattr(analysis_task_module, "run_analysis", stub_run_analysis)

    await analysis_task_module.execute_analysis_pipeline(task.id)

    card_result = await db_session.execute(select(InsightCard).where(InsightCard.task_id == task.id))
    assert card_result.scalars().all() == []


async def test_facts_snapshot_persists_audit_metadata(
    db_session: AsyncSession,
) -> None:
    user = User(
        email=f"facts-meta-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("SecurePass123!"),
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="Another test product description long enough.",
        mode="market_insight",
        audit_level="gold",
    )
    db_session.add(task)
    await db_session.flush()

    expires_at = datetime.now(timezone.utc) + timedelta(days=90)
    snapshot = FactsSnapshot(
        task_id=task.id,
        schema_version="2.0",
        v2_package={"schema_version": "2.0"},
        quality={"tier": "X_blocked", "flags": ["topic_mismatch"]},
        passed=False,
        tier="X_blocked",
        audit_level="gold",
        status="blocked",
        validator_level="error",
        retention_days=90,
        expires_at=expires_at,
        blocked_reason="quality_gate_blocked",
        error_code="facts_v2_missing_quotes",
    )
    db_session.add(snapshot)
    await db_session.commit()

    result = await db_session.execute(
        select(FactsSnapshot).where(FactsSnapshot.id == snapshot.id)
    )
    stored = result.scalars().one()
    assert stored.audit_level == "gold"
    assert stored.status == "blocked"
    assert stored.validator_level == "error"
    assert stored.retention_days == 90
    assert stored.expires_at is not None
    assert stored.blocked_reason == "quality_gate_blocked"
    assert stored.error_code == "facts_v2_missing_quotes"


async def test_facts_run_log_persists_minimum_fields(
    db_session: AsyncSession,
) -> None:
    user = User(
        email=f"facts-log-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("SecurePass123!"),
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="Noise task for minimal run log.",
        mode="market_insight",
        audit_level="noise",
    )
    db_session.add(task)
    await db_session.flush()

    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    log = FactsRunLog(
        task_id=task.id,
        audit_level="noise",
        status="skipped",
        validator_level="info",
        retention_days=7,
        expires_at=expires_at,
        summary={
            "posts_fetched": 0,
            "comments_fetched": 0,
            "posts_kept": 0,
            "comments_kept": 0,
            "config_hash": "noop",
        },
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(FactsRunLog).where(FactsRunLog.id == log.id)
    )
    stored = result.scalars().one()
    assert stored.audit_level == "noise"
    assert stored.status == "skipped"
    assert stored.validator_level == "info"
    assert stored.retention_days == 7
    assert stored.expires_at is not None


async def test_lab_task_skips_snapshot_when_not_sampled(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(
        email=f"facts-lab-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("SecurePass123!"),
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="Lab task should skip full snapshot when not sampled.",
        mode="market_insight",
        audit_level="lab",
    )
    db_session.add(task)
    await db_session.commit()

    from app.tasks import analysis_task as analysis_task_module

    class _NoopStatusCache:
        async def set_status(self, payload: object, ttl_seconds: int = 3600) -> None:
            return None

    monkeypatch.setattr(analysis_task_module, "STATUS_CACHE", _NoopStatusCache())
    monkeypatch.setattr(
        analysis_task_module, "_should_sample_lab_snapshot", lambda _task_id: False
    )

    async def stub_run_analysis(_summary) -> AnalysisResult:
        facts_v2_package = {
            "schema_version": "2.0",
            "meta": {"topic": "lab-topic", "topic_profile_id": "tp_lab"},
            "data_lineage": {"source_range": {"posts": 1, "comments": 0}},
            "aggregates": {"communities": [{"name": "r/test", "posts": 1, "comments": 0}]},
            "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
            "sample_posts_db": [{"title": "hello world", "text": "hello world"}],
            "sample_comments_db": [],
        }
        facts_v2_quality = {
            "passed": True,
            "tier": "A_full",
            "flags": [],
            "metrics": {"on_topic_ratio": 1.0},
        }
        return AnalysisResult(
            insights={"pain_points": [], "competitors": [], "opportunities": []},
            sources=_analysis_sources(
                facts_v2_package=facts_v2_package,
                facts_v2_quality=facts_v2_quality,
                report_tier="A_full",
            ),
            report_html="<html><body>stub report</body></html>",
            action_items=[],
            confidence_score=0.9,
        )

    monkeypatch.setattr(analysis_task_module, "run_analysis", stub_run_analysis)

    await analysis_task_module.execute_analysis_pipeline(task.id)

    snapshot_result = await db_session.execute(
        select(FactsSnapshot).where(FactsSnapshot.task_id == task.id)
    )
    assert snapshot_result.scalars().first() is None

    log_result = await db_session.execute(
        select(FactsRunLog).where(FactsRunLog.task_id == task.id)
    )
    log = log_result.scalars().one()
    assert log.audit_level == "lab"
    assert log.status == "ok"


async def test_lab_task_stores_snapshot_on_warn(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(
        email=f"facts-lab-warn-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("SecurePass123!"),
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="Lab task should store snapshot on warn.",
        mode="market_insight",
        audit_level="lab",
    )
    db_session.add(task)
    await db_session.commit()

    from app.tasks import analysis_task as analysis_task_module

    class _NoopStatusCache:
        async def set_status(self, payload: object, ttl_seconds: int = 3600) -> None:
            return None

    monkeypatch.setattr(analysis_task_module, "STATUS_CACHE", _NoopStatusCache())
    monkeypatch.setattr(
        analysis_task_module, "_should_sample_lab_snapshot", lambda _task_id: False
    )

    async def stub_run_analysis(_summary) -> AnalysisResult:
        facts_v2_package = {
            "schema_version": "2.0",
            "meta": {"topic": "lab-topic", "topic_profile_id": "tp_lab"},
            "data_lineage": {"source_range": {"posts": 1, "comments": 0}},
            "aggregates": {"communities": [{"name": "r/test", "posts": 1, "comments": 0}]},
            "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
            "sample_posts_db": [{"title": "hello world", "text": "hello world"}],
            "sample_comments_db": [],
        }
        facts_v2_quality = {
            "passed": True,
            "tier": "B_trimmed",
            "flags": ["pains_low"],
            "metrics": {"on_topic_ratio": 0.6},
        }
        return AnalysisResult(
            insights={"pain_points": [], "competitors": [], "opportunities": []},
            sources=_analysis_sources(
                facts_v2_package=facts_v2_package,
                facts_v2_quality=facts_v2_quality,
                report_tier="B_trimmed",
            ),
            report_html="<html><body>stub report</body></html>",
            action_items=[],
            confidence_score=0.9,
        )

    monkeypatch.setattr(analysis_task_module, "run_analysis", stub_run_analysis)

    await analysis_task_module.execute_analysis_pipeline(task.id)

    snapshot_result = await db_session.execute(
        select(FactsSnapshot).where(FactsSnapshot.task_id == task.id)
    )
    snapshot = snapshot_result.scalars().one()
    assert snapshot.audit_level == "lab"
    assert snapshot.status == "ok"
    assert snapshot.validator_level in {"warn", "error"}


async def test_noise_task_writes_run_log_only(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = User(
        email=f"facts-noise-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("SecurePass123!"),
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        user_id=user.id,
        product_description="Noise task should only write a run log.",
        mode="market_insight",
        audit_level="noise",
    )
    db_session.add(task)
    await db_session.commit()

    from app.tasks import analysis_task as analysis_task_module

    class _NoopStatusCache:
        async def set_status(self, payload: object, ttl_seconds: int = 3600) -> None:
            return None

    monkeypatch.setattr(analysis_task_module, "STATUS_CACHE", _NoopStatusCache())

    async def stub_run_analysis(_summary) -> AnalysisResult:
        facts_v2_package = {
            "schema_version": "2.0",
            "meta": {"topic": "noise-topic"},
            "data_lineage": {"source_range": {"posts": 1, "comments": 0}},
            "aggregates": {"communities": [{"name": "r/test", "posts": 1, "comments": 0}]},
            "business_signals": {"high_value_pains": [], "brand_pain": [], "solutions": []},
            "sample_posts_db": [{"title": "hello world", "text": "hello world"}],
            "sample_comments_db": [],
        }
        return AnalysisResult(
            insights={"pain_points": [], "competitors": [], "opportunities": []},
            sources=_analysis_sources(
                facts_v2_package=facts_v2_package,
                facts_v2_quality={"passed": True, "tier": "A_full", "flags": []},
                report_tier="A_full",
            ),
            report_html="<html><body>stub report</body></html>",
            action_items=[],
            confidence_score=0.8,
        )

    monkeypatch.setattr(analysis_task_module, "run_analysis", stub_run_analysis)

    await analysis_task_module.execute_analysis_pipeline(task.id)

    snapshot_result = await db_session.execute(
        select(FactsSnapshot).where(FactsSnapshot.task_id == task.id)
    )
    assert snapshot_result.scalars().first() is None

    log_result = await db_session.execute(
        select(FactsRunLog).where(FactsRunLog.task_id == task.id)
    )
    log = log_result.scalars().one()
    assert log.audit_level == "noise"
    assert log.status == "ok"
