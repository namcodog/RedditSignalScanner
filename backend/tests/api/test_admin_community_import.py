from __future__ import annotations

import io
import uuid

import pytest
import xlsxwriter
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.main import app
from app.models.community_import import CommunityImportHistory
from app.models.community_pool import CommunityPool


def _override_settings(admin_email: str) -> Settings:
    current = get_settings()
    return current.model_copy(update={"admin_emails_raw": admin_email})


def _build_workbook(rows: list[list[object]]) -> bytes:
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
    for row_index, row in enumerate(rows, start=1):
        worksheet.write_row(row_index, 0, row)
    workbook.close()
    buffer.seek(0)
    return buffer.read()


@pytest.mark.asyncio
async def test_admin_template_download_returns_valid_workbook(
    client: AsyncClient,
    token_factory,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    app.dependency_overrides[get_settings] = lambda: _override_settings(admin_email)

    try:
        token, _ = await token_factory(email=admin_email)
        response = await client.get(
            "/api/admin/communities/template",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] in (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/octet-stream",
        )
        payload = response.content
        assert len(payload) > 1024
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.asyncio
async def test_admin_import_and_history_endpoints(
    client: AsyncClient,
    token_factory,
    db_session: AsyncSession,
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex}@example.com"
    app.dependency_overrides[get_settings] = lambda: _override_settings(admin_email)

    community_rows = [
        [
            f"r/testimport_{uuid.uuid4().hex[:8]}",
            "gold",
            "startup,innovation",
            "founder,growth",
            120,
            60,
            0.88,
            "high",
        ],
        [
            f"r/testimport_{uuid.uuid4().hex[:8]}",
            "silver",
            "marketing,content",
            "newsletter,copywriting",
            85,
            45,
            0.73,
            "medium",
        ],
    ]
    excel_bytes = _build_workbook(community_rows)

    try:
        token, actor_id = await token_factory(email=admin_email)
        headers = {"Authorization": f"Bearer {token}"}

        dry_run_response = await client.post(
            "/api/admin/communities/import",
            params={"dry_run": "true"},
            headers=headers,
            files={"file": ("communities.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert dry_run_response.status_code == 200
        dry_run_payload = dry_run_response.json()
        assert dry_run_payload["code"] == 0
        data = dry_run_payload["data"]
        assert data["status"] in {"validated", "success"}
        assert data["summary"]["total"] == len(community_rows)

        history_after_dry_run = await client.get(
            "/api/admin/communities/import-history",
            headers=headers,
        )
        assert history_after_dry_run.status_code == 200
        history_payload = history_after_dry_run.json()
        assert history_payload["code"] == 0
        history_items = history_payload["data"]["imports"]
        assert any(item["filename"] == "communities.xlsx" and item["dry_run"] for item in history_items)

        import_response = await client.post(
            "/api/admin/communities/import",
            params={"dry_run": "false"},
            headers=headers,
            files={"file": ("communities.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert import_response.status_code == 200
        import_payload = import_response.json()
        assert import_payload["code"] == 0
        assert import_payload["data"]["summary"]["imported"] == len(community_rows)

        community_names = [row[0] for row in community_rows]
        communities_stmt = select(CommunityPool).where(
            CommunityPool.name.in_(community_names)
        )
        communities = (await db_session.execute(communities_stmt)).scalars().all()
        assert len(communities) == len(community_rows)

        # 单用户模式：uploaded_by_user_id 为 None,通过 uploaded_by 邮箱查询
        history_stmt = select(CommunityImportHistory).where(
            CommunityImportHistory.uploaded_by == "admin@local"
        )
        history_records = (await db_session.execute(history_stmt)).scalars().all()
        assert len(history_records) >= 2

    finally:
        app.dependency_overrides.pop(get_settings, None)
