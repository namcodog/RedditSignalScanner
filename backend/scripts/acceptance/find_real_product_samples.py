#!/usr/bin/env python3
from __future__ import annotations

"""
Find real report / hotpost samples in Dev DB for product-surface acceptance.

Use this script when product polish must be verified with real data instead of
mock payloads. It prints the strongest available report samples by tier and the
latest hotpost queries with enough evidence.
"""

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.tenant_context import set_current_user_id, unset_current_user_id
from app.db.session import SessionFactory
from app.models.analysis import Analysis
from app.models.hotpost_query import HotpostQuery
from app.models.report import Report
from app.models.task import Task


def _safe_text(value: Any, *, limit: int = 120) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1]}…"


async def _load_report_samples(user_id: str | None, limit: int) -> list[dict[str, Any]]:
    if user_id:
        set_current_user_id(user_id)

    try:
        async with SessionFactory() as session:
            stmt = (
                select(Task, Analysis, Report)
                .join(Analysis, Analysis.task_id == Task.id)
                .join(Report, Report.analysis_id == Analysis.id)
                .options(selectinload(Task.user))
                .order_by(Task.created_at.desc())
                .limit(limit * 8)
            )
            if user_id:
                stmt = stmt.where(Task.user_id == UUID(user_id))

            rows = (await session.execute(stmt)).all()
    finally:
        if user_id:
            unset_current_user_id()

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task, analysis, report in rows:
        sources = analysis.sources or {}
        tier = str(sources.get("report_tier") or "unknown")
        grouped[tier].append(
            {
                "task_id": str(task.id),
                "analysis_id": str(analysis.id),
                "report_id": str(report.id),
                "user_id": str(task.user_id),
                "user_email": getattr(task.user, "email", None),
                "membership_level": getattr(getattr(task.user, "membership_level", None), "value", None)
                or str(getattr(task.user, "membership_level", "") or ""),
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "report_tier": tier,
                "analysis_blocked": sources.get("analysis_blocked"),
                "posts_analyzed": sources.get("posts_analyzed"),
                "communities_count": len(sources.get("communities") or []),
                "confidence_score": float(analysis.confidence_score or 0),
                "product_description": _safe_text(task.product_description, limit=160),
            }
        )

    ordered: list[dict[str, Any]] = []
    for tier in ("A_full", "B_trimmed", "C_scouting", "X_blocked", "unknown"):
        ordered.extend(grouped.get(tier, [])[:limit])
    return ordered


async def _load_hotpost_samples(limit: int, min_evidence: int) -> list[dict[str, Any]]:
    async with SessionFactory() as session:
        stmt = (
            select(HotpostQuery)
            .where(HotpostQuery.evidence_count >= min_evidence)
            .order_by(HotpostQuery.created_at.desc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).scalars().all()

    return [
        {
            "query_id": str(row.id),
            "query": row.query,
            "mode": row.mode,
            "evidence_count": row.evidence_count,
            "community_count": row.community_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Find real product samples in Dev DB")
    parser.add_argument("--user-id", help="Optional task owner user_id for report samples")
    parser.add_argument("--report-limit", type=int, default=2)
    parser.add_argument("--hotpost-limit", type=int, default=5)
    parser.add_argument("--min-hotpost-evidence", type=int, default=10)
    args = parser.parse_args()

    payload = {
        "report_samples": await _load_report_samples(args.user_id, args.report_limit),
        "hotpost_samples": await _load_hotpost_samples(args.hotpost_limit, args.min_hotpost_evidence),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
