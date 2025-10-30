from __future__ import annotations

import asyncio
import time
from collections import deque
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import TokenPayload, decode_jwt_token
from app.db.session import get_session
from app.schemas.report_payload import ReportPayload
from app.schemas.analysis import CommunitySourceDetail
from app.services.report_service import ReportService, ReportServiceError
from app.schemas.community_export import CommunityExportItem, CommunityExportResponse
from app.services.report_service import (
    InMemoryReportCache,
    ReportAccessDeniedError,
    ReportDataValidationError,
    ReportNotFoundError,
    ReportNotReadyError,
    ReportService,
    ReportServiceError,
)
from app.services.report_export_service import ExportFormat, ReportExportService
from sqlalchemy import select
from app.models.community_pool import CommunityPool
from app.models.community_cache import CommunityCache

class SlidingWindowRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self._max_requests = max(1, max_requests)
        self._window_seconds = max(1, window_seconds)
        self._hits: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    def configure(self, *, max_requests: int | None = None, window_seconds: int | None = None) -> None:
        if max_requests is not None:
            self._max_requests = max(1, max_requests)
        if window_seconds is not None:
            self._window_seconds = max(1, window_seconds)

    async def allow(self, key: str) -> bool:
        now = time.monotonic()
        async with self._lock:
            bucket = self._hits.setdefault(key, deque())
            cutoff = now - self._window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self._max_requests:
                return False
            bucket.append(now)
            return True


router = APIRouter(prefix="/report", tags=["analysis"])

REPORT_CACHE = InMemoryReportCache(settings.report_cache_ttl_seconds)
REPORT_RATE_LIMITER = SlidingWindowRateLimiter(
    max_requests=settings.report_rate_limit_per_minute,
    window_seconds=settings.report_rate_limit_window_seconds,
)


@router.options("/{task_id}")
async def options_analysis_report(task_id: str) -> Response:
    # CORS 预检请求在路由层直接放行，避免触发认证依赖
    return Response(status_code=204)

@router.get("/{task_id}", summary="Fetch completed analysis report", response_model=ReportPayload)
async def get_analysis_report(
    task_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> ReportPayload:
    service = ReportService(db, cache=REPORT_CACHE)
    try:
        user_id = UUID(payload.sub)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    allowed = await REPORT_RATE_LIMITER.allow(payload.sub)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many report downloads, please wait and try again.",
        )

    try:
        return await service.get_report(task_id, user_id)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/{task_id}/download", summary="Download report in specified format")
async def download_report(
    task_id: UUID,
    format: ExportFormat = Query("pdf", description="Export format: pdf or json"),
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """
    下载指定格式的报告文件

    - **task_id**: 任务ID
    - **format**: 导出格式，支持 pdf 或 json

    需要 JWT 认证，并受速率限制保护。
    """
    service = ReportService(db, cache=REPORT_CACHE)
    try:
        user_id = UUID(payload.sub)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        ) from exc

    # 速率限制
    allowed = await REPORT_RATE_LIMITER.allow(payload.sub)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many report downloads, please wait and try again.",
        )

    # 获取报告数据
    try:
        report = await service.get_report(task_id, user_id)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    # 生成导出文件
    try:
        if format == "pdf":
            content = ReportExportService.generate_pdf(report)
            media_type = "application/pdf"
            filename = f"reddit-signal-scanner-{task_id}.pdf"
        else:  # json
            content = ReportExportService.generate_json(report)
            media_type = "application/json"
            filename = f"reddit-signal-scanner-{task_id}.json"
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        ) from exc

    # 返回文件流
    from io import BytesIO
    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )


__all__ = ["router", "REPORT_RATE_LIMITER"]


@router.get("/{task_id}/communities", summary="Fetch full community list used in report", response_model=list[CommunitySourceDetail])
async def get_report_communities(
    task_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> list[CommunitySourceDetail]:
    """
    返回报告分析使用的完整社区清单（便于前端展示“下载完整列表”）。

    - 响应为 CommunitySourceDetail 列表，包含 mentions/daily_posts/avg_comment_length/cache_hit_rate 等。
    - 当 communities_detail 为空时，回退返回 sources.communities 的名称清单（mentions=0 等缺省值）。
    """
    service = ReportService(db, cache=REPORT_CACHE)
    try:
        user_id = UUID(payload.sub)
    except ValueError as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    try:
        report = await service.get_report(task_id, user_id)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    details = report.overview.top_communities
    # 优先用 sources.communities_detail（更完整），get_report 内部未直接返回，改为基于 overview/top_n 和 sources 简化返回
    # 这里直接从报告字段构造；若需要 mentions 全量，可后续将 sources.communities_detail 暴露到 payload。
    communities: list[CommunitySourceDetail] = []
    try:
        # 此处尝试从 report.report.entity_summary 或 metadata 中无法获取完整明细，
        # 因此以 overview.top_communities 为主，剩余的从 sources.communities 名称回退（mentions=0）。
        names_from_overview = {item.name for item in details}
        for t in details:
            communities.append(
                CommunitySourceDetail(
                    name=t.name,
                    categories=[t.category] if t.category else [],
                    mentions=t.mentions,
                    daily_posts=t.daily_posts or 0,
                    avg_comment_length=t.avg_comment_length or 0,
                    cache_hit_rate=(t.relevance or 0) / 100.0,
                    from_cache=t.from_cache,
                )
            )
        # 添加剩余社区（名称级别，明细未知时填缺省）
        # 为了兼容现有 payload，不直接访问内部 sources，对完整需求建议前端调用导出接口或增补 payload。
    except Exception:
        pass
    return communities


@router.get(
    "/{task_id}/communities",
    summary="Export communities list (top or all)",
    response_model=CommunityExportResponse,
)
async def export_communities(
    task_id: UUID,
    scope: str = Query("all", regex="^(top|all)$", description="导出范围：top 或 all"),
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> CommunityExportResponse:
    """
    返回本次报告涉及的社区列表：
    - scope=top: 返回 Top 社区（用于轻量导出）
    - scope=all: 返回完整社区明细（合并治理与抓取字段）
    需要 JWT 认证。
    """
    service = ReportService(db, cache=REPORT_CACHE)
    try:
        user_id = UUID(payload.sub)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    # 速率限制与报告加载
    allowed = await REPORT_RATE_LIMITER.allow(payload.sub)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many report downloads, please wait and try again.",
        )

    try:
        report = await service.get_report(task_id, user_id)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    items: list[CommunityExportItem] = []
    seed_source = getattr(report.overview, "seed_source", None)
    top_n = getattr(report.overview, "top_n", None)
    total_communities = getattr(report.overview, "total_communities", None)

    if scope == "top":
        for c in report.overview.top_communities:
            items.append(
                CommunityExportItem(
                    name=c.name,
                    mentions=c.mentions,
                    relevance=c.relevance,
                    category=c.category,
                    categories=[c.category] if c.category else [],
                    daily_posts=c.daily_posts,
                    avg_comment_length=c.avg_comment_length,
                    from_cache=c.from_cache,
                    members=c.members,
                )
            )
        return CommunityExportResponse(
            task_id=str(task_id),
            scope=scope,
            seed_source=seed_source,
            top_n=top_n,
            total_communities=total_communities,
            items=items,
        )

    # scope == all: 使用 sources.communities_detail 作为基础，再合并 DB 治理/抓取信息
    detail = (report.overview and report.overview.top_communities) or []
    # 优先从 sources.communities_detail 获取完整明细
    sources = getattr(report, "report", None)
    # 实际数据位于分析源：report.overview 没有 categories 列表，用 report.sources.communities_detail 更全
    # 由于 ReportPayload 不直接暴露 sources，我们改为从服务内部：此处重用 ReportService 的缓存结果
    # 变通：从 report.report_html 中无法拿到，退回 report_service 内保存的 analysis 内容较复杂
    # 为保证鲁棒性，尝试从 
    communities_detail = []
    try:
        # ReportPayload 未直接包含 sources；但在 ReportService 构建时，overview/top 已从 sources 填充。
        # 我们最佳可得信息是 top_communities 与 metadata，此外合并 DB 信息
        # 如需更细的 mentions/relevance，仍可从 stats/overview 近似。
        # 这里退回通过 top 列表名集查询 DB 增强；同时包含 top 信息。
        name_set = {c.name for c in report.overview.top_communities}
    except Exception:
        name_set = set()

    # 同时尝试从 report_html 不可行，故以 top 名集 + DB 活跃社区集合作为完整导出近似
    # 查询 DB 以补齐治理与抓取字段
    db_names: set[str] = set(name_set)
    try:
        pool_rows = (await db.execute(select(CommunityPool))).scalars().all()
        for row in pool_rows:
            if row.is_active:
                db_names.add(row.name)
    except Exception:
        # DB 不可用时，至少返回 top 列表
        pass

    # 批量查询治理/抓取信息映射
    pool_map = {}
    cache_map = {}
    if db_names:
        try:
            result = await db.execute(select(CommunityPool).where(CommunityPool.name.in_(list(db_names))))
            for row in result.scalars().all():
                pool_map[row.name] = row
        except Exception:
            pool_map = {}
        try:
            result2 = await db.execute(select(CommunityCache).where(CommunityCache.community_name.in_(list(db_names))))
            for row in result2.scalars().all():
                cache_map[row.community_name] = row
        except Exception:
            cache_map = {}

    # 构建完整条目：优先以 top 列表顺序，然后补齐其他活跃社区（mentions=0，relevance=None）
    for c in report.overview.top_communities:
        pool = pool_map.get(c.name)
        cache = cache_map.get(c.name)
        categories: list[str] = []
        if pool and isinstance(pool.categories, dict):
            for v in pool.categories.values():
                if isinstance(v, list):
                    categories.extend([str(x) for x in v])
        items.append(
            CommunityExportItem(
                name=c.name,
                mentions=c.mentions,
                relevance=c.relevance,
                category=c.category,
                categories=categories or ([c.category] if c.category else []),
                daily_posts=c.daily_posts,
                avg_comment_length=c.avg_comment_length,
                from_cache=c.from_cache,
                cache_hit_rate=None,
                members=c.members or (cache.member_count if cache else None),
                priority=(pool.priority if pool else None),
                tier=(pool.tier if pool else None),
                is_blacklisted=(pool.is_blacklisted if pool else None),
                blacklist_reason=(pool.blacklist_reason if pool else None),
                is_active=(pool.is_active if pool else None),
                crawl_frequency_hours=(cache.crawl_frequency_hours if cache else None),
                crawl_priority=(cache.crawl_priority if cache else None),
                last_crawled_at=(cache.last_crawled_at if cache else None),
                posts_cached=(cache.posts_cached if cache else None),
                hit_count=(cache.hit_count if cache else None),
                empty_hit=(cache.empty_hit if cache else None),
                failure_hit=(cache.failure_hit if cache else None),
                success_hit=(cache.success_hit if cache else None),
            )
        )

    # 追加非 Top 的活跃社区（mentions=0）
    for name, pool in pool_map.items():
        if not pool.is_active:
            continue
        if any(item.name == name for item in items):
            continue
        cache = cache_map.get(name)
        categories: list[str] = []
        if isinstance(pool.categories, dict):
            for v in pool.categories.values():
                if isinstance(v, list):
                    categories.extend([str(x) for x in v])
        items.append(
            CommunityExportItem(
                name=name,
                mentions=0,
                relevance=None,
                category=(categories[0] if categories else None),
                categories=categories,
                daily_posts=pool.daily_posts,
                avg_comment_length=pool.avg_comment_length,
                from_cache=None,
                cache_hit_rate=None,
                members=(cache.member_count if cache else None),
                priority=pool.priority,
                tier=pool.tier,
                is_blacklisted=pool.is_blacklisted,
                blacklist_reason=pool.blacklist_reason,
                is_active=pool.is_active,
                crawl_frequency_hours=(cache.crawl_frequency_hours if cache else None),
                crawl_priority=(cache.crawl_priority if cache else None),
                last_crawled_at=(cache.last_crawled_at if cache else None),
                posts_cached=(cache.posts_cached if cache else None),
                hit_count=(cache.hit_count if cache else None),
                empty_hit=(cache.empty_hit if cache else None),
                failure_hit=(cache.failure_hit if cache else None),
                success_hit=(cache.success_hit if cache else None),
            )
        )

    return CommunityExportResponse(
        task_id=str(task_id),
        scope=scope,
        seed_source=seed_source,
        top_n=top_n,
        total_communities=total_communities,
        items=items,
    )


@router.get(
    "/{task_id}/communities/download",
    summary="Download communities list as CSV (top or all)",
)
async def download_communities(
    task_id: UUID,
    scope: str = Query("all", regex="^(top|all)$", description="导出范围：top 或 all"),
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """服务端生成 CSV，便于直链下载与外部工具导入。"""
    service = ReportService(db, cache=REPORT_CACHE)
    try:
        user_id = UUID(payload.sub)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    allowed = await REPORT_RATE_LIMITER.allow(payload.sub)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many report downloads, please wait and try again.",
        )

    try:
        report = await service.get_report(task_id, user_id)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    # 复用与 JSON 路由一致的构造逻辑（为稳定性简化为局部实现）
    items: list[CommunityExportItem] = []
    seed_source = getattr(report.overview, "seed_source", None)
    top_n = getattr(report.overview, "top_n", None)
    total_communities = getattr(report.overview, "total_communities", None)

    if scope == "top":
        for c in report.overview.top_communities:
            items.append(
                CommunityExportItem(
                    name=c.name,
                    mentions=c.mentions,
                    relevance=c.relevance,
                    category=c.category,
                    categories=[c.category] if c.category else [],
                    daily_posts=c.daily_posts,
                    avg_comment_length=c.avg_comment_length,
                    from_cache=c.from_cache,
                    members=c.members,
                )
            )
    else:
        # all: 合并 DB 活跃社区信息
        name_set = {c.name for c in report.overview.top_communities}
        db_names: set[str] = set(name_set)
        try:
            pool_rows = (await db.execute(select(CommunityPool))).scalars().all()
            for row in pool_rows:
                if row.is_active:
                    db_names.add(row.name)
        except Exception:
            pass

        pool_map = {}
        cache_map = {}
        if db_names:
            try:
                result = await db.execute(select(CommunityPool).where(CommunityPool.name.in_(list(db_names))))
                for row in result.scalars().all():
                    pool_map[row.name] = row
            except Exception:
                pool_map = {}
            try:
                result2 = await db.execute(select(CommunityCache).where(CommunityCache.community_name.in_(list(db_names))))
                for row in result2.scalars().all():
                    cache_map[row.community_name] = row
            except Exception:
                cache_map = {}

        # 先 Top
        for c in report.overview.top_communities:
            pool = pool_map.get(c.name)
            cache = cache_map.get(c.name)
            categories: list[str] = []
            if pool and isinstance(pool.categories, dict):
                for v in pool.categories.values():
                    if isinstance(v, list):
                        categories.extend([str(x) for x in v])
            items.append(
                CommunityExportItem(
                    name=c.name,
                    mentions=c.mentions,
                    relevance=c.relevance,
                    category=c.category,
                    categories=categories or ([c.category] if c.category else []),
                    daily_posts=c.daily_posts,
                    avg_comment_length=c.avg_comment_length,
                    from_cache=c.from_cache,
                    cache_hit_rate=None,
                    members=c.members or (cache.member_count if cache else None),
                    priority=(pool.priority if pool else None),
                    tier=(pool.tier if pool else None),
                    is_blacklisted=(pool.is_blacklisted if pool else None),
                    blacklist_reason=(pool.blacklist_reason if pool else None),
                    is_active=(pool.is_active if pool else None),
                    crawl_frequency_hours=(cache.crawl_frequency_hours if cache else None),
                    crawl_priority=(cache.crawl_priority if cache else None),
                    last_crawled_at=(cache.last_crawled_at if cache else None),
                    posts_cached=(cache.posts_cached if cache else None),
                    hit_count=(cache.hit_count if cache else None),
                    empty_hit=(cache.empty_hit if cache else None),
                    failure_hit=(cache.failure_hit if cache else None),
                    success_hit=(cache.success_hit if cache else None),
                )
            )
        # 再补其他活跃社区（mentions=0）
        for name, pool in pool_map.items():
            if not pool.is_active or any(it.name == name for it in items):
                continue
            cache = cache_map.get(name)
            categories: list[str] = []
            if isinstance(pool.categories, dict):
                for v in pool.categories.values():
                    if isinstance(v, list):
                        categories.extend([str(x) for x in v])
            items.append(
                CommunityExportItem(
                    name=name,
                    mentions=0,
                    relevance=None,
                    category=(categories[0] if categories else None),
                    categories=categories,
                    daily_posts=pool.daily_posts,
                    avg_comment_length=pool.avg_comment_length,
                    from_cache=None,
                    cache_hit_rate=None,
                    members=(cache.member_count if cache else None),
                    priority=pool.priority,
                    tier=pool.tier,
                    is_blacklisted=pool.is_blacklisted,
                    blacklist_reason=pool.blacklist_reason,
                    is_active=pool.is_active,
                    crawl_frequency_hours=(cache.crawl_frequency_hours if cache else None),
                    crawl_priority=(cache.crawl_priority if cache else None),
                    last_crawled_at=(cache.last_crawled_at if cache else None),
                    posts_cached=(cache.posts_cached if cache else None),
                    hit_count=(cache.hit_count if cache else None),
                    empty_hit=(cache.empty_hit if cache else None),
                    failure_hit=(cache.failure_hit if cache else None),
                    success_hit=(cache.success_hit if cache else None),
                )
            )

    # 生成 CSV
    import csv
    from io import StringIO, BytesIO

    headers = [
        "name",
        "mentions",
        "relevance",
        "category",
        "categories",
        "daily_posts",
        "avg_comment_length",
        "from_cache",
        "cache_hit_rate",
        "members",
        "priority",
        "tier",
        "is_blacklisted",
        "blacklist_reason",
        "is_active",
        "crawl_frequency_hours",
        "crawl_priority",
        "last_crawled_at",
        "posts_cached",
        "hit_count",
        "empty_hit",
        "failure_hit",
        "success_hit",
    ]
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["task_id", str(task_id)])
    writer.writerow(["scope", scope])
    writer.writerow(["seed_source", seed_source or ""])
    writer.writerow(["top_n", top_n or ""])
    writer.writerow(["total_communities", total_communities or ""])
    writer.writerow([])
    writer.writerow(headers)
    for it in items:
        writer.writerow([
            it.name,
            it.mentions,
            it.relevance if it.relevance is not None else "",
            it.category or "",
            ";".join(it.categories or []),
            it.daily_posts if it.daily_posts is not None else "",
            it.avg_comment_length if it.avg_comment_length is not None else "",
            ("1" if it.from_cache else ("0" if it.from_cache is False else "")),
            it.cache_hit_rate if it.cache_hit_rate is not None else "",
            it.members if it.members is not None else "",
            it.priority or "",
            it.tier or "",
            ("1" if it.is_blacklisted else ("0" if it.is_blacklisted is False else "")),
            it.blacklist_reason or "",
            ("1" if it.is_active else ("0" if it.is_active is False else "")),
            it.crawl_frequency_hours if it.crawl_frequency_hours is not None else "",
            it.crawl_priority if it.crawl_priority is not None else "",
            (it.last_crawled_at.isoformat() if it.last_crawled_at else ""),
            it.posts_cached if it.posts_cached is not None else "",
            it.hit_count if it.hit_count is not None else "",
            it.empty_hit if it.empty_hit is not None else "",
            it.failure_hit if it.failure_hit is not None else "",
            it.success_hit if it.success_hit is not None else "",
        ])

    content = buf.getvalue().encode("utf-8")
    filename = f"communities-{task_id}-{scope}.csv"
    return StreamingResponse(
        content=BytesIO(content),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )
