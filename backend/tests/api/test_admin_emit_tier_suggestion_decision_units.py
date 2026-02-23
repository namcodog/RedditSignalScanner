from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.main import app
from app.models.tier_suggestion import TierSuggestion


def _override_admin_settings(admin_email: str) -> Settings:
    base = get_settings()
    return base.model_copy(update={"admin_emails_raw": admin_email})


@pytest.mark.asyncio
async def test_admin_can_emit_tier_suggestions_as_decision_units(
    client: AsyncClient,
    token_factory,
    db_session: AsyncSession,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = _override_admin_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        admin_token, admin_user_id = await token_factory(email=admin_email)
        headers = {"Authorization": f"Bearer {admin_token}"}

        now = datetime.now(timezone.utc)
        community = f"r/test_admin_{uuid.uuid4().hex[:8]}"

        community_id = (
            await db_session.execute(
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

        await db_session.execute(
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
                "title": "Admin emit evidence post",
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
        db_session.add(suggestion)
        await db_session.commit()
        await db_session.refresh(suggestion)

        resp = await client.post(
            "/api/admin/communities/tier-suggestions/emit-decision-units",
            headers=headers,
            json={"suggestion_ids": [suggestion.id], "lookback_days": 30, "max_evidence_posts": 2},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["code"] == 0
        assert payload["data"]["created_units"] == 1
        assert payload["data"]["created_evidences"] >= 1

        # admin should be able to see the emitted decision unit from the main contract API
        resp_list = await client.get(
            "/api/decision-units",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp_list.status_code == 200
        items = resp_list.json()["items"]
        assert any(
            item.get("signal_type") == "ops"
            and item.get("du_payload", {}).get("lineage", {}).get("source") == "tier_suggestions"
            for item in items
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)

