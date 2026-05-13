from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.comment import ContentEntity, ContentLabel
from app.models.llm_labels import CommentLLMLabel, PostLLMLabel
from app.models.post_semantic_label import PostSemanticLabel
from app.models.semantic_observation import SemanticObservation
from app.models.semantic_term import SemanticTerm
from app.services.semantic.semantic_observation_sync import sync_semantic_observations


async def _ensure_semantic_observation_table(db_session) -> None:
    async with db_session.bind.begin() as conn:
        await conn.run_sync(SemanticObservation.__table__.create, checkfirst=True)


@pytest.mark.asyncio
async def test_sync_semantic_observations_writes_post_ledger(db_session) -> None:
    await _ensure_semantic_observation_table(db_session)
    await db_session.execute(
        SemanticObservation.__table__.delete().where(
            SemanticObservation.content_type == "post",
            SemanticObservation.content_id == 101,
        )
    )
    await db_session.execute(
        SemanticTerm.__table__.delete().where(SemanticTerm.canonical == "shopify-sync-test")
    )
    db_session.add(
        SemanticTerm(
            canonical="shopify-sync-test",
            category="brand",
            lifecycle="approved",
        )
    )
    await db_session.flush()

    result = await sync_semantic_observations(
        db_session,
        content_type="post",
        content_id=101,
        post_semantic_label=PostSemanticLabel(
            post_id=101,
            l1_category="pain",
            l2_business="Ecommerce_Business",
            l3_scene="refund",
            top_terms=["shopify-sync-test"],
            rule_version="rules-v1",
            llm_version="llm-v1",
            confidence=0.88,
        ),
        post_llm_label=PostLLMLabel(
            post_id=101,
            llm_version="llm-v2",
            model_name="gpt-test",
            tags_analysis={"pain": ["chargeback", "refund"]},
            entities_extracted=["shopify-sync-test"],
        ),
        content_labels=[
            ContentLabel(content_type="post", content_id=101, category="pain", aspect="fees", confidence=90)
        ],
        content_entities=[
            ContentEntity(
                content_type="post",
                content_id=101,
                entity="shopify-sync-test",
                entity_type="platform",
                count=2,
            )
        ],
    )
    await db_session.commit()

    rows = (
        await db_session.execute(
            SemanticObservation.__table__.select().where(
                SemanticObservation.content_type == "post",
                SemanticObservation.content_id == 101,
            )
        )
    ).fetchall()

    assert result.observations_written == len(rows)
    assert len(rows) >= 6
    assert any(row.observation_type == "semantic_term" and row.term_id is not None for row in rows)
    assert any(row.observation_type == "llm_tag" and row.label_key == "pain" for row in rows)


@pytest.mark.asyncio
async def test_sync_semantic_observations_replaces_reconciled_rows(db_session) -> None:
    await _ensure_semantic_observation_table(db_session)

    await sync_semantic_observations(
        db_session,
        content_type="comment",
        content_id=202,
        comment_llm_label=CommentLLMLabel(
            comment_id=202,
            llm_version="llm-v1",
            model_name="gpt-test",
            tags_analysis={"intent": "buy"},
            entities_extracted=[],
            value_score=Decimal("0.72"),
        ),
    )
    await db_session.flush()

    second = await sync_semantic_observations(
        db_session,
        content_type="comment",
        content_id=202,
        comment_llm_label=CommentLLMLabel(
            comment_id=202,
            llm_version="llm-v2",
            model_name="gpt-test-2",
            tags_analysis={"intent": "switch"},
            entities_extracted=["paypal"],
            value_score=Decimal("0.81"),
        ),
    )
    await db_session.commit()

    rows = (
        await db_session.execute(
            SemanticObservation.__table__.select().where(
                SemanticObservation.content_type == "comment",
                SemanticObservation.content_id == 202,
            )
        )
    ).fetchall()

    assert second.observations_written == len(rows)
    assert any(row.label_value == "switch" for row in rows)
    assert not any(row.label_value == "buy" for row in rows)
