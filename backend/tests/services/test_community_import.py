from __future__ import annotations

import io
import uuid

import pytest
import xlsxwriter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community_import import CommunityImportHistory
from app.models.community_pool import CommunityPool
from app.services.community_import_service import CommunityImportService


def _make_workbook(rows: list[list[object]]) -> bytes:
    headers = [
        "name",
        "tier",
        "categories",
        "description_keywords",
        "daily_posts",
        "avg_comment_length",
        "quality_score",
        "priority",
    ]
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    worksheet = workbook.add_worksheet("Communities")
    worksheet.write_row(0, 0, headers)
    for index, row in enumerate(rows, start=1):
        worksheet.write_row(index, 0, row)
    workbook.close()
    buffer.seek(0)
    return buffer.read()


@pytest.mark.asyncio
async def test_import_from_excel_records_history_and_commits(
    db_session: AsyncSession,
) -> None:
    service = CommunityImportService(db_session)
    actor_id = uuid.uuid4()
    actor_email = f"admin-{actor_id.hex}@example.com"

    rows = [
        [
            f"r/service_test_{uuid.uuid4().hex[:8]}",
            "gold",
            "startup,founder",
            "launch,growth",
            150,
            70,
            0.91,
            "high",
        ],
        [
            f"r/service_test_{uuid.uuid4().hex[:8]}",
            "silver",
            "marketing,content",
            "newsletter,copywriting",
            80,
            55,
            0.76,
            "medium",
        ],
    ]
    excel_bytes = _make_workbook(rows)

    dry_run_result = await service.import_from_excel(
        content=excel_bytes,
        filename="service-test.xlsx",
        dry_run=True,
        actor_email=actor_email,
        actor_id=actor_id,
    )
    assert dry_run_result["status"] in {"validated", "success"}
    assert dry_run_result["summary"]["total"] == len(rows)
    assert dry_run_result["summary"]["imported"] == 0

    dry_run_history = await db_session.execute(
        select(CommunityImportHistory).where(
            CommunityImportHistory.filename == "service-test.xlsx"
        )
    )
    history_records = dry_run_history.scalars().all()
    assert len(history_records) == 1
    assert history_records[0].dry_run is True
    assert history_records[0].uploaded_by == actor_email
    assert history_records[0].total_rows == len(rows)

    import_result = await service.import_from_excel(
        content=excel_bytes,
        filename="service-test.xlsx",
        dry_run=False,
        actor_email=actor_email,
        actor_id=actor_id,
    )
    assert import_result["status"] == "success"
    assert import_result["summary"]["imported"] == len(rows)

    communities = await db_session.execute(
        select(CommunityPool).where(CommunityPool.name.in_([row[0] for row in rows]))
    )
    assert len(communities.scalars().all()) == len(rows)

    history_all = await db_session.execute(
        select(CommunityImportHistory).where(
            CommunityImportHistory.filename == "service-test.xlsx"
        )
    )
    assert len(history_all.scalars().all()) == 2


@pytest.mark.asyncio
async def test_import_from_excel_missing_columns_returns_error(
    db_session: AsyncSession,
) -> None:
    service = CommunityImportService(db_session)
    actor_email = "admin-missing@example.com"

    headers = [
        "name",
        "categories",
        "description_keywords",
    ]
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    worksheet = workbook.add_worksheet("Communities")
    worksheet.write_row(0, 0, headers)
    worksheet.write_row(
        1,
        0,
        [
            f"r/missingtier_{uuid.uuid4().hex[:6]}",
            "startup,founder",
            "growth,launch",
        ],
    )
    workbook.close()
    buffer.seek(0)

    result = await service.import_from_excel(
        content=buffer.read(),
        filename="missing-tier.xlsx",
        dry_run=True,
        actor_email=actor_email,
        actor_id=None,
    )

    assert result["status"] == "error"
    assert result["summary"]["total"] == 0
    assert result["summary"]["imported"] == 0
    assert any(error["field"] == "tier" for error in result["errors"])

    history = await db_session.execute(
        select(CommunityImportHistory).where(
            CommunityImportHistory.filename == "missing-tier.xlsx"
        )
    )
    records = history.scalars().all()
    assert len(records) == 1
    assert records[0].dry_run is True
