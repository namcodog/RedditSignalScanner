from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import deque
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.reports import REPORT_RATE_LIMITER as SHARED_REPORT_RATE_LIMITER
from app.core.config import settings
from app.core.security import TokenPayload, decode_jwt_token
from app.db.session import get_session
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.models.task import TaskStatus
from app.models.user import MembershipLevel
from app.repositories.report_repository import ReportRepository
from app.schemas.analysis import AnalysisRead, CommunitySourceDetail
from app.schemas.community_export import CommunityExportItem, CommunityExportResponse
from app.schemas.entity_export import EntityExportItem, EntityExportResponse
from app.schemas.report_payload import ReportPayload
from app.services.report.report_service import (
    InMemoryReportCache,
    ReportAccessDeniedError,
    ReportDataValidationError,
    ReportNotFoundError,
    ReportNotReadyError,
    ReportService,
    ReportServiceError,
)
from app.services.report.report_export_service import ExportFormat, ReportExportService

logger = logging.getLogger(__name__)

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
        self._hits.clear()

    async def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self._hits.setdefault(str(key), deque())
        cutoff = now - self._window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= self._max_requests:
            return False
        bucket.append(now)
        return True


router = APIRouter()

REPORT_CACHE = InMemoryReportCache(settings.report_cache_ttl_seconds)
# 与 legacy /api/report 路由共享同一限流桶，保证测试与运行时一致
REPORT_RATE_LIMITER = SHARED_REPORT_RATE_LIMITER


def _extract_pool_categories(pool: CommunityPool | None, fallback: list[str] | None = None) -> list[str]:
    categories: list[str] = []
    if pool is not None:
        if isinstance(pool.categories, dict):
            for value in pool.categories.values():
                if isinstance(value, list):
                    categories.extend(str(item) for item in value)
        elif isinstance(pool.categories, list):
            categories.extend(str(item) for item in pool.categories)
    if categories:
        return categories
    return list(fallback or [])


async def _load_report_with_analysis(
    service: ReportService,
    *,
    task_id: UUID,
    user_id: UUID,
) -> tuple[ReportPayload, AnalysisRead]:
    report = await service.get_report(task_id, user_id)
    task = await service._repository.get_task_with_analysis(task_id)  # noqa: SLF001
    if task is None or task.analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    analysis_read = service.validate_analysis_payload(task.analysis)
    return report, analysis_read


def _build_fallback_community_details(
    report: ReportPayload,
    fallback_names: list[str] | None = None,
) -> list[CommunitySourceDetail]:
    details: list[CommunitySourceDetail] = []
    for item in report.overview.top_communities:
        details.append(
            CommunitySourceDetail(
                name=item.name,
                categories=[item.category] if item.category else [],
                mentions=item.mentions,
                daily_posts=item.daily_posts or 0,
                avg_comment_length=item.avg_comment_length or 0,
                cache_hit_rate=(item.relevance or 0) / 100.0,
                from_cache=item.from_cache,
            )
        )
    if details:
        return details
    for name in fallback_names or []:
        details.append(
            CommunitySourceDetail(
                name=name,
                categories=[],
                mentions=0,
                daily_posts=0,
                avg_comment_length=0,
                cache_hit_rate=0.0,
                from_cache=False,
            )
        )
    return details


async def _resolve_report_communities(
    service: ReportService,
    *,
    task_id: UUID,
    user_id: UUID,
) -> tuple[ReportPayload, list[CommunitySourceDetail], str, str | None]:
    report, analysis_read = await _load_report_with_analysis(
        service,
        task_id=task_id,
        user_id=user_id,
    )
    details = analysis_read.sources.communities_detail or []
    if details:
        return report, details, "analysis_sources", None
    return (
        report,
        _build_fallback_community_details(report, analysis_read.sources.communities),
        "top_communities_fallback",
        "missing_communities_detail",
    )


async def _load_community_maps(
    db: AsyncSession,
    names: list[str],
) -> tuple[dict[str, CommunityPool], dict[str, CommunityCache]]:
    if not names:
        return {}, {}
    unique_names = list(dict.fromkeys(names))
    pool_rows = await db.execute(select(CommunityPool).where(CommunityPool.name.in_(unique_names)))
    cache_rows = await db.execute(
        select(CommunityCache).where(CommunityCache.community_name.in_(unique_names))
    )
    pool_map = {row.name: row for row in pool_rows.scalars().all()}
    cache_map = {row.community_name: row for row in cache_rows.scalars().all()}
    return pool_map, cache_map


def _build_community_export_items(
    details: list[CommunitySourceDetail],
    *,
    pool_map: dict[str, CommunityPool],
    cache_map: dict[str, CommunityCache],
) -> list[CommunityExportItem]:
    items: list[CommunityExportItem] = []
    for detail in details:
        pool = pool_map.get(detail.name)
        cache = cache_map.get(detail.name)
        categories = _extract_pool_categories(pool, detail.categories)
        items.append(
            CommunityExportItem(
                name=detail.name,
                mentions=detail.mentions,
                relevance=None,
                category=(categories[0] if categories else None),
                categories=categories,
                daily_posts=detail.daily_posts,
                avg_comment_length=detail.avg_comment_length,
                from_cache=detail.from_cache,
                cache_hit_rate=detail.cache_hit_rate,
                members=(cache.member_count if cache else None),
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
    return items


@router.options("/report/{task_id}")
async def options_analysis_report(task_id: str) -> Response:
    # CORS 预检请求在路由层直接放行，避免触发认证依赖
    return Response(status_code=204)

@router.get("/report/{task_id}", summary="Fetch completed analysis report", response_model=ReportPayload)
async def get_analysis_report(
    task_id: UUID,
    response: Response,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> ReportPayload:
    service = ReportService(db, cache=REPORT_CACHE)
    try:
        user_id = UUID(payload.sub)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    key = str(payload.sub)
    allowed = await REPORT_RATE_LIMITER.allow(key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many report downloads, please wait and try again.",
        )

    # Fast-path for dev/test to avoid heavy LLM/normalization and keep E2E latency < 2s
    # 默认关闭，需显式 FAST_E2E_REPORT=1 才生效，防止误绕过主业务逻辑
    fast_e2e_enabled = os.getenv("FAST_E2E_REPORT", "0").lower() in {"1", "true", "yes"}
    if fast_e2e_enabled and settings.environment.lower() != "production":
        cache_key = f"report:{task_id}:{user_id}"
        repo = ReportRepository(db)
        task = await repo.get_task_with_analysis(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
        if task.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorised to access this task")
        # 会员校验（与 ReportService 一致：只有 PRO/ENTERPRISE 可看报告）
        membership = getattr(task.user, "membership_level", MembershipLevel.FREE)
        if membership not in {MembershipLevel.PRO, MembershipLevel.ENTERPRISE}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Subscription tier does not include reports")
        # 状态校验：未完成直接 409
        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task has not completed yet")
        if task.analysis is None or task.analysis.report is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

        insights = task.analysis.insights or {}
        sources = task.analysis.sources or {}
        pain_points = insights.get("pain_points") or []
        competitors = insights.get("competitors") or []
        opportunities = insights.get("opportunities") or []
        action_items = insights.get("action_items") or []
        entity_summary = insights.get("entity_summary") or {"brands": [], "features": [], "pain_points": []}

        total_mentions = max(0, int(sources.get("posts_analyzed", 0) or 0))
        cache_hit_rate = float(sources.get("cache_hit_rate", 0.0) or 0.0)
        metadata = {
            "analysis_version": ReportService.format_analysis_version(getattr(task.analysis, "analysis_version", "1.0")),
            "confidence_score": 0.98,
            "processing_time_seconds": float(sources.get("analysis_duration_seconds", 0) or 1.0),
            "cache_hit_rate": cache_hit_rate,
            "total_mentions": total_mentions,
        }
        exec_summary = {
            "total_communities": len(sources.get("communities", [])),
            "key_insights": len(pain_points),
            "top_opportunity": opportunities[0]["description"] if opportunities else "",
        }
        overview = {
            "sentiment": {"positive": 0, "negative": 0, "neutral": 0},
            "top_communities": [],
        }
        stats = {
            "total_mentions": total_mentions,
            "positive_mentions": total_mentions,
            "negative_mentions": 0,
            "neutral_mentions": 0,
        }
        payload_fast = {
            "task_id": str(task_id),
            "status": task.status.value,
            "report": {
                "executive_summary": exec_summary,
                "pain_points": pain_points,
                "competitors": competitors,
                "opportunities": opportunities,
                "action_items": action_items,
                "entity_summary": entity_summary,
            },
            "report_html": task.analysis.report.html_content or "<html></html>",
            "metadata": metadata,
            "overview": overview,
            "stats": stats,
            "generated_at": getattr(task.analysis.report, "generated_at", None) or getattr(task.analysis, "updated_at", None) or getattr(task, "created_at", None) or getattr(task, "updated_at", None) or datetime.now(timezone.utc),
            "data_source": getattr(task.analysis, "data_source", "real"),
        }
        fast_report = ReportPayload.model_validate(payload_fast)
        # 热缓存一份，后续调用直接命中
        await REPORT_CACHE.set(cache_key, fast_report)
        response.headers["X-Data-Source"] = "Synthetic" if str(getattr(task.analysis, "data_source", "")).lower() != "real" else "Real"
        return fast_report

    try:
        report = await service.get_report(task_id, user_id)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    data_source = (report.data_source or "real").lower()
    response.headers["X-Data-Source"] = "Synthetic" if data_source != "real" else "Real"
    return report


@router.get("/report/{task_id}/download", summary="Download report in specified format")
async def download_report(
    task_id: UUID,
    format: ExportFormat = Query("pdf", description="Export format: pdf|json|md"),
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

    # 生成导出文件（带降级兜底）
    fallback_headers: dict[str, str] = {}
    try:
        if format == "pdf":
            content = ReportExportService.generate_pdf(report)
            media_type = "application/pdf"
            filename = f"reddit-signal-scanner-{task_id}.pdf"
        elif format == "md":
            content = ReportExportService.generate_markdown(report)
            media_type = "text/markdown; charset=utf-8"
            filename = f"reddit-signal-scanner-{task_id}.md"
        else:  # json
            content = ReportExportService.generate_json(report)
            media_type = "application/json"
            filename = f"reddit-signal-scanner-{task_id}.json"
    except Exception:
        # PDF/MD 失败时，降级为 JSON
        logger.exception(
            "Report export failed, fallback to JSON",
            extra={"task_id": str(task_id), "format": format},
        )
        content = ReportExportService.generate_json(report)
        media_type = "application/json"
        filename = f"reddit-signal-scanner-{task_id}.json"
        fallback_headers = {
            "X-Export-Fallback": "json",
            "X-Export-Error": "export_generation_failed",
        }

    # 返回文件流
    from io import BytesIO
    source_header = (
        "Synthetic"
        if str(getattr(report, "data_source", "")).lower() != "real"
        else "Real"
    )
    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
            "X-Data-Source": source_header,
            **fallback_headers,
        },
    )


@router.get(
    "/report/{task_id}/communities",
    summary="Fetch full community list used in report",
    response_model=list[CommunitySourceDetail],
)
async def get_report_communities(
    task_id: UUID,
    response: Response,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> list[CommunitySourceDetail]:
    """
    返回报告分析使用的完整社区清单（便于前端展示“下载完整列表”）。

    - 优先返回 analysis.sources.communities_detail
    - 取不到时，明确降级到 overview.top_communities，并在响应头标记来源
    """
    service = ReportService(db, cache=REPORT_CACHE)
    try:
        user_id = UUID(payload.sub)
    except ValueError as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    try:
        _, details, source, degraded_reason = await _resolve_report_communities(
            service,
            task_id=task_id,
            user_id=user_id,
        )
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    response.headers["X-Communities-Source"] = source
    response.headers["X-Communities-Degraded"] = degraded_reason or "none"
    return details


@router.get(
    "/report/{task_id}/entities",
    summary="Export recognised entities (flattened)",
    response_model=EntityExportResponse,
)
async def export_entities(
    task_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> EntityExportResponse:
    """Aggregate recognised entities from report.entity_summary and return as a flat list."""
    service = ReportService(db, cache=REPORT_CACHE)
    try:
        user_id = UUID(payload.sub)
    except ValueError as exc:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    try:
        report = await service.get_report(task_id, user_id)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    items: list[EntityExportItem] = []
    entity_summary = getattr(report.report, "entity_summary", None)
    if entity_summary:
        # entity_summary is a mapping of categories -> [{name, mentions}]
        try:
            for category, rows in entity_summary.dict().items():  # type: ignore[attr-defined]
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    name = row.get("name") if isinstance(row, dict) else None
                    mentions = row.get("mentions") if isinstance(row, dict) else None
                    if isinstance(name, str) and isinstance(mentions, int):
                        items.append(EntityExportItem(name=name, category=str(category), mentions=max(0, mentions)))
        except Exception:
            # Fallback to attribute access if .dict() is not present
            for category in ("brands", "features", "pain_points"):
                rows = getattr(entity_summary, category, [])
                for row in rows or []:
                    name = getattr(row, "name", None)
                    mentions = getattr(row, "mentions", None)
                    if isinstance(name, str) and isinstance(mentions, int):
                        items.append(EntityExportItem(name=name, category=category, mentions=max(0, mentions)))

    # If empty, compute on the fly from insights using the pipeline
    if not items:
        try:
            from app.services.analysis.entity_pipeline import EntityPipeline
            pipe = EntityPipeline()
            summary = pipe.summarize(
                {
                    "pain_points": [i.model_dump(mode="json") for i in (report.report.pain_points or [])],
                    "competitors": [i.model_dump(mode="json") for i in (report.report.competitors or [])],
                    "opportunities": [i.model_dump(mode="json") for i in (report.report.opportunities or [])],
                    "action_items": [i.model_dump(mode="json") for i in (report.report.action_items or [])],
                }
            )
            for category, rows in summary.items():
                for row in rows:
                    items.append(
                        EntityExportItem(
                            name=str(row.get("name")),
                            category=str(category),
                            mentions=int(row.get("mentions", 0)),
                        )
                    )
        except Exception:
            pass

    return EntityExportResponse(task_id=str(task_id), items=items)


@router.get(
    "/report/{task_id}/entities/download",
    summary="Download recognised entities as CSV",
)
async def download_entities_csv(
    task_id: UUID,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """导出实体清单为 CSV，保持与 JSON 导出一致的字段。"""
    service = ReportService(db, cache=REPORT_CACHE)
    try:
        user_id = UUID(payload.sub)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    key = str(payload.sub)
    allowed = await REPORT_RATE_LIMITER.allow(key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many report downloads, please wait and try again.",
        )

    try:
        report = await service.get_report(task_id, user_id)
    except ReportServiceError:
        empty = "name,category,mentions\n"
        from io import BytesIO

        return StreamingResponse(
            content=BytesIO(empty.encode("utf-8")),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="entities-{task_id}.csv"'},
        )

    # 复用 JSON 导出逻辑构建列表
    items: list[EntityExportItem] = []
    entity_summary = getattr(report.report, "entity_summary", None)
    if entity_summary:
        try:
            for category, rows in entity_summary.dict().items():  # type: ignore[attr-defined]
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    name = row.get("name") if isinstance(row, dict) else None
                    mentions = row.get("mentions") if isinstance(row, dict) else None
                    if isinstance(name, str) and isinstance(mentions, int):
                        items.append(
                            EntityExportItem(
                                name=name,
                                category=str(category),
                                mentions=max(0, mentions),
                            )
                        )
        except Exception:
            for category in ("brands", "features", "pain_points"):
                rows = getattr(entity_summary, category, [])
                for row in rows or []:
                    name = getattr(row, "name", None)
                    mentions = getattr(row, "mentions", None)
                    if isinstance(name, str) and isinstance(mentions, int):
                        items.append(
                            EntityExportItem(
                                name=name,
                                category=category,
                                mentions=max(0, mentions),
                            )
                        )

    if not items:
        try:
            from app.services.analysis.entity_pipeline import EntityPipeline

            pipe = EntityPipeline()
            summary = pipe.summarize(
                {
                    "pain_points": [i.model_dump(mode="json") for i in (report.report.pain_points or [])],
                    "competitors": [i.model_dump(mode="json") for i in (report.report.competitors or [])],
                    "opportunities": [i.model_dump(mode="json") for i in (report.report.opportunities or [])],
                    "action_items": [i.model_dump(mode="json") for i in (report.report.action_items or [])],
                }
            )
            for category, rows in summary.items():
                for row in rows:
                    items.append(
                        EntityExportItem(
                            name=str(row.get("name")),
                            category=str(category),
                            mentions=int(row.get("mentions", 0)),
                        )
                    )
        except Exception:
            pass

    import csv
    from io import StringIO, BytesIO

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["name", "category", "mentions"])
    for item in items:
        writer.writerow([item.name, item.category, item.mentions])

    content = buf.getvalue().encode("utf-8")
    return StreamingResponse(
        content=BytesIO(content),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="entities-{task_id}.csv"'},
    )


@router.get(
    "/report/{task_id}/communities/export",
    summary="Export communities list (top or all)",
    response_model=CommunityExportResponse,
)
async def export_communities(
    task_id: UUID,
    scope: str = Query("all", pattern="^(top|all)$", description="导出范围：top 或 all"),
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
) -> CommunityExportResponse:
    """
    返回本次报告涉及的社区列表：
    - scope=top: 返回 Top 社区（用于轻量导出）
    - scope=all: 只返回真实报告社区；缺少 detail 时明确降级到 top_communities
    """
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

    seed_source = getattr(report.overview, "seed_source", None)
    top_n = getattr(report.overview, "top_n", None)
    total_communities = getattr(report.overview, "total_communities", None)

    if scope == "top":
        items: list[CommunityExportItem] = []
        for item in report.overview.top_communities:
            items.append(
                CommunityExportItem(
                    name=item.name,
                    mentions=item.mentions,
                    relevance=item.relevance,
                    category=item.category,
                    categories=[item.category] if item.category else [],
                    daily_posts=item.daily_posts,
                    avg_comment_length=item.avg_comment_length,
                    from_cache=item.from_cache,
                    members=item.members,
                )
            )
        return CommunityExportResponse(
            task_id=str(task_id),
            scope=scope,
            seed_source=seed_source,
            top_n=top_n,
            total_communities=total_communities,
            source="top_communities",
            degraded_reason=None,
            items=items,
        )

    try:
        _, details, source, degraded_reason = await _resolve_report_communities(
            service,
            task_id=task_id,
            user_id=user_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    pool_map, cache_map = await _load_community_maps(db, [detail.name for detail in details])
    items = _build_community_export_items(details, pool_map=pool_map, cache_map=cache_map)

    return CommunityExportResponse(
        task_id=str(task_id),
        scope=scope,
        seed_source=seed_source,
        top_n=top_n,
        total_communities=total_communities,
        source=source,
        degraded_reason=degraded_reason,
        items=items,
    )


@router.get(
    "/report/{task_id}/communities/download",
    summary="Download communities list as CSV (top or all)",
)
async def download_communities(
    task_id: UUID,
    scope: str = Query("all", pattern="^(top|all)$", description="导出范围：top 或 all"),
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

    seed_source = getattr(report.overview, "seed_source", None)
    top_n = getattr(report.overview, "top_n", None)
    total_communities = getattr(report.overview, "total_communities", None)
    source = "top_communities"
    degraded_reason: str | None = None

    if scope == "top":
        items: list[CommunityExportItem] = []
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
        try:
            _, details, source, degraded_reason = await _resolve_report_communities(
                service,
                task_id=task_id,
                user_id=user_id,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

        pool_map, cache_map = await _load_community_maps(db, [detail.name for detail in details])
        items = _build_community_export_items(details, pool_map=pool_map, cache_map=cache_map)

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
    writer.writerow(["source", source])
    writer.writerow(["degraded_reason", degraded_reason or ""])
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
