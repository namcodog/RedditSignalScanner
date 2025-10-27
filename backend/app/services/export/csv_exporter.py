"""CSV export service for analysis insights."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.insight import InsightCard
from app.models.task import Task, TaskStatus
from app.models.user import MembershipLevel


class CSVExportError(RuntimeError):
    """Base error for CSV export failures."""


class CSVExportNotFoundError(CSVExportError):
    """Raised when the requested task or insights cannot be found."""


class CSVExportPermissionError(CSVExportError):
    """Raised when the caller lacks permission to export the task."""


@dataclass(slots=True)
class CSVExportService:
    """Service responsible for exporting analysis insights to CSV."""

    session: AsyncSession
    output_dir: Path = Path("reports/exports")

    async def export_to_csv(self, *, task_id: UUID, user_id: UUID) -> Path:
        """Generate a CSV file for the requested task insights.

        Args:
            task_id: Analysis task identifier
            user_id: Requesting user identifier (used for authorisation)

        Returns:
            Path to the generated CSV file
        """
        task = await self._fetch_task(task_id)
        if task is None:
            raise CSVExportNotFoundError("Task not found")
        if task.user_id != user_id:
            raise CSVExportPermissionError("Not authorised to export this task")

        membership = task.user.membership_level if task.user else MembershipLevel.FREE
        if membership not in {MembershipLevel.PRO, MembershipLevel.ENTERPRISE}:
            raise CSVExportPermissionError("Your subscription tier does not allow exports")

        if task.status != TaskStatus.COMPLETED:
            raise CSVExportError("Task is not complete yet")

        insights = task.insight_cards or []
        if not insights:
            raise CSVExportNotFoundError("No insights available for export")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = self.output_dir / f"report_{task_id}.csv"

        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "title",
                "summary",
                "confidence",
                "time_window_days",
                "subreddits",
                "evidence_count",
            ])
            for card in insights:
                writer.writerow(
                    [
                        card.title,
                        card.summary,
                        float(card.confidence),
                        card.time_window_days,
                        "; ".join(card.subreddits),
                        len(card.evidences or []),
                    ]
                )

        return csv_path

    async def _fetch_task(self, task_id: UUID) -> Task | None:
        stmt = (
            select(Task)
            .options(
                joinedload(Task.user),
                joinedload(Task.insight_cards).joinedload(InsightCard.evidences),
            )
            .where(Task.id == task_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().unique().one_or_none()


__all__ = [
    "CSVExportService",
    "CSVExportError",
    "CSVExportNotFoundError",
    "CSVExportPermissionError",
]
