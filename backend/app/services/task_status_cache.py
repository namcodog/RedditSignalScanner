"""
Redis-backed task status cache used for near-real-time progress polling.

The cache mirrors PostgreSQL state transitions but allows the API layer
to serve quick responses without hitting the database for every poll.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import (TYPE_CHECKING, Any, Dict, Optional, Protocol, TypeVar,
                    cast, runtime_checkable)

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_STATUS_CACHE_URL = os.getenv(
    "TASK_STATUS_REDIS_URL", "redis://localhost:6379/3"
)
DEFAULT_STATUS_TTL_SECONDS = int(os.getenv("TASK_STATUS_TTL_SECONDS", "3600"))

if TYPE_CHECKING:
    from app.models.task import TaskStatus as TaskStatusEnum

logger = logging.getLogger(__name__)


@dataclass
class TaskStatusPayload:
    """Structured representation of cached task status."""

    task_id: str
    status: str
    progress: int
    message: str
    error: Optional[str] = None
    updated_at: str | None = None

    def encode(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def decode(raw: str) -> "TaskStatusPayload":
        data: Dict[str, Any] = json.loads(raw)
        return TaskStatusPayload(
            task_id=data["task_id"],
            status=data["status"],
            progress=int(data.get("progress", 0)),
            message=data.get("message", ""),
            error=data.get("error"),
            updated_at=data.get("updated_at"),
        )


T = TypeVar("T")


@runtime_checkable
class RedisClient(Protocol[T]):
    async def set(self, key: str, value: T, ex: int | None = ...) -> Any:
        ...

    async def get(self, key: str) -> T | None:
        ...

    async def delete(self, key: str) -> Any:
        ...


class TaskStatusCache:
    """Thin wrapper around Redis for task status entries."""

    def __init__(self, redis_url: str = DEFAULT_STATUS_CACHE_URL) -> None:
        client = Redis.from_url(redis_url, decode_responses=True)
        self._redis: RedisClient[str] = cast(RedisClient[str], client)

    @property
    def redis(self) -> RedisClient[str]:
        return self._redis

    async def set_status(
        self,
        payload: TaskStatusPayload,
        ttl_seconds: int = DEFAULT_STATUS_TTL_SECONDS,
    ) -> None:
        key = self._build_key(payload.task_id)
        if payload.updated_at is None:
            payload.updated_at = datetime.now(timezone.utc).isoformat()
        try:
            await self.redis.set(key, payload.encode(), ex=ttl_seconds)
        except Exception as exc:  # pragma: no cover - depends on Redis availability
            logger.warning("Unable to persist task status to Redis: %s", exc)

    async def get_status(
        self,
        task_id: str,
        session: AsyncSession | None = None,
        *,
        repopulate: bool = True,
    ) -> Optional[TaskStatusPayload]:
        key = self._build_key(task_id)
        try:
            raw = await self.redis.get(key)
        except Exception as exc:  # pragma: no cover - depends on Redis availability
            logger.warning("Unable to read task status from Redis: %s", exc)
            raw = None

        if raw is None:
            if session is None:
                return None

            fallback = await self._load_from_db(task_id, session)
            if fallback is None:
                return None

            if repopulate:
                await self.set_status(fallback)
            return fallback

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return TaskStatusPayload.decode(raw)

    async def clear_status(self, task_id: str) -> None:
        try:
            await self.redis.delete(self._build_key(task_id))
        except Exception as exc:  # pragma: no cover
            logger.warning("Unable to delete task status from Redis: %s", exc)

    @staticmethod
    def _build_key(task_id: str) -> str:
        return f"task-status:{task_id}"

    async def sync_to_db(
        self, payload: TaskStatusPayload, session: AsyncSession
    ) -> None:
        try:
            task_uuid = uuid.UUID(payload.task_id)
        except ValueError:
            return

        from app.models.task import Task as TaskModel  # Local import
        from app.models.task import TaskStatus

        task: TaskModel | None = await session.get(TaskModel, task_uuid)
        if task is None:
            return

        status_value = TaskStatus(payload.status)
        task.status = status_value
        if payload.error is not None:
            task.error_message = payload.error
        task.updated_at = datetime.now(timezone.utc)
        await session.commit()

    async def _load_from_db(
        self, task_id: str, session: AsyncSession
    ) -> Optional[TaskStatusPayload]:
        try:
            task_uuid = uuid.UUID(task_id)
        except ValueError:
            return None

        from app.models.task import \
            Task as TaskModel  # Local import to avoid cycles
        from app.models.task import TaskStatus

        task: TaskModel | None = await session.get(TaskModel, task_uuid)
        if task is None:
            return None

        status_value = task.status
        progress = self._default_progress(status_value)
        message = self._default_message(status_value)
        error = task.error_message
        updated_at = (task.updated_at or datetime.now(timezone.utc)).isoformat()

        return TaskStatusPayload(
            task_id=task_id,
            status=status_value.value,
            progress=progress,
            message=message,
            error=error,
            updated_at=updated_at,
        )

    @staticmethod
    def _default_progress(status: "TaskStatusEnum") -> int:
        from app.models.task import TaskStatus  # Local import

        mapping: Dict[TaskStatus, int] = {
            TaskStatus.PENDING: 0,
            TaskStatus.PROCESSING: 50,
            TaskStatus.COMPLETED: 100,
            TaskStatus.FAILED: 0,
        }
        return mapping.get(status, 0)

    @staticmethod
    def _default_message(status: "TaskStatusEnum") -> str:
        from app.models.task import TaskStatus  # Local import

        mapping: Dict[TaskStatus, str] = {
            TaskStatus.PENDING: "任务排队中",
            TaskStatus.PROCESSING: "任务正在处理",
            TaskStatus.COMPLETED: "分析完成",
            TaskStatus.FAILED: "任务失败",
        }
        return mapping.get(status, "")


__all__ = ["TaskStatusCache", "TaskStatusPayload"]
