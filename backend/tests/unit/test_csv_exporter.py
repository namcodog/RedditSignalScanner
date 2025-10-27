"""Tests for CSV export service."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.models.insight import Evidence, InsightCard
from app.models.task import Task, TaskStatus
from app.models.user import MembershipLevel, User


@pytest.mark.asyncio
async def test_export_to_csv_success(tmp_path, db_session):
    """CSV exporter should generate a file with expected headers and rows."""
    from app.services.export.csv_exporter import CSVExportService

    user = User(
        email="csv@example.com",
        password_hash="hashed",
        membership_level=MembershipLevel.PRO,
    )
    db_session.add(user)
    await db_session.flush()

    task = Task(
        id=uuid4(),
        user_id=user.id,
        product_description="Test product",
        status=TaskStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.flush()

    card = InsightCard(
        task_id=task.id,
        title="Insight Title",
        summary="Summary text",
        confidence=0.83,
        time_window_days=30,
        subreddits=["r/test"],
    )
    db_session.add(card)
    await db_session.flush()

    evidence = Evidence(
        insight_card_id=card.id,
        post_url="https://reddit.com/r/test",
        excerpt="Example evidence",
        timestamp=datetime.now(timezone.utc),
        subreddit="r/test",
        score=0.9,
    )
    db_session.add(evidence)
    await db_session.commit()

    exporter = CSVExportService(db_session, output_dir=Path(tmp_path))
    csv_path = await exporter.export_to_csv(task_id=task.id, user_id=user.id)

    assert csv_path.exists()
    content = csv_path.read_text(encoding="utf-8").strip().splitlines()
    assert content[0] == "title,summary,confidence,time_window_days,subreddits,evidence_count"
    assert "Insight Title" in content[1]


@pytest.mark.asyncio
async def test_export_to_csv_invalid_task(tmp_path, db_session):
    """Exporter should raise when task cannot be accessed."""
    from app.services.export.csv_exporter import CSVExportService

    exporter = CSVExportService(db_session, output_dir=Path(tmp_path))

    with pytest.raises(LookupError):
        await exporter.export_to_csv(task_id=uuid4(), user_id=uuid4())
