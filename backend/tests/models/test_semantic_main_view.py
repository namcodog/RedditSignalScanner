from __future__ import annotations

import json
from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import text

from app.db.session import SessionFactory


async def _insert_community_pool(session, *, name: str, ts: datetime) -> int:
    result = await session.execute(
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
        {"name": name, "ts": ts},
    )
    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_semantic_main_view_exists() -> None:
    async with SessionFactory() as session:
        view_exists = (
            await session.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.views
                    WHERE table_schema = 'public'
                      AND table_name = 'semantic_main_view'
                    LIMIT 1
                    """
                )
            )
        ).scalar()

    assert view_exists == 1


@pytest.mark.asyncio
async def test_semantic_main_view_post_prefers_scores_and_is_resilient_to_dirty_labels() -> None:
    async with SessionFactory() as session:
        await session.execute(
            text(
                """
                TRUNCATE TABLE
                    content_labels,
                    content_entities,
                    post_semantic_labels,
                    post_scores,
                    comment_scores,
                    comments,
                    posts_raw,
                    community_pool
                RESTART IDENTITY CASCADE
                """
            )
        )

        now = datetime.now(timezone.utc)
        community_id = await _insert_community_pool(
            session, name=f"r/test_{uuid.uuid4().hex[:8]}", ts=now
        )
        post_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO posts_raw (
                        source, source_post_id, version, created_at,
                        fetched_at, valid_from, subreddit, title, body, is_current, community_id
                    )
                    VALUES (
                        'reddit', :pid, 1, :ts,
                        :ts, :ts, 'r/test', 'title', 'body', true, :community_id
                    )
                    RETURNING id
                    """
                ),
                {
                    "pid": f"post_{uuid.uuid4().hex[:8]}",
                    "ts": now,
                    "community_id": community_id,
                },
            )
        ).scalar_one()

        tags_analysis = {"topic": "Shopify Ads", "kind": "tags_analysis"}
        entities_extracted = [{"entity": "Shopify", "type": "brand", "count": 2}]

        await session.execute(
            text(
                """
                INSERT INTO post_scores (
                    post_id, llm_version, rule_version, scored_at,
                    is_latest, value_score, opportunity_score, purchase_intent_score,
                    business_pool, sentiment, tags_analysis, entities_extracted
                )
                VALUES (
                    :post_id, 'llm-x', 'formal_v2', :ts,
                    true, 8.0, 7.0, 6.0,
                    'core', 0.25, CAST(:tags_analysis AS jsonb), CAST(:entities_extracted AS jsonb)
                )
                """
            ),
            {
                "post_id": post_id,
                "ts": now,
                "tags_analysis": json.dumps(tags_analysis),
                "entities_extracted": json.dumps(entities_extracted),
            },
        )

        await session.execute(
            text(
                """
                INSERT INTO post_semantic_labels (
                    post_id, l1_category, l2_business, l3_scene,
                    matched_rule_ids, top_terms, raw_scores,
                    rule_version, llm_version, created_at, updated_at
                )
                VALUES (
                    :post_id, 'ecommerce', 'ads', 'conversion',
                    ARRAY[1,2], ARRAY['roas','cpc'], '{"score": 0.9}'::jsonb,
                    'rulebook_v1', 'llm-tax', :ts, :ts
                )
                """
            ),
            {"post_id": post_id, "ts": now},
        )

        # Insert a "dirty" label value that used to crash ORM Enum parsing (e.g. pain_tag)
        await session.execute(
            text(
                """
                INSERT INTO content_labels (content_type, content_id, category, aspect, confidence)
                VALUES ('post', :post_id, 'pain_tag', 'subscription', 90)
                """
            ),
            {"post_id": post_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO content_entities (content_type, content_id, entity, entity_type, count)
                VALUES ('post', :post_id, 'Shopify', 'brand', 2)
                """
            ),
            {"post_id": post_id},
        )
        await session.commit()

        row = (
            await session.execute(
                text(
                    """
                    SELECT *
                    FROM semantic_main_view
                    WHERE content_type = 'post' AND content_id = :post_id
                    """
                ),
                {"post_id": post_id},
            )
        ).mappings().one()

    assert row["tags_analysis"] == tags_analysis
    assert row["entities_extracted"] == entities_extracted
    assert row["taxonomy_l1"] == "ecommerce"
    assert row["taxonomy_l2"] == "ads"
    assert row["taxonomy_l3"] == "conversion"
    assert isinstance(row["content_labels"], list)
    assert any(label.get("category") == "pain_tag" for label in row["content_labels"])
    assert isinstance(row["content_entities"], list)
    assert any(ent.get("entity") == "Shopify" for ent in row["content_entities"])
    assert row["provenance"]["has_score"] is True


@pytest.mark.asyncio
async def test_semantic_main_view_post_falls_back_when_scores_missing() -> None:
    async with SessionFactory() as session:
        await session.execute(
            text(
                """
                TRUNCATE TABLE
                    content_labels,
                    content_entities,
                    post_semantic_labels,
                    post_scores,
                    comments,
                    posts_raw,
                    community_pool
                RESTART IDENTITY CASCADE
                """
            )
        )

        now = datetime.now(timezone.utc)
        community_id = await _insert_community_pool(
            session, name=f"r/test_{uuid.uuid4().hex[:8]}", ts=now
        )
        post_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO posts_raw (
                        source, source_post_id, version, created_at,
                        fetched_at, valid_from, subreddit, title, body, is_current, community_id
                    )
                    VALUES (
                        'reddit', :pid, 1, :ts,
                        :ts, :ts, 'r/test', 'title', 'body', true, :community_id
                    )
                    RETURNING id
                    """
                ),
                {
                    "pid": f"post_{uuid.uuid4().hex[:8]}",
                    "ts": now,
                    "community_id": community_id,
                },
            )
        ).scalar_one()

        await session.execute(
            text(
                """
                INSERT INTO post_semantic_labels (
                    post_id, l1_category, l2_business, l3_scene,
                    rule_version, llm_version, created_at, updated_at
                )
                VALUES (
                    :post_id, 'ecommerce', 'ads', 'conversion',
                    'rulebook_v1', 'llm-tax', :ts, :ts
                )
                """
            ),
            {"post_id": post_id, "ts": now},
        )
        await session.commit()

        row = (
            await session.execute(
                text(
                    """
                    SELECT *
                    FROM semantic_main_view
                    WHERE content_type = 'post' AND content_id = :post_id
                    """
                ),
                {"post_id": post_id},
            )
        ).mappings().one()

    assert row["tags_analysis"] == {}
    assert row["entities_extracted"] == []
    assert row["taxonomy_l1"] == "ecommerce"
    assert row["provenance"]["has_score"] is False


@pytest.mark.asyncio
async def test_semantic_main_view_comment_uses_comment_scores_latest_v() -> None:
    async with SessionFactory() as session:
        await session.execute(
            text(
                """
                TRUNCATE TABLE
                    comment_scores,
                    comments,
                    posts_raw,
                    community_pool
                RESTART IDENTITY CASCADE
                """
            )
        )

        now = datetime.now(timezone.utc)
        community_id = await _insert_community_pool(
            session, name=f"r/test_{uuid.uuid4().hex[:8]}", ts=now
        )
        source_post_id = f"post_{uuid.uuid4().hex[:8]}"
        post_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO posts_raw (
                        source, source_post_id, version, created_at,
                        fetched_at, valid_from, subreddit, title, body, is_current, community_id
                    )
                    VALUES (
                        'reddit', :pid, 1, :ts,
                        :ts, :ts, 'r/test', 'title', 'body', true, :community_id
                    )
                    RETURNING id
                    """
                ),
                {"pid": source_post_id, "ts": now, "community_id": community_id},
            )
        ).scalar_one()

        comment_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO comments (
                        reddit_comment_id, source, source_post_id, subreddit, body, created_utc, post_id
                    )
                    VALUES (:cid, 'reddit', :pid, 'r/test', 'comment body', :ts, :post_id)
                    RETURNING id
                    """
                ),
                {"cid": f"t1_{uuid.uuid4().hex[:8]}", "pid": source_post_id, "ts": now, "post_id": post_id},
            )
        ).scalar_one()

        tags_analysis = {"topic": "Shopify Ads", "kind": "comment_tags"}
        entities_extracted = [{"entity": "Meta Ads", "type": "platform", "count": 1}]

        await session.execute(
            text(
                """
                INSERT INTO comment_scores (
                    comment_id, llm_version, rule_version, scored_at,
                    is_latest, value_score, business_pool, tags_analysis, entities_extracted
                )
                VALUES (
                    :comment_id, 'llm-x', 'formal_v2', :ts,
                    true, 6.0, 'lab', CAST(:tags_analysis AS jsonb), CAST(:entities_extracted AS jsonb)
                )
                """
            ),
            {
                "comment_id": comment_id,
                "ts": now,
                "tags_analysis": json.dumps(tags_analysis),
                "entities_extracted": json.dumps(entities_extracted),
            },
        )
        await session.commit()

        row = (
            await session.execute(
                text(
                    """
                    SELECT *
                    FROM semantic_main_view
                    WHERE content_type = 'comment' AND content_id = :comment_id
                    """
                ),
                {"comment_id": comment_id},
            )
        ).mappings().one()

    assert row["tags_analysis"] == tags_analysis
    assert row["entities_extracted"] == entities_extracted
    assert row["provenance"]["has_score"] is True
