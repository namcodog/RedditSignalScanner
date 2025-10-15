from __future__ import annotations

import uuid
from io import BytesIO
from typing import Dict, Iterable

import pytest
import xlrd
import xlsxwriter
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.main import app
from app.models.community_pool import CommunityImportHistory, CommunityPool


def _override_admin_settings(admin_email: str) -> Settings:
    base = get_settings()
    return base.model_copy(update={"admin_emails_raw": admin_email})


def _build_workbook(rows: Iterable[Dict[str, object]]) -> bytes:
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
async def test_admin_template_download_returns_valid_workbook(
    client: AsyncClient,
    token_factory,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = _override_admin_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        admin_token, _ = await token_factory(email=admin_email)
        response = await client.get(
            "/api/admin/communities/template",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        assert (
            response.headers["content-type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        workbook = xlrd.open_workbook(file_contents=response.content)
        sheet = workbook.sheet_by_index(0)
        headers = [sheet.cell_value(0, idx) for idx in range(sheet.ncols)]
        assert headers[:8] == [
            "name",
            "tier",
            "categories",
            "description_keywords",
            "daily_posts",
            "avg_comment_length",
            "quality_score",
            "priority",
        ]
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_admin_import_and_history_endpoints(
    client: AsyncClient,
    token_factory,
    db_session: AsyncSession,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    overridden = _override_admin_settings(admin_email)
    app.dependency_overrides[get_settings] = lambda: overridden

    try:
        admin_token, admin_user_id = await token_factory(email=admin_email)

        workbook_bytes = _build_workbook(
            [
                {
                    "name": "r/templateimport",
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

        response = await client.post(
            "/api/admin/communities/import",
            params={"dry_run": "false"},
            headers={"Authorization": f"Bearer {admin_token}"},
            files={
                "file": (
                    "communities.xlsx",
                    workbook_bytes,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 0
        data = body["data"]
        assert data["status"] == "success"
        assert data["summary"]["total"] == 1
        assert data["summary"]["imported"] == 1
        assert data["communities"][0]["status"] == "imported"

        stored_pool = (
            await db_session.execute(select(CommunityPool).where(CommunityPool.name == "r/templateimport"))
        ).scalar_one()
        assert stored_pool.priority == "high"

        history_resp = await client.get(
            "/api/admin/communities/import-history",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert history_resp.status_code == 200
        history_body = history_resp.json()
        assert history_body["code"] == 0
        imports = history_body["data"]["imports"]
        assert imports
        latest = imports[0]
        assert latest["filename"] == "communities.xlsx"
        assert latest["status"] == "success"
        assert latest["uploaded_by"] == admin_email
        assert latest["summary"]["imported"] == 1

        history_rows = (
            await db_session.execute(select(CommunityImportHistory).order_by(CommunityImportHistory.id.desc()))
        ).scalars().all()
        assert history_rows
        assert history_rows[0].uploaded_by_user_id == uuid.UUID(admin_user_id)
    finally:
        app.dependency_overrides.pop(get_settings, None)
