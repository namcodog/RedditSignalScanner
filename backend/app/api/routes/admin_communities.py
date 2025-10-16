from __future__ import annotations

import uuid
from io import BytesIO

from fastapi import (APIRouter, Depends, File, HTTPException, Query,
                     UploadFile, status)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.admin import _response
from app.core.auth import require_admin
from app.core.security import TokenPayload
from app.db.session import get_session
from app.services.community_import_service import CommunityImportService

router = APIRouter(prefix="/admin/communities", tags=["admin"])


@router.get("/template", summary="下载社区导入 Excel 模板")  # type: ignore[misc]
async def download_template(
    _payload: TokenPayload = Depends(require_admin),
) -> StreamingResponse:
    content = CommunityImportService.generate_template()
    headers = {
        "Content-Disposition": 'attachment; filename="community_template.xlsx"',
    }
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/import", summary="上传并导入社区信息")  # type: ignore[misc]
async def import_communities(
    file: UploadFile = File(..., description="Excel 模板文件（.xlsx）"),
    dry_run: bool = Query(False, description="true=仅验证，false=验证并导入"),
    payload: TokenPayload = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上传文件不能为空",
        )

    try:
        actor_id = uuid.UUID(payload.sub)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token sub 无法解析为 UUID",
        ) from exc

    actor_email = payload.email or "unknown@admin"
    service = CommunityImportService(session)
    result = await service.import_from_excel(
        content=content,
        filename=file.filename,
        dry_run=dry_run,
        actor_email=actor_email,
        actor_id=actor_id,
    )
    return _response(result)


@router.get("/import-history", summary="查询社区导入历史")  # type: ignore[misc]
async def get_import_history(
    _payload: TokenPayload = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    service = CommunityImportService(session)
    result = await service.get_import_history()
    return _response(result)


__all__ = ["router"]
