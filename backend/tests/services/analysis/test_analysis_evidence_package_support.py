from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from app.services.analysis.analysis_evidence_package_support import (
    build_sample_posts_db,
    derive_comments_pipeline_status,
    fetch_comment_evidence,
)


class _FakeScalarResult:
    def __init__(self, value: int) -> None:
        self._value = value

    def scalar_one(self) -> int:
        return self._value


class _FakeMappingResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def mappings(self) -> "_FakeMappingResult":
        return self

    def all(self) -> list[dict[str, object]]:
        return self._rows


class _FakeSession:
    def __init__(self, queue: list[object]) -> None:
        self._queue = queue

    async def execute(self, *_args: object, **_kwargs: object) -> object:
        return self._queue.pop(0)


class _FakeSessionContext:
    def __init__(self, queue: list[object]) -> None:
        self._queue = queue

    async def __aenter__(self) -> _FakeSession:
        return _FakeSession(self._queue)

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def test_build_sample_posts_db_normalizes_shape() -> None:
    payload = build_sample_posts_db(
        [
            {
                "id": "p1",
                "title": "PayPal payout",
                "summary": "still pending",
                "subreddit": "PayPal",
                "author": "sellerA",
                "score": 12,
                "url": "https://x",
                "permalink": "/r/paypal/p1",
            }
        ],
        normalise_community_name=lambda raw: f"r/{raw.lower()}",
    )

    assert payload == [
        {
            "id": "p1",
            "title": "PayPal payout still pending",
            "text": "PayPal payout still pending",
            "body": "still pending",
            "subreddit": "r/paypal",
            "author": "sellerA",
            "score": 12,
            "url": "https://x",
            "permalink": "/r/paypal/p1",
        }
    ]


def test_derive_comments_pipeline_status_variants() -> None:
    assert (
        derive_comments_pipeline_status(
            sample_comments_db=[{"id": "c1"}],
            comments_db_total=3,
            comments_db_eligible=2,
        )
        == "ok"
    )
    assert (
        derive_comments_pipeline_status(
            sample_comments_db=[],
            comments_db_total=0,
            comments_db_eligible=0,
        )
        == "disabled"
    )
    assert (
        derive_comments_pipeline_status(
            sample_comments_db=[],
            comments_db_total=5,
            comments_db_eligible=0,
        )
        == "all_noise"
    )
    assert (
        derive_comments_pipeline_status(
            sample_comments_db=[],
            comments_db_total=5,
            comments_db_eligible=2,
        )
        == "filtered"
    )


@pytest.mark.asyncio
async def test_fetch_comment_evidence_builds_sample_comments_and_counts() -> None:
    queue = [
        _FakeScalarResult(4),
        _FakeScalarResult(3),
        _FakeScalarResult(2),
        _FakeMappingResult(
            [
                {
                    "comment_id": "c1",
                    "body": "PayPal payout still pending after shipping",
                    "subreddit": "PayPal",
                    "author_name": "sellerA",
                    "permalink": "/r/paypal/comments/c1",
                    "score": 10,
                    "source_post_id": "p1",
                }
            ]
        ),
    ]

    artifacts = await fetch_comment_evidence(
        task=SimpleNamespace(),
        topic_profile=None,
        deduped_posts=[{"id": "p1"}],
        session_factory=lambda: _FakeSessionContext(queue),
        normalise_community_name=lambda raw: f"r/{str(raw).lower()}",
        filter_items_by_profile_context_fn=lambda items, *_args, **_kwargs: items,
        schedule_auto_backfill_for_missing_comments_fn=lambda **_kwargs: [],
    )

    assert artifacts.posts_db_current == 4
    assert artifacts.comments_db_total == 3
    assert artifacts.comments_db_eligible == 2
    assert artifacts.comments_pipeline_status == "ok"
    assert artifacts.comment_counts_by_subreddit == {"r/paypal": 1}
    assert artifacts.sample_comments_db[0]["id"] == "c1"


@pytest.mark.asyncio
async def test_fetch_comment_evidence_triggers_remediation_for_empty_topic_comments() -> None:
    async def _remediate(**_kwargs: object) -> list[dict[str, object]]:
        return [{"type": "comment_backfill"}]

    artifacts = await fetch_comment_evidence(
        task=SimpleNamespace(),
        topic_profile=SimpleNamespace(require_context_for_fetch=False),
        deduped_posts=[{"id": "p1"}],
        session_factory=lambda: _FakeSessionContext([]),
        normalise_community_name=lambda raw: f"r/{str(raw).lower()}",
        filter_items_by_profile_context_fn=lambda items, *_args, **_kwargs: items,
        schedule_auto_backfill_for_missing_comments_fn=_remediate,
    )

    assert artifacts.comments_pipeline_status == "disabled"
    assert artifacts.remediation_actions == [{"type": "comment_backfill"}]
