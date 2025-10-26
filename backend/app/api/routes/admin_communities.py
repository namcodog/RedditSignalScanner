from __future__ import annotations

import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.admin import _response
from app.db.session import get_session
from app.models.community_cache import CommunityCache
from app.services.community_import_service import CommunityImportService

router = APIRouter(prefix="/admin/communities", tags=["admin"])


@router.get("/summary", summary="获取社区验收列表")
async def get_communities_summary(
    q: str | None = Query(None, description="搜索关键词"),
    status: str | None = Query(None, description="状态筛选: green|yellow|red"),
    tag: str | None = Query(None, description="标签筛选"),
    sort: str | None = Query("cscore_desc", description="排序: cscore_desc|hit_desc"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    获取社区验收列表（真实数据）

    从 community_cache 表读取社区数据，计算 C-Score 和状态灯号
    """
    # 构建基础查询
    stmt = select(CommunityCache)

    # 搜索过滤
    if q:
        stmt = stmt.where(CommunityCache.community_name.ilike(f"%{q}%"))

    # 计算总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    # 排序
    if sort == "hit_desc":
        stmt = stmt.order_by(desc(CommunityCache.hit_count))
    else:  # cscore_desc (默认)
        stmt = stmt.order_by(desc(CommunityCache.quality_score))

    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    # 执行查询
    result = await session.execute(stmt)
    communities = result.scalars().all()

    # 转换为响应格式
    items = []
    for comm in communities:
        # 计算 C-Score (0-100)
        c_score = int(float(comm.quality_score) * 100)

        # 计算状态灯号
        if c_score >= 70 and comm.success_hit > comm.failure_hit:
            status_color = "green"
            labels = ["状态:正常"]
        elif c_score >= 50:
            status_color = "yellow"
            labels = ["状态:警告"]
        else:
            status_color = "red"
            labels = ["状态:异常"]

        # 添加质量标签
        if comm.quality_tier == "high":
            labels.append("质量:优秀")
        elif comm.quality_tier == "low":
            labels.append("质量:较差")

        # 计算重复率和垃圾率（基于现有字段估算）
        dup_ratio = float(comm.dedup_rate) if comm.dedup_rate else 0.0
        spam_ratio = 0.0  # 暂时没有垃圾率字段，设为 0

        # 计算主题评分（基于质量分数）
        topic_score = float(comm.quality_score)

        # 计算 7 天命中数（使用 hit_count 作为近似）
        hit_7d = comm.hit_count

        items.append({
            "community": comm.community_name,
            "hit_7d": hit_7d,
            "last_crawled_at": comm.last_crawled_at.isoformat() if comm.last_crawled_at else None,
            "dup_ratio": dup_ratio,
            "spam_ratio": spam_ratio,
            "topic_score": topic_score,
            "c_score": c_score,
            "status_color": status_color,
            "labels": labels,
        })

    # 状态筛选（在内存中过滤，因为状态是计算出来的）
    if status:
        items = [item for item in items if item["status_color"] == status]
        total = len(items)

    return _response({
        "items": items,
        "total": total,
    })



@router.get("/template", summary="下载社区导入 Excel 模板")
async def download_template() -> StreamingResponse:
    """
    向管理员下发最新的 Excel 模板，包含样例与字段提示。

    注意：此端点无需登录鉴权，适用于单用户本地部署场景。
    """
    content = CommunityImportService.generate_template()
    filename = "community_template.xlsx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/import", summary="上传并导入社区信息")
async def import_communities(
    file: UploadFile = File(..., description="Excel 文件 (.xlsx/.xls)"),
    dry_run: bool = Query(
        False,
        description="仅验证（不写入数据库）。true=仅验证，false=写入。",
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    接收管理员上传的 Excel 并将社区写入社区池，支持 dry-run 验证模式。

    注意：此端点无需登录鉴权，适用于单用户本地部署场景。
    """
    filename = file.filename or "community_import.xlsx"
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上传文件内容为空",
        )

    # 单用户模式：使用固定的管理员标识
    # 使用固定的 UUID 作为管理员 ID (基于 "admin@local" 生成)
    actor_email = "admin@local"
    actor_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    service = CommunityImportService(session)
    result = await service.import_from_excel(
        content=content,
        filename=filename,
        dry_run=dry_run,
        actor_email=actor_email,
        actor_id=actor_id,
    )
    return _response(result)


@router.get("/import-history", summary="查询社区导入历史")
async def get_import_history(
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="返回的历史记录数量",
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """
    返回最近的导入历史记录，便于审计与回溯。

    注意：此端点无需登录鉴权，适用于单用户本地部署场景。
    """
    service = CommunityImportService(session)
    history = await service.get_import_history(limit=limit)
    return _response(history)


__all__ = ["router"]
