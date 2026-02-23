"""Robust semantic loader with DB/YAML strategies, cache and metrics."""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.semantic_bus import Events, get_event_bus
from app.interfaces.semantic_provider import (
    SemanticLoadStrategy,
    SemanticMetrics,
    SemanticProvider,
)


@dataclass(slots=True)
class _CacheEntry:
    loaded_at: float
    payload: Any


class RobustSemanticLoader(SemanticProvider):
    """语义库加载器：支持 DB/YAML 策略、缓存、事件驱动 reload。"""

    def __init__(
        self,
        session_factory: Callable[[], Awaitable[AsyncSession]] | None = None,
        *,
        fallback_yaml: Path | str = Path("backend/config/semantic_sets/unified_lexicon.yml"),
        strategy: SemanticLoadStrategy = SemanticLoadStrategy.DB_YAML_FALLBACK,
        ttl_seconds: int = 300,
    ) -> None:
        self._session_factory = session_factory
        self._fallback_yaml = Path(fallback_yaml)
        self._strategy = strategy
        self._ttl = max(1, ttl_seconds)
        self._cache: Optional[_CacheEntry] = None
        self._lock = asyncio.Lock()
        self._db_hits = 0
        self._yaml_fallbacks = 0
        self._load_latencies: list[float] = []
        get_event_bus().subscribe(Events.LEXICON_UPDATED, self._on_lexicon_updated)

    async def load(self):
        async with self._lock:
            if self._cache and (time.monotonic() - self._cache.loaded_at) < self._ttl:
                return self._cache.payload
            start = time.monotonic()
            payload = await self._load_by_strategy()
            latency = (time.monotonic() - start) * 1000.0
            self._load_latencies.append(latency)
            self._cache = _CacheEntry(loaded_at=time.monotonic(), payload=payload)
            return payload

    async def reload(self) -> None:
        async with self._lock:
            self._cache = None
            await self.load()

    async def get_metrics(self) -> SemanticMetrics:
        last_refresh_dt = None
        if self._cache is not None:
            last_refresh_dt = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._cache.loaded_at))
        cache_hits = 1 if self._cache else 0
        total_requests = len(self._load_latencies) or 1
        cache_hit_rate = cache_hits / max(1, total_requests)
        p95_latency = self._percentile(self._load_latencies, 0.95) if self._load_latencies else 0.0
        return SemanticMetrics(
            db_hits=self._db_hits,
            yaml_fallbacks=self._yaml_fallbacks,
            cache_hit_rate=cache_hit_rate,
            last_refresh=last_refresh_dt,  # type: ignore[arg-type]
            total_terms=self._estimate_terms(self._cache.payload if self._cache else None),
            load_latency_p95_ms=p95_latency,
        )

    async def _load_by_strategy(self):
        if self._strategy == SemanticLoadStrategy.DB_ONLY:
            return await self._load_from_db()
        if self._strategy == SemanticLoadStrategy.YAML_ONLY:
            return self._load_from_yaml()
        try:
            return await self._load_from_db()
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("DB load failed, fallback to YAML: %s", exc)
            self._yaml_fallbacks += 1
            return self._load_from_yaml()

    async def _load_from_db(self):
        if not self._session_factory:
            raise RuntimeError("Session factory not provided for DB load")
        async with await self._session_factory() as session:
            self._db_hits += 1
            # 这里用最小实现：读取 semantic_terms 表，如不存在则返回空
            try:
                rows = await session.execute(
                    "SELECT canonical, metadata FROM semantic_terms"  # type: ignore[arg-type]
                )
                return [{"canonical": r[0], "metadata": r[1]} for r in rows.fetchall()]
            except Exception:
                raise

    def _load_from_yaml(self):
        if not self._fallback_yaml.exists():
            return []
        try:
            content = self._fallback_yaml.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception:
            return []

    async def _on_lexicon_updated(self, _payload: Any) -> None:
        await self.reload()

    @staticmethod
    def _percentile(values: list[float], pct: float) -> float:
        if not values:
            return 0.0
        values_sorted = sorted(values)
        k = int(len(values_sorted) * pct)
        k = min(max(k, 0), len(values_sorted) - 1)
        return values_sorted[k]

    @staticmethod
    def _estimate_terms(payload: Any) -> int:
        if isinstance(payload, list):
            return len(payload)
        if isinstance(payload, dict):
            return len(payload)
        return 0


__all__ = ["RobustSemanticLoader"]
