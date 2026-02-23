#!/usr/bin/env python3
import asyncio
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select, text
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
load_dotenv(ROOT / "backend/.env")

# Force data-collection to use DB/redis paths without hitting live Reddit.
os.environ.setdefault("ENABLE_REDDIT_SEARCH", "false")
os.environ.setdefault("REDDIT_CLIENT_ID", "stub")
os.environ.setdefault("REDDIT_CLIENT_SECRET", "stub")
os.environ.setdefault("REDDIT_USER_AGENT", "integration-test")

from app.db.session import SessionFactory
from app.models.posts_storage import PostHot
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskSummary
from app.services.data_collection import CollectionResult
from app.services.analysis_engine import run_analysis


async def _resolve_task_id() -> uuid.UUID:
    try:
        async with SessionFactory() as session:
            result = await session.execute(select(Task.id).limit(1))
            existing = result.scalar_one_or_none()
            if existing:
                return existing
    except Exception:
        pass
    return uuid.uuid4()


async def _load_labeled_posts(limit: int = 20000) -> list[dict]:
    async with SessionFactory() as session:
        id_rows = await session.execute(
            text("select distinct post_id from mv_analysis_labels limit :limit"),
            {"limit": limit},
        )
        post_ids = [row[0] for row in id_rows.fetchall()]
        if not post_ids:
            return []

        result = await session.execute(
            select(PostHot)
            .where(PostHot.id.in_(post_ids))
            .order_by(PostHot.created_at.desc())
        )
        records = result.scalars().all()

    posts: list[dict] = []
    for rec in records:
        posts.append(
            {
                "id": rec.id,
                "title": rec.title or "",
                "summary": rec.body or "",
                "selftext": rec.body or "",
                "score": int(rec.score or 0),
                "num_comments": int(rec.num_comments or 0),
                "url": "",
                "permalink": "",
                "author": rec.author_name or "",
                "subreddit": rec.subreddit or "",
            }
        )
    return posts


class DBDataCollectionService:
    def __init__(self, posts: list[dict]):
        self.posts = posts

    async def collect_posts(self, communities, *, limit_per_subreddit: int = 50):
        posts_by_subreddit: dict[str, list[dict]] = defaultdict(list)
        target = communities[0] if communities else "sample"
        posts_by_subreddit[target] = list(self.posts)

        total_posts = sum(len(v) for v in posts_by_subreddit.values())
        return CollectionResult(
            total_posts=total_posts,
            cache_hits=0,
            api_calls=0,
            cache_hit_rate=0.0,
            posts_by_subreddit=posts_by_subreddit,
            cached_subreddits=set(),
        )


async def main() -> None:
    task_id = await _resolve_task_id()
    posts = await _load_labeled_posts()
    data_collection = DBDataCollectionService(posts)
    now = datetime.utcnow()
    task = TaskSummary(
        id=task_id,
        status=TaskStatus.PENDING,
        product_description="dropshipping payment gateway solution",
        created_at=now,
        updated_at=now,
        completed_at=None,
        retry_count=0,
        failure_category=None,
    )

    result = await run_analysis(task, data_collection=data_collection)

    print(f"Confidence Score: {result.confidence_score}")
    print(f"P/S Ratio: {result.sources.get('ps_ratio')}")

    print("--- Top Pains ---")
    for pain in result.insights.get("pain_points", []):
        desc = pain.get("description")
        freq = pain.get("frequency")
        print(f"- {desc} (Freq: {freq})")

    print("--- Top Opportunities ---")
    for opp in result.insights.get("opportunities", []):
        print(f"- {opp.get('description')}")

    print("--- Competitors ---")
    for comp in result.insights.get("competitors", []):
        print(f"- {comp.get('name')} (Mentions: {comp.get('mentions')})")


if __name__ == "__main__":
    asyncio.run(main())
