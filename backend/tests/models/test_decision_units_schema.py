from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import SessionFactory


@pytest.mark.asyncio
async def test_insight_cards_has_decision_unit_columns() -> None:
    async with SessionFactory() as session:
        columns = (
            await session.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'insight_cards'
                    """
                )
            )
        ).scalars().all()
        colset = set(columns)

    for required in {
        "kind",
        "concept_id",
        "signal_type",
        "du_schema_version",
        "du_payload",
    }:
        assert required in colset


@pytest.mark.asyncio
async def test_decision_units_view_allows_same_title_as_insight_and_filters_kind() -> None:
    async with SessionFactory() as session:
        await session.execute(
            text(
                """
                TRUNCATE TABLE
                    evidences,
                    insight_cards,
                    tasks,
                    users
                RESTART IDENTITY CASCADE
                """
            )
        )

        user_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO users (email, password_hash, membership_level)
                    VALUES (:email, :password_hash, 'free')
                    RETURNING id
                    """
                ),
                {
                    "email": f"du-{uuid.uuid4().hex}@example.com",
                    "password_hash": hash_password("SecurePass123!"),
                },
            )
        ).scalar_one()
        task_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO tasks (user_id, product_description)
                    VALUES (:user_id, :product_description)
                    RETURNING id
                    """
                ),
                {"user_id": user_id, "product_description": "DecisionUnit schema verification task"},
            )
        ).scalar_one()

        shared_title = "Same title can exist in two kinds"

        insight_id = uuid.uuid4()
        await session.execute(
            text(
                """
                INSERT INTO insight_cards (
                    id, task_id, title, summary, confidence, time_window_days, subreddits
                )
                VALUES (
                    :id, :task_id, :title, 'insight summary', 0.5000, 30, ARRAY['r/test']
                )
                """
            ),
            {"id": insight_id, "task_id": task_id, "title": shared_title},
        )

        decision_unit_id = uuid.uuid4()
        du_payload = {
            "claim": "This is a DecisionUnit",
            "metrics": {"mentions": 12},
            "recommended_actions": [{"type": "noop"}],
            "versions": {"du_schema_version": 1},
        }
        await session.execute(
            text(
                """
                INSERT INTO insight_cards (
                    id, task_id, title, summary, confidence, time_window_days, subreddits,
                    kind, signal_type, du_schema_version, du_payload
                )
                VALUES (
                    :id, :task_id, :title, 'du summary', 0.8000, 30, ARRAY['r/test'],
                    'decision_unit', 'ops', 1, CAST(:du_payload AS jsonb)
                )
                """
            ),
            {
                "id": decision_unit_id,
                "task_id": task_id,
                "title": shared_title,
                "du_payload": json.dumps(du_payload),
            },
        )
        await session.commit()

        rows = (
            await session.execute(
                text("SELECT id, du_payload FROM decision_units_v WHERE task_id = :task_id"),
                {"task_id": task_id},
            )
        ).mappings().all()

    assert len(rows) == 1
    assert rows[0]["id"] == decision_unit_id
    assert rows[0]["du_payload"]["claim"] == "This is a DecisionUnit"


@pytest.mark.asyncio
async def test_evidences_has_content_reference_columns() -> None:
    async with SessionFactory() as session:
        columns = (
            await session.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'evidences'
                    """
                )
            )
        ).scalars().all()
        colset = set(columns)

    assert "content_type" in colset
    assert "content_id" in colset

