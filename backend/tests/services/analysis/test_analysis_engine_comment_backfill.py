from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory
from app.models.task import TaskStatus
from app.schemas.task import TaskSummary
from app.services.analysis.topic_profiles import TopicProfile
from app.services.analysis import analysis_engine as analysis_engine_module


pytestmark = pytest.mark.asyncio(loop_scope="session")


def _profile() -> TopicProfile:
    return TopicProfile(
        id="shopify_ads_conversion_v1",
        topic_name="Shopify Traffic Ads Conversion",
        product_desc="desc",
        vertical="Ecommerce_Business",
        allowed_communities=["r/shopify", "r/facebookads"],
        community_patterns=[],
        required_entities_any=["Shopify"],
        soft_required_entities_any=[],
        include_keywords_any=["ROAS", "CPC"],
        exclude_keywords_any=[],
        mode="operations",
    )


@pytest.mark.asyncio
async def test_schedule_auto_comment_backfill_creates_targets_and_outbox() -> None:
    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Optimize Shopify ads conversion funnels.",
        topic_profile_id="shopify_ads_conversion_v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Two posts that claim to have comments, but DB currently has none.
    posts = [
        {
            "id": "t3_abcd12",
            "subreddit": "r/shopify",
            "title": "Shopify ROAS low",
            "summary": "ROAS dropped after campaign changes",
            "score": 100,
            "num_comments": 12,
        },
        {
            "id": "t3_efgh34",
            "subreddit": "r/facebookads",
            "title": "Meta Ads conversion tracking broken",
            "summary": "Pixel events not firing",
            "score": 50,
            "num_comments": 5,
        },
    ]

    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM task_outbox"))
        await session.execute(text("DELETE FROM crawler_run_targets"))
        await session.execute(text("DELETE FROM crawler_runs"))
        await session.execute(
            text(
                """
                DELETE FROM comments
                WHERE source = 'reddit'
                  AND source_post_id = ANY(:ids)
                """
            ),
            {"ids": [p["id"] for p in posts]},
        )
        await session.commit()

    actions = await analysis_engine_module._schedule_auto_backfill_for_missing_comments(  # type: ignore[attr-defined]
        task=task,
        topic_profile=_profile(),
        posts=posts,
    )
    assert actions, "Expected comment backfill actions when comments are missing"
    assert actions[0]["type"] == "backfill_comments"
    assert int(actions[0]["targets"] or 0) > 0
    assert isinstance(actions[0].get("target_ids"), list)
    assert actions[0].get("target_ids"), "Expected target_ids sample for lineage tracing"

    import uuid

    crawl_run_id = uuid.uuid5(uuid.NAMESPACE_URL, f"analysis_preflight_comments:{task.id}")
    async with SessionFactory() as session:
        target_count = await session.scalar(
            text(
                "SELECT COUNT(*) FROM crawler_run_targets WHERE crawl_run_id = CAST(:rid AS uuid)"
            ),
            {"rid": str(crawl_run_id)},
        )
        outbox_count = await session.scalar(
            text("SELECT COUNT(*) FROM task_outbox WHERE event_type = 'execute_target'")
        )
    assert int(target_count or 0) > 0
    assert int(outbox_count or 0) > 0

    # Returned target_ids should correspond to the created crawler_run_targets rows.
    returned_ids = [str(x) for x in actions[0].get("target_ids") or [] if str(x)]
    async with SessionFactory() as session:
        matched = await session.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM crawler_run_targets
                WHERE crawl_run_id = CAST(:rid AS uuid)
                  AND id = ANY(:ids)
                """
            ),
            {"rid": str(crawl_run_id), "ids": returned_ids},
        )
    assert int(matched or 0) == len(returned_ids)


@pytest.mark.asyncio
async def test_schedule_auto_comment_backfill_allows_unknown_num_comments() -> None:
    task = TaskSummary(
        id=uuid4(),
        status=TaskStatus.PENDING,
        product_description="Optimize Shopify ads conversion funnels.",
        topic_profile_id="shopify_ads_conversion_v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Some data sources do not populate num_comments reliably (often 0).
    # We still want to backfill comments when comments are missing, otherwise narrow topics never self-heal.
    posts = [
        {
            "id": "t3_ijkl56",
            "subreddit": "r/shopify",
            "title": "Shopify ROAS unstable",
            "summary": "ROAS swings a lot week to week",
            "score": 120,
            "num_comments": 0,
        },
        {
            "id": "t3_mnop78",
            "subreddit": "r/facebookads",
            "title": "Meta ads performance dropped",
            "summary": "Learning phase resets unexpectedly",
            "score": 80,
            "num_comments": 0,
        },
    ]

    async with SessionFactory() as session:
        await session.execute(text("DELETE FROM task_outbox"))
        await session.execute(text("DELETE FROM crawler_run_targets"))
        await session.execute(text("DELETE FROM crawler_runs"))
        await session.execute(
            text(
                """
                DELETE FROM comments
                WHERE source = 'reddit'
                  AND source_post_id = ANY(:ids)
                """
            ),
            {"ids": [p["id"] for p in posts]},
        )
        await session.commit()

    actions = await analysis_engine_module._schedule_auto_backfill_for_missing_comments(  # type: ignore[attr-defined]
        task=task,
        topic_profile=_profile(),
        posts=posts,
    )
    assert actions, "Expected comment backfill actions even when num_comments is unknown"
    assert actions[0]["type"] == "backfill_comments"
    assert int(actions[0]["targets"] or 0) > 0
