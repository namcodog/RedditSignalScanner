from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from fastapi import Query, Request
from redis.asyncio import Redis

from app.core.auth import require_admin
from app.core.config import get_settings
from app.core.security import TokenPayload
from app.interfaces.semantic_provider import SemanticProvider
from app.middleware.route_metrics import DEFAULT_ROUTE_METRICS_KEY_PREFIX
from app.services.semantic.provider_factory import get_semantic_provider as _get_provider

router = APIRouter(prefix="/admin/metrics", tags=["admin"])
PERFORMANCE_DASHBOARD_KEY = os.getenv("PERFORMANCE_DASHBOARD_KEY", "dashboard:performance")


def get_semantic_provider() -> SemanticProvider:
    return _get_provider()


def get_monitoring_redis(request: Request) -> Redis:
    settings = get_settings()
    redis_url = os.getenv("MONITOR_REDIS_URL") or settings.reddit_cache_redis_url
    return Redis.from_url(redis_url, decode_responses=False)


@router.get("/semantic", summary="语义库运行指标")
async def get_semantic_metrics(
    provider: SemanticProvider = Depends(get_semantic_provider),
    payload: TokenPayload = Depends(require_admin),
):
    # 先确保至少加载一次，避免全部为零
    try:
        await provider.load()
    except Exception:
        pass
    metrics = await provider.get_metrics()
    return {
        "db_hits": metrics.db_hits,
        "yaml_fallbacks": metrics.yaml_fallbacks,
        "cache_hit_rate": metrics.cache_hit_rate,
        "last_refresh": metrics.last_refresh,
        "total_terms": metrics.total_terms,
        "load_latency_p95_ms": metrics.load_latency_p95_ms,
    }


@router.get("/routes", summary="路由调用统计（golden vs legacy）")
async def get_route_metrics(
    request: Request,
    payload: TokenPayload = Depends(require_admin),
    minutes: int = Query(60, ge=1, le=720),
    top_n: int = Query(20, ge=0, le=200),
) -> dict[str, object]:
    redis = getattr(request.app.state, "route_metrics_redis", None)
    if redis is None:
        return {"enabled": False}

    now_bucket = int(datetime.now(timezone.utc).timestamp() // 60)
    keys = [
        f"{DEFAULT_ROUTE_METRICS_KEY_PREFIX}:{now_bucket - offset}"
        for offset in range(minutes)
    ]

    pipeline = redis.pipeline()
    for key in keys:
        pipeline.hgetall(key)
    buckets = await pipeline.execute()

    totals: dict[str, int] = {"golden": 0, "legacy": 0, "other": 0}
    route_calls: dict[tuple[str, str, str], int] = defaultdict(int)

    for bucket_data in buckets:
        if not bucket_data:
            continue
        for raw_field, raw_value in bucket_data.items():
            field = (
                raw_field.decode("utf-8", errors="replace")
                if isinstance(raw_field, (bytes, bytearray))
                else str(raw_field)
            )
            value = (
                int(raw_value.decode("utf-8", errors="replace"))
                if isinstance(raw_value, (bytes, bytearray))
                else int(raw_value)
            )
            parts = field.split("|")
            if len(parts) < 2:
                continue
            group = parts[0]
            if len(parts) == 2 and parts[1] == "_total":
                totals[group if group in totals else "other"] += value
                continue
            if len(parts) >= 3:
                method = parts[1]
                path = "|".join(parts[2:])
                route_calls[(group, method, path)] += value

    top_routes = [
        {"group": group, "method": method, "path": path, "calls": calls}
        for (group, method, path), calls in sorted(
            route_calls.items(),
            key=lambda item: (-item[1], item[0][0], item[0][1], item[0][2]),
        )[:top_n]
    ]

    return {
        "enabled": True,
        "window_minutes": minutes,
        "totals": totals,
        "top_routes": top_routes,
    }


@router.get("/contract-health", summary="合同健康度（Phase106-2）")
async def get_contract_health(
    request: Request,
    payload: TokenPayload = Depends(require_admin),
) -> dict[str, object]:
    redis = get_monitoring_redis(request)
    raw = await redis.hget(PERFORMANCE_DASHBOARD_KEY, "contract_health")
    updated_at = await redis.hget(PERFORMANCE_DASHBOARD_KEY, "updated_at")

    def _decode(value: object | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8", errors="replace")
        return str(value)

    raw_text = _decode(raw)
    updated_text = _decode(updated_at)
    if not raw_text:
        return {"enabled": False, "updated_at": updated_text}
    try:
        payload_obj = json.loads(raw_text)
        if not isinstance(payload_obj, dict):
            return {"enabled": False, "updated_at": updated_text}
    except json.JSONDecodeError:
        return {"enabled": False, "updated_at": updated_text}

    return {
        "enabled": True,
        "updated_at": updated_text,
        "contract_health": payload_obj,
    }
