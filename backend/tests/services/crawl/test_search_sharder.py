import asyncio
from pathlib import Path
import json

import pytest

from app.services.crawl.search_sharder import run_search_partition


class FakeAPI:
    def __init__(self):
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    async def authenticate(self):
        return None

    async def search_subreddit_page(self, subreddit, query, *, limit, sort, time_filter, restrict_sr, syntax, after):
        # Return synthetic results: prefixes 'a' returns 3 posts, 'b' returns 950 (to trigger split)
        posts = []
        next_after = None
        if query == "a" and not after:
            posts = [
                type("P", (), {"id": f"ida{i}", "title": "t", "selftext": "s", "score": 1, "num_comments": 0,
                                 "created_utc": 1700000000.0, "subreddit": subreddit, "author": "u", "url": "u", "permalink": "/p"})
                for i in range(3)
            ]
        elif query == "b":
            # simulate many results via pagination: 10 pages * 95 = 950
            page = 0
            if after:
                try:
                    page = int(after.split('_')[-1])
                except Exception:
                    page = 0
            if page < 10:
                posts = [
                    type("P", (), {"id": f"idb{page}_{i}", "title": "t", "selftext": "s", "score": 1, "num_comments": 0,
                                     "created_utc": 1700000000.0, "subreddit": subreddit, "author": "u", "url": "u", "permalink": "/p"})
                    for i in range(95)
                ]
                next_after = f"t3_page_{page+1}"
        return posts, next_after


@pytest.mark.asyncio
async def test_run_search_partition(monkeypatch, tmp_path: Path):
    # Monkeypatch RedditAPIClient to our FakeAPI
    import app.services.crawl.search_sharder as sh

    class _FakeCtx:
        def __init__(self):
            self._api = FakeAPI()
        async def __aenter__(self):
            return self._api
        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr(sh, "RedditAPIClient", lambda **kw: _FakeCtx())

    out = tmp_path / "out.jsonl"
    progress = tmp_path / "progress.json"
    # Use writer to stream
    from scripts.crawl_for_lexicon import JSONLWriter
    writer = JSONLWriter(out)
    total, kpi = await run_search_partition(
        subreddit="ecommerce",
        client_id="x", client_secret="y", user_agent="z",
        prefix_chars="ab", max_prefix_len=2, split_threshold=900, max_pages_per_shard=15,
        sort="new", writer=writer, progress_path=progress, kpi_output_dir=tmp_path,
    )
    writer.close()

    # Expect 'a' contributed 3 posts; 'b' splits and contributes many; total > 3
    assert total > 3
    assert out.exists() and out.stat().st_size > 0
    assert kpi.exists()
