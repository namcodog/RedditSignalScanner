from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import SessionFactory


@pytest.mark.asyncio
async def test_emit_tier_suggestions_as_decision_units_creates_task_units_and_evidence() -> None:
    from app.models.posts_storage import PostRaw
    from app.models.task import Task
    from app.models.tier_suggestion import TierSuggestion
    from app.models.user import MembershipLevel, User
    from app.services.ops.tier_suggestion_decision_units import (
        emit_tier_suggestions_as_decision_units,
    )

    async with SessionFactory() as session:
        await session.execute(
            text(
                """
                TRUNCATE TABLE
                    evidences,
                    insight_cards,
                    tier_suggestions,
                    tasks,
                    users,
                    posts_raw
                RESTART IDENTITY CASCADE
                """
            )
        )

        now = datetime.now(timezone.utc)
        user = User(
            email=f"ops-{uuid.uuid4().hex}@example.com",
            password_hash=hash_password("StrongPassw0rd!"),
            membership_level=MembershipLevel.PRO,
        )
        session.add(user)
        await session.flush()

        community = f"r/test_{uuid.uuid4().hex[:8]}"
        community_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO community_pool (
                        name,
                        tier,
                        categories,
                        description_keywords,
                        semantic_quality_score,
                        is_active,
                        is_blacklisted,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :name,
                        'candidate',
                        '{}'::jsonb,
                        '{}'::jsonb,
                        0.5,
                        true,
                        false,
                        :ts,
                        :ts
                    )
                    RETURNING id
                    """
                ),
                {"name": community, "ts": now},
            )
        ).scalar_one()
        await session.execute(
            text(
                """
                INSERT INTO posts_raw (
                    source, source_post_id, version, created_at,
                    fetched_at, valid_from, subreddit, title, body, is_current, url, community_id
                )
                VALUES (
                    'reddit', :pid, 1, :ts,
                    :ts, :ts, :subreddit, :title, :body, true, :url, :community_id
                )
                """
            ),
            {
                "pid": f"post_{uuid.uuid4().hex[:8]}",
                "ts": now,
                "subreddit": community,
                "title": "Sample post for tier suggestion evidence",
                "body": "Body text",
                "url": "/r/test/comments/abc123/sample/",
                "community_id": int(community_id),
            },
        )

        suggestion = TierSuggestion(
            community_name=community,
            current_tier="T3",
            suggested_tier="T2",
            confidence=0.92,
            reasons=["日均帖子数高于阈值", "痛点密度高于阈值"],
            metrics={"posts_per_day": 120.0, "pain_density": 0.4},
            priority_score=10,
            expires_at=now + timedelta(days=7),
        )
        session.add(suggestion)
        await session.commit()

        result = await emit_tier_suggestions_as_decision_units(
            session,
            user_id=user.id,
            suggestion_ids=[suggestion.id],
            emitted_at=now,
            lookback_days=30,
            max_evidence_posts=3,
        )

        assert result.created_units == 1
        assert result.task_id is not None

        task = await session.get(Task, result.task_id)
        assert task is not None
        assert task.user_id == user.id

        du_rows = (
            await session.execute(
                text(
                    """
                    SELECT id, du_payload
                    FROM decision_units_v
                    WHERE task_id = :task_id
                    """
                ),
                {"task_id": result.task_id},
            )
        ).mappings().all()
        assert len(du_rows) == 1
        assert du_rows[0]["du_payload"]["lineage"]["source"] == "tier_suggestions"

        evidence_count = int(
            (
                await session.execute(
                    text("SELECT COUNT(*) FROM evidences WHERE insight_card_id = :id"),
                    {"id": du_rows[0]["id"]},
                )
            ).scalar_one()
            or 0
        )
        assert evidence_count >= 1

        # Idempotent: emitting again should not duplicate decision units.
        result2 = await emit_tier_suggestions_as_decision_units(
            session,
            user_id=user.id,
            suggestion_ids=[suggestion.id],
            emitted_at=now,
            lookback_days=30,
            max_evidence_posts=3,
        )
        assert result2.created_units == 0
