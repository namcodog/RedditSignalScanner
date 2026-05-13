from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.db.session import SessionFactory
from app.models.community_registry import CommunityRegistry
from app.models.community_runtime_state import CommunityRuntimeState
from app.services.analysis.analysis_collection_support import fetch_coverage_summary


@pytest.mark.asyncio
async def test_fetch_coverage_summary_reads_runtime_truth_source() -> None:
    async with SessionFactory() as session:
        registry = CommunityRegistry(
            platform="reddit",
            community_name="r/coverage",
            source_of_truth="registry",
            is_enabled=True,
        )
        session.add(registry)
        await session.flush()
        session.add(
            CommunityRuntimeState(
                community_id=registry.id,
                crawl_status="active",
                crawl_priority=50,
                is_enabled=True,
                sample_posts=123,
                sample_comments=456,
                backfill_floor=datetime.now(timezone.utc) - timedelta(days=180),
                runtime_notes={
                    "backfill_status": "DONE_CAPPED",
                    "coverage_months": 6,
                    "backfill_capped": True,
                },
            )
        )
        await session.commit()

    summary = await fetch_coverage_summary(["r/coverage", "r/missing"])

    assert summary["status_counts"] == {"DONE_CAPPED": 1}
    assert summary["coverage_months_min"] == 6
    assert summary["coverage_months_avg"] == 6
    assert summary["coverage_months_max"] == 6
    assert summary["capped_count"] == 1
    assert summary["missing_communities"] == ["r/missing"]
    assert summary["community_statuses"] == [
        {
            "community": "r/coverage",
            "backfill_status": "DONE_CAPPED",
            "coverage_months": 6,
            "sample_posts": 123,
            "sample_comments": 456,
            "backfill_capped": True,
        }
    ]
