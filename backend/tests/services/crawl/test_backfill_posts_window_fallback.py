from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.db.session import SessionFactory
from app.services.crawl.incremental_crawler import IncrementalCrawler
from app.services.infrastructure.reddit_client import RedditPost


@pytest.mark.asyncio
async def test_backfill_posts_window_listing_stops_at_since(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=7)
    until = now
    in_window = (since + timedelta(hours=1)).timestamp()
    in_window_2 = (since + timedelta(hours=2)).timestamp()
    out_window = (since - timedelta(days=1)).timestamp()

    class DummyReddit:
        def __init__(self) -> None:
            self.calls: list[str | None] = []

        async def fetch_subreddit_posts(
            self, *args: Any, **kwargs: Any
        ) -> tuple[list[RedditPost], str | None]:
            after = kwargs.get("after")
            if after is None:
                self.calls.append(None)
                return (
                    [
                        RedditPost(
                            id="p_in",
                            title="inside",
                            selftext="",
                            score=1,
                            num_comments=0,
                            created_utc=float(in_window),
                            subreddit="test",
                            author="a",
                            url="",
                            permalink="",
                        ),
                        RedditPost(
                            id="p_in2",
                            title="inside2",
                            selftext="",
                            score=1,
                            num_comments=0,
                            created_utc=float(in_window_2),
                            subreddit="test",
                            author="a",
                            url="",
                            permalink="",
                        ),
                    ],
                    "t3_next",
                )
            self.calls.append(after)
            return (
                [
                    RedditPost(
                        id="p_out",
                        title="outside",
                        selftext="",
                        score=1,
                        num_comments=0,
                        created_utc=float(out_window),
                        subreddit="test",
                        author="a",
                        url="",
                        permalink="",
                    ),
                ],
                None,
            )

    async def fake_dual_write(  # noqa: ARG001
        self: IncrementalCrawler,
        community_name: str,
        posts: list[RedditPost],
        trigger_comments_fetch: bool = False,
    ) -> tuple[int, int, int]:
        return (0, 0, 0)

    monkeypatch.setattr(IncrementalCrawler, "_dual_write", fake_dual_write)

    async with SessionFactory() as session:
        crawler = IncrementalCrawler(
            db=session,
            reddit_client=DummyReddit(),
            crawl_run_id="run",
            community_run_id="cid",
            source_track="backfill_posts",
            refresh_posts_latest_after_write=False,
        )
        result = await crawler.backfill_posts_window(
            "r/test_backfill_fallback",
            since=since,
            until=until,
            max_posts=10,
            sort="new",
        )

    assert result["status"] == "completed"
    assert result["total_fetched"] == 2
    assert crawler.reddit_client.calls == [None, "t3_next"]
    assert result["pages_processed"] == 2
