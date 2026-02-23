from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.security import TokenPayload, decode_jwt_token, http_bearer
from app.db.session import get_session
from app.models.hotpost_query import HotpostQuery
from app.schemas.hotpost import (
    HotpostDeepdiveRequest,
    HotpostDeepdiveResponse,
    HotpostSearchRequest,
    HotpostSearchResponse,
)
from app.services.hotpost.service import HotpostService


router = APIRouter(prefix="/hotpost", tags=["hotpost"])
logger = logging.getLogger(__name__)


QUEUE_POLL_INTERVAL_SECONDS = float(os.getenv("HOTPOST_QUEUE_STREAM_POLL_INTERVAL", "1.0"))
QUEUE_HEARTBEAT_SECONDS = float(os.getenv("HOTPOST_QUEUE_STREAM_HEARTBEAT_INTERVAL", "30.0"))


def _hash_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


async def _optional_payload(
    credentials: HTTPAuthorizationCredentials | None,
    settings: Settings,
) -> TokenPayload | None:
    if credentials is None:
        return None
    return await decode_jwt_token(credentials, settings)


@router.post(
    "/search",
    response_model=HotpostSearchResponse,
    summary="Hotpost quick search",
)
async def hotpost_search(
    request: HotpostSearchRequest,
    http_request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> HotpostSearchResponse:
    payload = await _optional_payload(credentials, settings)
    user_id = uuid.UUID(payload.sub) if payload else None
    session_id = http_request.headers.get("X-Session-Id")
    ip_hash = _hash_ip(http_request.client.host if http_request.client else None)

    service = HotpostService(settings=settings, db=db)
    try:
        return await service.search(
            request,
            user_id=user_id,
            session_id=session_id,
            ip_hash=ip_hash,
        )
    except ValidationError:
        logger.exception("Hotpost response validation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="报告生成失败，请稍后重试或缩短关键词。",
        )
    finally:
        await service.close()


@router.get(
    "/result/{query_id}",
    response_model=HotpostSearchResponse,
    summary="Get cached hotpost result",
)
async def hotpost_result(
    query_id: str,
    settings: Settings = Depends(get_settings),
) -> HotpostSearchResponse:
    redis = Redis.from_url(settings.reddit_cache_redis_url, decode_responses=True)
    cached_raw = await redis.get(f"hotpost:result:{query_id}")
    if not cached_raw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    payload = json.loads(cached_raw)
    try:
        return HotpostSearchResponse(**payload)
    except ValidationError:
        logger.exception("Hotpost cached payload validation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="缓存结果结构异常，请重新发起查询。",
        )


async def _hotpost_queue_event_generator(redis: Redis, query_id: str):
    key = f"hotpost:queue:{query_id}"
    last_payload: str | None = None
    last_heartbeat = time.monotonic()
    while True:
        payload = await redis.get(key)
        if payload and payload != last_payload:
            try:
                data = json.loads(payload)
            except Exception:
                data = {}
            status_value = data.get("status") or "processing"
            if status_value == "waiting":
                event_name = "queue_update"
            elif status_value == "processing":
                event_name = "progress"
            elif status_value == "completed":
                event_name = "completed"
            elif status_value == "failed":
                event_name = "error"
            else:
                event_name = "progress"
            yield f"event: {event_name}\n"
            yield f"data: {payload}\n\n"
            last_payload = payload
            if status_value in {"completed", "failed"}:
                break

        now = time.monotonic()
        if now - last_heartbeat >= QUEUE_HEARTBEAT_SECONDS:
            yield "event: ping\n"
            yield "data: {}\n\n"
            last_heartbeat = now

        await asyncio.sleep(QUEUE_POLL_INTERVAL_SECONDS)


@router.get(
    "/stream/{query_id}",
    summary="Hotpost queue streaming (SSE)",
    responses={
        200: {
            "description": "SSE Stream",
            "content": {"text/event-stream": {}}
        }
    }
)
async def hotpost_stream(
    query_id: str,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    redis = Redis.from_url(settings.reddit_cache_redis_url, decode_responses=True)
    generator = _hotpost_queue_event_generator(redis, query_id)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/deepdive",
    response_model=HotpostDeepdiveResponse,
    summary="Create deepdive token for full report",
)
async def hotpost_deepdive(
    request: HotpostDeepdiveRequest,
    payload: TokenPayload = Depends(decode_jwt_token),
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> HotpostDeepdiveResponse:
    try:
        query_id = uuid.UUID(request.query_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid query_id",
        ) from exc

    record: HotpostQuery | None = await db.get(HotpostQuery, query_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found",
        )

    seed = {
        "product_desc": request.product_desc or record.query,
        "seed_subreddits": request.seed_subreddits or (record.subreddits or []),
        "mode": record.mode,
        "time_filter": record.time_filter,
        "query_id": str(query_id),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    token = uuid.uuid4().hex
    redis = Redis.from_url(settings.reddit_cache_redis_url, decode_responses=True)
    await redis.setex(
        f"hotpost:deepdive:{token}",
        30 * 60,
        json.dumps(seed, ensure_ascii=False),
    )

    return HotpostDeepdiveResponse(deepdive_token=token, expires_in_seconds=30 * 60)


__all__ = ["router"]
