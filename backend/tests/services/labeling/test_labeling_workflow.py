from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

import pandas as pd
import pytest
from sqlalchemy import delete

from app.db.session import SessionFactory
from app.models.posts_storage import PostRaw
from app.services.labeling import (
    SAMPLE_COLUMNS,
    export_samples_to_csv,
    load_labeled_data,
    sample_posts_for_labeling,
    validate_labels,
)


def _make_post(
    subreddit: str,
    *,
    created_at: datetime,
    score: int,
    index: int,
) -> PostRaw:
    return PostRaw(
        source="reddit",
        source_post_id=f"{subreddit}-{index}",
        version=1,
        created_at=created_at,
        fetched_at=created_at,
        valid_from=created_at,
        valid_to=datetime(9999, 12, 31, tzinfo=timezone.utc),
        is_current=True,
        title=f"{subreddit} title {index}",
        body=f"Body {index} for {subreddit}",
        subreddit=subreddit,
        score=score,
        num_comments=index % 50,
    )


async def _seed_posts(total_subreddits: int = 30, posts_per_bucket: int = 120) -> None:
    async with SessionFactory() as session:
        await session.execute(delete(PostRaw))
        now = datetime.now(timezone.utc)
        scores = [5, 30, 75, 160]
        batch: List[PostRaw] = []
        batch_size = 500

        def flush_batch() -> None:
            if not batch:
                return
            session.add_all(batch)
            batch.clear()

        for idx in range(total_subreddits):
            subreddit = f"r/test_{idx}"
            for bucket, score in enumerate(scores):
                bucket_share = posts_per_bucket // len(scores)
                for offset in range(bucket_share):
                    created_at = now - timedelta(days=(idx + bucket + offset) % 28)
                    batch.append(
                        _make_post(
                            subreddit,
                            created_at=created_at,
                            score=score + offset,
                            index=(idx * posts_per_bucket)
                            + (bucket * bucket_share)
                            + offset,
                        )
                    )
                    if len(batch) >= batch_size:
                        flush_batch()
        flush_batch()
        await session.commit()


@pytest.mark.asyncio
async def test_sample_posts_for_labeling_returns_diverse_dataset() -> None:
    await _seed_posts(total_subreddits=32, posts_per_bucket=160)
    samples = await sample_posts_for_labeling(limit=500, random_seed=21)
    assert len(samples) == 500
    unique_communities = {row["subreddit"] for row in samples}
    assert len(unique_communities) >= 20
    score_buckets = {"very_low": 0, "low": 0, "medium": 0, "high": 0}

    def classify(score: int) -> str:
        if score < 10:
            return "very_low"
        if score < 50:
            return "low"
        if score < 100:
            return "medium"
        return "high"

    for row in samples:
        assert set(row.keys()).issuperset({"post_id", "title", "body", "subreddit", "score"})
        bucket = classify(int(row["score"]))
        score_buckets[bucket] += 1
    assert all(count > 0 for count in score_buckets.values())


def test_export_and_load_roundtrip(tmp_path: Path) -> None:
    samples: List[Dict[str, str | int]] = [
        {
            "post_id": "abc123",
            "title": "Need better onboarding",
            "body": "Any SaaS founders solved this?",
            "subreddit": "r/startups",
            "score": 42,
            "label": "",
            "strength": "",
            "notes": "",
        },
        {
            "post_id": "def456",
            "title": "CRM alternatives?",
            "body": "Looking for lightweight CRM",
            "subreddit": "r/sales",
            "score": 103,
            "label": "",
            "strength": "",
            "notes": "",
        },
    ]
    csv_path = tmp_path / "labeled_samples_template.csv"
    export_samples_to_csv(samples, csv_path)
    assert csv_path.exists()
    df = load_labeled_data(csv_path)
    assert list(df.columns) == SAMPLE_COLUMNS
    assert len(df) == len(samples)


def test_validate_labels_requires_complete_annotations() -> None:
    df = pd.DataFrame(
        [
            {
                "post_id": "abc",
                "title": "Pain",
                "body": "Example body",
                "subreddit": "r/startups",
                "score": 12,
                "label": "opportunity",
                "strength": "medium",
                "notes": "clear signal",
            },
            {
                "post_id": "ghi",
                "title": "Another pain",
                "body": "Another body",
                "subreddit": "r/startup",
                "score": 73,
                "label": "non-opportunity",
                "strength": "weak",
                "notes": "",
            },
        ]
    )
    validate_labels(df, expected_count=2)

    with pytest.raises(ValueError):
        invalid = df.copy()
        invalid.loc[0, "label"] = "maybe"
        validate_labels(invalid, expected_count=2)
