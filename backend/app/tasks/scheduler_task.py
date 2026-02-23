from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from app.core.celery_app import celery_app
from app.services.scheduler_service import recalibrate_crawl_frequencies
from app.db.session import SessionFactory

logger = logging.getLogger(__name__)


async def _run_recalibration() -> Dict[str, Any]:
    async with SessionFactory() as db:
        result = await recalibrate_crawl_frequencies(db)
    return result


@celery_app.task(name="tasks.recalibrate_community_schedules")  # type: ignore[misc]
def recalibrate_community_schedules() -> Dict[str, Any]:
    """
    周期性任务：基于 R-F-E 指标自动调整社区抓取频率。
    """
    result = asyncio.run(_run_recalibration())
    logger.info("Recalibration complete: %s", result)
    return result
