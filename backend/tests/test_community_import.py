from __future__ import annotations

import uuid
from io import BytesIO
from typing import List

import pytest
import xlsxwriter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_pool import CommunityImportHistory, CommunityPool
from app.services.community_import_service import CommunityImportService


def _build_excel(rows: List[dict]) -> bytes:
    buffer = BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    sheet = workbook.add_worksheet("Communities")

    columns = [
        "name",
        "tier",
        "categories",
        "description_keywords",
        "daily_posts",
        "avg_comment_length",
        "quality_score",
        "priority",
    ]

    for idx, column_name in enumerate(columns):
        sheet.write(0, idx, column_name)

    for row_idx, payload in enumerate(rows, start=1):
        for col_idx, column_name in enumerate(columns):
            sheet.write(row_idx, col_idx, payload.get(column_name))

    workbook.close()
    buffer.seek(0)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_import_success_creates_communities_and_history(db_session: AsyncSession) -> None:
    service = CommunityImportService(db_session)

    content = _build_excel(
        [
            {
                "name": "r/testcommunity",
                "tier": "gold",
                "categories": "startup,business",
                "description_keywords": "builder,founder",
                "daily_posts": 120,
                "avg_comment_length": 60,
                "quality_score": 0.9,
                "priority": "high",
            }
        ]
    )

    admin_id = uuid.uuid4()
    result = await service.import_from_excel(
        content=content,
        filename="communities.xlsx",
        dry_run=False,
        actor_email="admin@example.com",
        actor_id=admin_id,
    )

    assert result["status"] == "success"
    summary = result["summary"]
    assert summary == {
        "total": 1,
        "valid": 1,
        "invalid": 0,
        "duplicates": 0,
        "imported": 1,
    }
    assert result["communities"][0]["status"] == "imported"

    pool_rows = (await db_session.execute(select(CommunityPool))).scalars().all()
    assert len(pool_rows) == 1
    stored = pool_rows[0]
    assert stored.name == "r/testcommunity"
    assert stored.priority == "high"
    assert stored.daily_posts == 120
    assert stored.categories == ["startup", "business"]

    history_rows = (
        await db_session.execute(
            select(CommunityImportHistory).order_by(CommunityImportHistory.id)
        )
    ).scalars().all()
    assert len(history_rows) == 1
    history = history_rows[0]
    assert history.status == "success"
    assert history.uploaded_by == "admin@example.com"
    assert history.imported_rows == 1
    assert history.valid_rows == 1
    assert history.duplicate_rows == 0


@pytest.mark.asyncio
async def test_import_validation_and_duplicates(db_session: AsyncSession) -> None:
    existing = CommunityPool(
        name="r/existing",
        tier="gold",
        categories=["existing"],
        description_keywords=["existing"],
        daily_posts=10,
        avg_comment_length=5,
        quality_score=0.75,
        priority="medium",
    )
    db_session.add(existing)
    await db_session.commit()

    service = CommunityImportService(db_session)
    content = _build_excel(
        [
            {
                "name": "startups",  # missing r/ prefix
                "tier": "premium",
                "categories": "startup",
                "description_keywords": "builder",
                "daily_posts": 120,
                "avg_comment_length": 60,
                "quality_score": 1.2,
                "priority": "urgent",
            },
            {
                "name": "r/existing",
                "tier": "gold",
                "categories": "startup",
                "description_keywords": "builder",
            },
            {
                "name": "r/existing",
                "tier": "gold",
                "categories": "startup",
                "description_keywords": "builder",
            },
        ]
    )

    admin_id = uuid.uuid4()
    result = await service.import_from_excel(
        content=content,
        filename="communities_invalid.xlsx",
        dry_run=True,
        actor_email="admin@example.com",
        actor_id=admin_id,
    )

    assert result["status"] == "error"
    summary = result["summary"]
    assert summary["total"] == 3
    assert summary["imported"] == 0
    assert summary["invalid"] >= 1
    assert summary["duplicates"] >= 1
    assert "errors" in result
    error_messages = {error["error"] for error in result["errors"]}
    assert "社区名称必须以 r/ 开头" in error_messages
    assert "tier 必须是 seed/gold/silver/admin 之一" in error_messages or "tier 为必填字段" in error_messages
    assert "社区已存在于数据库，请勿重复导入" in error_messages
    assert "Excel 中存在重复的社区名称" in error_messages

    pool_rows = (await db_session.execute(select(CommunityPool))).scalars().all()
    assert len(pool_rows) == 1  # no new imports in dry run

    history_rows = (
        await db_session.execute(
            select(CommunityImportHistory).order_by(CommunityImportHistory.id)
        )
    ).scalars().all()
    assert len(history_rows) == 2  # previous success + this dry run
    latest_history = history_rows[-1]
    assert latest_history.status == "error"
    assert latest_history.dry_run is True
    assert latest_history.imported_rows == 0
