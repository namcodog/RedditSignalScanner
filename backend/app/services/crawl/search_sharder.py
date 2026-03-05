from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from app.services.infrastructure.reddit_client import RedditAPIClient, RedditPost
from app.services.crawl.common import Submission, JSONLWriter


CHARSET_DEFAULT = "abcdefghijklmnopqrstuvwxyz0123456789"


def parse_prefix_chars(spec: str) -> str:
    spec = spec.strip()
    if spec == "a-z0-9":
        return CHARSET_DEFAULT
    # Fallback: explicit chars
    return "".join(ch for ch in spec if ch and not ch.isspace())


async def _search_shard(
    client: RedditAPIClient,
    subreddit: str,
    prefix: str,
    *,
    sort: str,
    max_pages: int,
) -> Tuple[List[RedditPost], int]:
    after: Optional[str] = None
    results: List[RedditPost] = []
    pages = 0
    while pages < max_pages:
        pages += 1
        posts, after = await client.search_subreddit_page(
            subreddit,
            query=prefix,
            limit=100,
            sort=sort,
            time_filter="all",
            restrict_sr=1,
            syntax=None,
            after=after,
        )
        if not posts:
            break
        results.extend(posts)
        if not after:
            break
    return results, pages


async def run_search_partition(
    *,
    subreddit: str,
    client_id: str,
    client_secret: str,
    user_agent: str,
    prefix_chars: str,
    max_prefix_len: int,
    split_threshold: int,
    max_pages_per_shard: int,
    sort: str,
    writer: JSONLWriter | None,
    progress_path: Path | None,
    kpi_output_dir: Path,
) -> Tuple[int, Path]:
    charset = parse_prefix_chars(prefix_chars)
    queue: List[str] = list(charset)  # initial 1-char prefixes
    seen_ids: set[str] = set()
    total = 0
    shards_processed = 0

    kpi_rows: List[Dict[str, str | int]] = []

    async with RedditAPIClient(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        rate_limit=58,
        rate_limit_window=600.0,
        max_concurrency=2,
    ) as api:
        await api.authenticate()

        while queue:
            prefix = queue.pop(0)
            shards_processed += 1
            # 写进度
            if progress_path is not None:
                try:
                    progress_path.parent.mkdir(parents=True, exist_ok=True)
                    progress_path.write_text(
                        json.dumps(
                            {
                                "subreddit": subreddit,
                                "status": "running",
                                "shard": prefix,
                                "queue_size": len(queue),
                                "processed": shards_processed,
                                "total": total,
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                            },
                            ensure_ascii=False,
                            indent=2,
                        ),
                        encoding="utf-8",
                    )
                except Exception:
                    pass

            # 抓该分片
            try:
                posts, pages = await _search_shard(
                    api,
                    subreddit,
                    prefix,
                    sort=sort,
                    max_pages=max_pages_per_shard,
                )
            except Exception as exc:
                kpi_rows.append(
                    {
                        "prefix": prefix,
                        "status": f"error:{exc}",
                        "count": 0,
                        "pages": 0,
                        "split": 0,
                    }
                )
                continue

            # 去重与写入
            new_count = 0
            for p in posts:
                if p.id in seen_ids:
                    continue
                seen_ids.add(p.id)
                total += 1
                new_count += 1
                if writer is not None:
                    rec = Submission.from_reddit_post(p)
                    writer.append(rec)

            # KPI & 决策
            split = 0
            if new_count >= split_threshold and len(prefix) < max_prefix_len:
                # 分裂为所有子前缀
                for ch in charset:
                    queue.append(prefix + ch)
                split = 1

            kpi_rows.append(
                {
                    "prefix": prefix,
                    "status": "ok",
                    "count": new_count,
                    "pages": pages,
                    "split": split,
                }
            )

    # 写 KPI 文件
    kpi_path = kpi_output_dir / f"{subreddit}.search_kpi.csv"
    try:
        import csv

        with kpi_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["prefix", "status", "count", "pages", "split"])
            w.writeheader()
            for r in kpi_rows:
                w.writerow(r)
    except Exception:
        pass

    return total, kpi_path
