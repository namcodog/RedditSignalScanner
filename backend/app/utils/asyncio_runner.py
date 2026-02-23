from __future__ import annotations

import asyncio
from typing import Awaitable, TypeVar

T = TypeVar("T")

_LOOP: asyncio.AbstractEventLoop | None = None


def run(coro: Awaitable[T]) -> T:
    """Run an async coroutine on a reusable event loop.

    说明（给 Celery 用）：
    - 同一个进程内反复 `asyncio.run()` 会不断创建/销毁事件循环，
      对 asyncpg + SQLAlchemy 这类长生命周期对象来说，容易出现
      “Future 绑定在旧 loop，但在新 loop 等待”的错误。
    - 这里改成：每个进程只创建一个全局 event loop，并在其上重复
      `run_until_complete`，从而避免跨 loop 的 Future 冲突。
    """
    global _LOOP
    if _LOOP is None or _LOOP.is_closed():
        _LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(_LOOP)
    return _LOOP.run_until_complete(coro)


def shutdown() -> None:
    """Close the reusable event loop (best-effort).

    Tests and local tooling may call this to avoid cross-test interference.
    """
    global _LOOP
    loop = _LOOP
    _LOOP = None
    if loop is None:
        return
    try:
        if not loop.is_closed():
            loop.close()
    except Exception:
        pass


__all__ = ["run", "shutdown"]
