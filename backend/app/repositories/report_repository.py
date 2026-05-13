from __future__ import annotations

import logging
import time
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis import Analysis
from app.models.community_cache import CommunityCache
from app.models.task import Task


logger = logging.getLogger(__name__)


class ReportRepository:
    """Data access layer for report-related queries."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_task_with_analysis(self, task_id: UUID) -> Optional[Task]:
        """Load a task with its analysis and report using efficient eager loading."""
        start = time.perf_counter()
        task = await self._db.get(
            Task,
            task_id,
            options=[
                selectinload(Task.analysis).selectinload(Analysis.report),
                selectinload(Task.user),
            ],
        )
        elapsed = time.perf_counter() - start
        logger.debug("Fetched report task %s in %.4fs", task_id, elapsed)
        return task

    async def get_community_member_count(self, community_name: str) -> int | None:
        """Load member count for a community from cache table."""
        result = await self._db.execute(
            select(CommunityCache.member_count).where(
                CommunityCache.community_name == community_name
            )
        )
        return result.scalar_one_or_none()


__all__ = ["ReportRepository"]
