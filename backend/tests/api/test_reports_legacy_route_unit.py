from __future__ import annotations

from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import Response
from fastapi.responses import StreamingResponse

from app.api.routes import reports as legacy_reports
from app.api.v1.endpoints import reports as v1_reports
from app.core.security import TokenPayload
from app.schemas.analysis import CommunitySourceDetail
from app.schemas.community_export import CommunityExportResponse


@pytest.mark.asyncio
async def test_legacy_get_analysis_report_delegates_to_v1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = uuid4()
    payload = TokenPayload(sub=str(uuid4()))
    response = Response()
    db = AsyncMock()
    expected = {"task_id": str(task_id), "data_source": "real"}

    delegate = AsyncMock(return_value=expected)
    monkeypatch.setattr(v1_reports, "get_analysis_report", delegate)

    result = await legacy_reports.get_analysis_report(
        task_id=task_id,
        response=response,
        payload=payload,
        request=None,
        db=db,
    )

    assert result is expected
    delegate.assert_awaited_once_with(
        task_id=task_id,
        response=response,
        payload=payload,
        db=db,
    )


@pytest.mark.asyncio
async def test_legacy_get_report_communities_delegates_to_v1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = uuid4()
    payload = TokenPayload(sub=str(uuid4()))
    response = Response()
    db = AsyncMock()
    details = [
        CommunitySourceDetail(
            name="r/test",
            categories=["AI_Workflow"],
            mentions=3,
            daily_posts=1,
            avg_comment_length=42.0,
            cache_hit_rate=0.5,
            from_cache=False,
        )
    ]

    async def _fake_delegate(*, task_id, response, payload, db):
        response.headers["X-Communities-Source"] = "analysis_sources_detail"
        response.headers["X-Communities-Degraded"] = "none"
        return details

    monkeypatch.setattr(v1_reports, "get_report_communities", _fake_delegate)

    result = await legacy_reports.get_report_communities(
        task_id=task_id,
        response=response,
        payload=payload,
        db=db,
    )

    assert result == details
    assert response.headers["X-Communities-Source"] == "analysis_sources_detail"
    assert response.headers["X-Communities-Degraded"] == "none"


@pytest.mark.asyncio
async def test_legacy_export_communities_delegates_to_v1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = uuid4()
    payload = TokenPayload(sub=str(uuid4()))
    db = AsyncMock()
    expected = CommunityExportResponse(
        task_id=str(task_id),
        scope="all",
        source="analysis_sources_detail",
        degraded_reason=None,
        items=[],
    )

    delegate = AsyncMock(return_value=expected)
    monkeypatch.setattr(v1_reports, "export_communities", delegate)

    result = await legacy_reports.export_communities(
        task_id=task_id,
        scope="all",
        payload=payload,
        db=db,
    )

    assert result == expected
    delegate.assert_awaited_once_with(
        task_id=task_id,
        scope="all",
        payload=payload,
        db=db,
    )


@pytest.mark.asyncio
async def test_legacy_download_report_delegates_to_v1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task_id = uuid4()
    payload = TokenPayload(sub=str(uuid4()))
    db = AsyncMock()
    expected = StreamingResponse(iter([b"ok"]), media_type="text/plain")

    delegate = AsyncMock(return_value=expected)
    monkeypatch.setattr(v1_reports, "download_report", delegate)

    result = await legacy_reports.download_report(
        task_id=task_id,
        format="json",
        payload=payload,
        db=db,
    )

    assert result is expected
    delegate.assert_awaited_once_with(
        task_id=task_id,
        format="json",
        payload=payload,
        db=db,
    )
