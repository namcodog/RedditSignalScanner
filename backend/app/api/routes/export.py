"""Export API endpoints."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from app.core.config import get_settings
from app.core.security import TokenPayload, decode_jwt_token
from app.db.session import get_session
from app.services.export.csv_exporter import (
    CSVExportError,
    CSVExportNotFoundError,
    CSVExportPermissionError,
    CSVExportService,
)

router = APIRouter(prefix="/export", tags=["export"])


class ExportCsvRequest(BaseModel):
    task_id: UUID = Field(description="Analysis task identifier")


def _remove_file(path: Path) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        # 删除失败不应阻塞响应
        pass


@router.post("/csv", summary="导出分析报告 CSV")
async def export_csv(
    body: ExportCsvRequest,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> FileResponse:
    """Export analysis insights as a CSV file for the authenticated user."""
    try:
        user_id = UUID(payload.sub)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    settings = get_settings()
    service = CSVExportService(db, output_dir=Path(settings.report_export_dir))
    try:
        csv_path = await service.export_to_csv(task_id=body.task_id, user_id=user_id)
    except CSVExportPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except CSVExportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CSVExportError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    background = BackgroundTask(_remove_file, csv_path)
    return FileResponse(csv_path, media_type="text/csv", filename=csv_path.name, background=background)


__all__ = ["router"]
