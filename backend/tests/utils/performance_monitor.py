from __future__ import annotations

"""
Lightweight performance monitoring helpers for tests (Day14).

Provides:
- Timer context manager
- Async/sync decorators for measuring latency
- Aggregated stats (count, avg, p50/p95/p99) and naive throughput
"""

import contextlib
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Callable, Deque, Dict, Iterable, Optional, TypeVar, Awaitable, Coroutine

T = TypeVar("T")


@dataclass(frozen=True)
class PerfStats:
    count: int
    total_time: float
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    throughput_per_sec: float


class PerformanceMonitor:
    def __init__(self, *, sample_size: int = 1000) -> None:
        self._durations: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=sample_size))
        self._start_time = time.perf_counter()

    def record(self, name: str, seconds: float) -> None:
        if seconds < 0:
            seconds = 0.0
        self._durations[name].append(seconds)

    def stats(self, name: str) -> Optional[PerfStats]:
        data = self._durations.get(name)
        if not data:
            return None
        arr = list(data)
        count = len(arr)
        total = sum(arr)
        avg = (total / max(count, 1)) * 1000.0
        p50 = _percentile_ms(arr, 50)
        p95 = _percentile_ms(arr, 95)
        p99 = _percentile_ms(arr, 99)
        wall = max(1e-9, time.perf_counter() - self._start_time)
        tps = count / wall
        return PerfStats(count, total, avg, p50, p95, p99, tps)

    @contextlib.contextmanager
    def timeit(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            self.record(name, time.perf_counter() - start)

    def monitor(self, name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
        def decorator(fn: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args: Any, **kwargs: Any) -> T:
                start = time.perf_counter()
                try:
                    return fn(*args, **kwargs)
                finally:
                    self.record(name, time.perf_counter() - start)

            return wrapper

        return decorator

    def monitor_async(self, name: str) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Coroutine[Any, Any, T]]]:
        def decorator(fn: Callable[..., Awaitable[T]]):
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                start = time.perf_counter()
                try:
                    return await fn(*args, **kwargs)
                finally:
                    self.record(name, time.perf_counter() - start)

            return wrapper

        return decorator


def _percentile_ms(samples: Iterable[float], percentile: float) -> float:
    arr = sorted(samples)
    if not arr:
        return 0.0
    k = max(0, min(len(arr) - 1, int(round((percentile / 100.0) * (len(arr) - 1)))))
    return arr[k] * 1000.0


__all__ = ["PerformanceMonitor", "PerfStats"]

