from __future__ import annotations

import asyncio

from app.utils.asyncio_runner import run


async def _current_loop_id() -> int:
    loop = asyncio.get_running_loop()
    return id(loop)


def test_run_reuses_single_event_loop() -> None:
    """确保多次 run() 复用同一个 loop，避免跨 loop Future 冲突。"""
    first = run(_current_loop_id())
    second = run(_current_loop_id())
    assert first == second

