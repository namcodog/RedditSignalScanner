from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.models.business_category import BusinessCategory
from app.models.community_domain_membership import CommunityDomainMembership
from app.models.community_governance_decision import CommunityGovernanceDecision
from app.models.community_registry import CommunityRegistry
from app.models.community_runtime_state import CommunityRuntimeState
from app.services.llm.comment_label_planner import (
    _fetch_activation_prefilter_stats,
    _fetch_effective_domain_weights,
)


@pytest.mark.asyncio
async def test_effective_domain_weights_read_truth_source_only() -> None:
    async with SessionFactory() as db:
        await db.execute(
            text(
                "TRUNCATE TABLE "
                "community_governance_decision, "
                "community_domain_membership, "
                "community_runtime_state, "
                "community_registry, "
                "business_categories "
                "RESTART IDENTITY CASCADE"
            )
        )
        await db.commit()

        db.add(
            BusinessCategory(
                key="AI_Workflow",
                display_name="AI Workflow",
                description="AI workflow",
                is_active=True,
            )
        )
        enabled = CommunityRegistry(
            platform="reddit",
            community_name="r/aitools",
            source_of_truth="registry",
            is_enabled=True,
        )
        disabled = CommunityRegistry(
            platform="reddit",
            community_name="r/orphanpool",
            source_of_truth="registry",
            is_enabled=False,
        )
        db.add_all([enabled, disabled])
        await db.flush()
        db.add_all(
            [
                CommunityRuntimeState(
                    community_id=enabled.id,
                    crawl_status="active",
                    crawl_priority=50,
                    is_enabled=True,
                    runtime_notes={},
                ),
                CommunityRuntimeState(
                    community_id=disabled.id,
                    crawl_status="active",
                    crawl_priority=50,
                    is_enabled=False,
                    runtime_notes={},
                ),
            ]
        )
        enabled_membership = CommunityDomainMembership(
            community_id=enabled.id,
            domain_key="AI_Workflow",
            membership_source="manual",
            is_primary=True,
            is_current=True,
            evidence={},
        )
        disabled_membership = CommunityDomainMembership(
            community_id=disabled.id,
            domain_key="AI_Workflow",
            membership_source="manual",
            is_primary=True,
            is_current=True,
            evidence={},
        )
        db.add_all([enabled_membership, disabled_membership])
        await db.flush()
        db.add_all(
            [
                CommunityGovernanceDecision(
                    membership_id=enabled_membership.id,
                    decision="approved",
                    decided_at=datetime.now(timezone.utc),
                    is_current=True,
                    evidence={},
                ),
                CommunityGovernanceDecision(
                    membership_id=disabled_membership.id,
                    decision="approved",
                    decided_at=datetime.now(timezone.utc),
                    is_current=True,
                    evidence={},
                ),
            ]
        )
        await db.commit()

    weights = await _fetch_effective_domain_weights()

    assert weights == {"AI_Workflow": 1}


@pytest.mark.asyncio
async def test_activation_prefilter_stats_ignore_non_truth_source_comments() -> None:
    now = datetime.now(timezone.utc)
    async with SessionFactory() as db:
        await db.execute(
            text(
                "TRUNCATE TABLE "
                "comment_llm_labels, "
                "comments, "
                "authors, "
                "community_pool, "
                "posts_raw, "
                "community_governance_decision, "
                "community_domain_membership, "
                "community_runtime_state, "
                "community_registry, "
                "business_categories "
                "RESTART IDENTITY CASCADE"
            )
        )
        await db.commit()

        db.add(
            BusinessCategory(
                key="AI_Workflow",
                display_name="AI Workflow",
                description="AI workflow",
                is_active=True,
            )
        )
        registry = CommunityRegistry(
            platform="reddit",
            community_name="r/aitools",
            source_of_truth="registry",
            is_enabled=True,
        )
        db.add(registry)
        await db.flush()
        db.add(
            CommunityRuntimeState(
                community_id=registry.id,
                crawl_status="active",
                crawl_priority=50,
                is_enabled=True,
                runtime_notes={},
            )
        )
        membership = CommunityDomainMembership(
            community_id=registry.id,
            domain_key="AI_Workflow",
            membership_source="manual",
            is_primary=True,
            is_current=True,
            evidence={},
        )
        db.add(membership)
        await db.flush()
        db.add(
            CommunityGovernanceDecision(
                membership_id=membership.id,
                decision="approved",
                decided_at=now,
                is_current=True,
                evidence={},
            )
        )
        await db.execute(
            text(
                """
                INSERT INTO community_pool (
                    name,
                    tier,
                    categories,
                    description_keywords,
                    semantic_quality_score,
                    priority,
                    is_active,
                    is_blacklisted,
                    created_at,
                    updated_at
                )
                VALUES
                    ('r/aitools', 'silver', '{"topic":["ai"]}'::jsonb, '{"keywords":["ai"]}'::jsonb, 0.50, 'medium', true, false, :pool_ts, :pool_ts),
                    ('r/orphanpool', 'silver', '{"topic":["ai"]}'::jsonb, '{"keywords":["ai"]}'::jsonb, 0.50, 'medium', true, false, :pool_ts, :pool_ts)
                """
            ),
            {"pool_ts": now},
        )
        pool_rows = await db.execute(
            text(
                """
                SELECT id, name
                FROM community_pool
                WHERE name IN ('r/aitools', 'r/orphanpool')
                """
            )
        )
        pool_ids = {row.name: row.id for row in pool_rows}
        await db.execute(
            text(
                """
                INSERT INTO authors (author_id, author_name)
                VALUES ('test_auth', 'Test User')
                """
            )
        )
        await db.execute(
            text(
                """
                INSERT INTO posts_raw (
                    source,
                    source_post_id,
                    version,
                    created_at,
                    fetched_at,
                    valid_from,
                    is_current,
                    title,
                    subreddit,
                    community_id,
                    author_id
                )
                VALUES
                    ('reddit', 'p1', 1, :ts1, :ts1, :ts1, true, 'Need help choosing an AI workflow tool', 'r/aitools', :pool1_id, 'test_auth'),
                    ('reddit', 'p2', 1, :ts2, :ts2, :ts2, true, 'Need help choosing an AI workflow tool', 'r/aitools', :pool1_id, 'test_auth'),
                    ('reddit', 'p3', 1, :ts3, :ts3, :ts3, true, 'Need help choosing an AI workflow tool', 'r/orphanpool', :pool2_id, 'test_auth')
                """
            ),
            {
                "ts1": now - timedelta(days=1),
                "ts2": now - timedelta(days=1),
                "ts3": now - timedelta(days=1),
                "pool1_id": pool_ids["r/aitools"],
                "pool2_id": pool_ids["r/orphanpool"],
            },
        )
        post_rows = await db.execute(
            text(
                """
                SELECT source_post_id, id
                FROM posts_raw
                WHERE source = 'reddit'
                  AND source_post_id IN ('p1', 'p2', 'p3')
                """
            )
        )
        post_ids = {row.source_post_id: row.id for row in post_rows}
        await db.execute(
            text(
                """
                INSERT INTO comments (
                    reddit_comment_id,
                    post_id,
                    source,
                    source_post_id,
                    subreddit,
                    depth,
                    body,
                    created_utc,
                    score,
                    permalink
                )
                VALUES
                    (:id1, :post1_id, 'reddit', 'p1', 'r/aitools', 0, :body1, :created1, 10, 'https://reddit.com/r/aitools/comments/p1/c_truth_long'),
                    (:id2, :post2_id, 'reddit', 'p2', 'r/aitools', 0, :body2, :created2, 5, 'https://reddit.com/r/aitools/comments/p2/c_truth_short'),
                    (:id3, :post3_id, 'reddit', 'p3', 'r/orphanpool', 0, :body3, :created3, 7, 'https://reddit.com/r/orphanpool/comments/p3/c_orphan_long')
                """
            ),
            {
                "id1": "c_truth_long",
                "post1_id": post_ids["p1"],
                "body1": "This workflow saves hours every week and clearly solves my problem.",
                "created1": now - timedelta(days=1),
                "id2": "c_truth_short",
                "post2_id": post_ids["p2"],
                "body2": "too short",
                "created2": now - timedelta(days=1),
                "id3": "c_orphan_long",
                "post3_id": post_ids["p3"],
                "body3": "This should never be counted because the community is not in truth source.",
                "created3": now - timedelta(days=1),
            },
        )
        await db.commit()

    stats = await _fetch_activation_prefilter_stats(lookback_days=30)

    assert stats["total_effective_unlabeled"] == 2
    assert stats["filtered_short"] == 1
    assert stats["admitted"] == 1
