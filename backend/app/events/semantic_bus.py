"""轻量级语义事件总线（进程内）。"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable, DefaultDict


class Events:
    LEXICON_UPDATED = "lexicon.updated"
    CANDIDATE_APPROVED = "candidate.approved"
    REPORT_COMPLETED = "report.completed"
    TIER_ADJUSTED = "tier.adjusted"


class SemanticEventBus:
    def __init__(self) -> None:
        self._subs: DefaultDict[str, list[Callable[[Any], Awaitable[None]]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def subscribe(self, event: str, callback: Callable[[Any], Awaitable[None]]) -> None:
        self._subs[event].append(callback)

    async def publish(self, event: str, payload: Any) -> None:
        async with self._lock:
            callbacks = list(self._subs.get(event, []))
        # 记录日志以便验收检查
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Publishing event: %s", event)
        for cb in callbacks:
            try:
                await cb(payload)
            except Exception:
                # 单个回调失败不影响其他订阅者
                continue


_event_bus: SemanticEventBus | None = None


def get_event_bus() -> SemanticEventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = SemanticEventBus()
    return _event_bus
