from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Protocol, cast

from starlette.types import ASGIApp, Message, Receive, Scope, Send

ENABLE_ROUTE_METRICS_ENV = "ENABLE_ROUTE_METRICS"
DEFAULT_ROUTE_METRICS_KEY_PREFIX = "metrics:route_calls"
DEFAULT_ROUTE_METRICS_TTL_SECONDS = 2 * 60 * 60


class RouteMetricsRedisClient(Protocol):
    async def hincrby(self, key: str, field: str, amount: int = 1) -> int: ...

    async def expire(self, key: str, time: int) -> bool: ...


def _env_flag(name: str) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _classify_endpoint_module(module: str | None) -> str:
    if not module:
        return "other"
    if module.startswith("app.api.v1.endpoints."):
        return "golden"
    if module.startswith("app.api.routes."):
        return "legacy"
    return "other"


def _route_template_from_scope(scope: Scope) -> str:
    route = scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str) and path:
        return path
    fallback = scope.get("path")
    return fallback if isinstance(fallback, str) else "/"


def _bucket_key(prefix: str) -> str:
    minute_bucket = int(datetime.now(timezone.utc).timestamp() // 60)
    return f"{prefix}:{minute_bucket}"


class RouteMetricsMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        key_prefix: str = DEFAULT_ROUTE_METRICS_KEY_PREFIX,
        ttl_seconds: int = DEFAULT_ROUTE_METRICS_TTL_SECONDS,
        enabled_env: str = ENABLE_ROUTE_METRICS_ENV,
    ) -> None:
        self.app = app
        self._key_prefix = key_prefix
        self._ttl_seconds = ttl_seconds
        self._enabled_env = enabled_env

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not _env_flag(self._enabled_env):
            await self.app(scope, receive, send)
            return

        recorded = False
        response_status: int | None = None

        async def send_wrapper(message: Message) -> None:
            nonlocal recorded
            nonlocal response_status
            if not recorded and message.get("type") == "http.response.start":
                recorded = True
                status = message.get("status")
                try:
                    response_status = int(status) if status is not None else None
                except (TypeError, ValueError):
                    response_status = None
                await self._record(scope, status_code=response_status)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            # Best-effort metrics: record as 500 when no response start occurred.
            if not recorded:
                await self._record(scope, status_code=500)
            raise
        finally:
            if not recorded:
                await self._record(scope, status_code=response_status)

    async def _record(self, scope: Scope, *, status_code: int | None = None) -> None:
        client = self._get_redis_client(scope)
        if client is None:
            return

        endpoint = scope.get("endpoint")
        module = getattr(endpoint, "__module__", None)
        group = _classify_endpoint_module(module)
        method = scope.get("method", "GET")
        method_upper = method.upper() if isinstance(method, str) else "GET"
        path = _route_template_from_scope(scope)

        key = _bucket_key(self._key_prefix)
        try:
            await client.hincrby(key, f"{group}|_total", 1)
            await client.hincrby(key, f"{group}|{method_upper}|{path}", 1)
            if isinstance(status_code, int) and status_code > 0:
                await client.hincrby(key, f"{group}|status|{status_code}", 1)
                await client.hincrby(key, f"{group}|status_class|{status_code // 100}xx", 1)
            await client.expire(key, self._ttl_seconds)
        except Exception:
            # Best-effort metrics: never break the request path.
            return

    @staticmethod
    def _get_redis_client(scope: Scope) -> RouteMetricsRedisClient | None:
        app = scope.get("app")
        state = getattr(app, "state", None)
        candidate = getattr(state, "route_metrics_redis", None)
        if candidate is None:
            return None
        return cast(RouteMetricsRedisClient, candidate)


__all__ = [
    "DEFAULT_ROUTE_METRICS_KEY_PREFIX",
    "DEFAULT_ROUTE_METRICS_TTL_SECONDS",
    "ENABLE_ROUTE_METRICS_ENV",
    "RouteMetricsMiddleware",
]
