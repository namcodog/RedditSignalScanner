#!/usr/bin/env python3
from __future__ import annotations

"""
Scrape Top Communities from https://www.reddit.com/best/communities/{page}/
and generate CSV/JSON baselines. This scraper is best-effort using static HTML.

Outputs (by default):
  - backend/data/top1000_scraped.csv
  - backend/data/top1000_scraped.json (names only, with defaults)

Caveats:
  - Page structure is subject to change. We rely on anchor href 
    patterns '/r/<name>/' and de-duplicate by first-seen order.
  - We attempt to ignore non-subreddit links like '/r/all'.
"""

import asyncio
import csv
import json
import os
import re
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import httpx


BASE_URL = "https://www.reddit.com/best/communities/{page}/"
HEADERS = {
    "User-Agent": os.getenv(
        "TOP_COMMUNITIES_UA",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X) RedditTopFetcher/1.0",
    )
}


BLOCKLIST = {"all", "popular", "mod", "new", "best", "rpan"}
NAME_RE = re.compile(r"/r/([A-Za-z0-9_]+)/?")


@dataclass
class ScrapeResult:
    names: List[str]
    pages_scanned: int


async def fetch_page(client: httpx.AsyncClient, page: int) -> str:
    url = BASE_URL.format(page=page)
    r = await client.get(url)
    r.raise_for_status()
    return r.text


def extract_subreddits(html: str) -> list[str]:
    """Extract candidate subreddit names from HTML, in first-seen order."""
    names: list[str] = []
    seen: set[str] = set()
    for m in NAME_RE.finditer(html):
        name = m.group(1)
        low = name.lower()
        if low in seen:
            continue
        if low in BLOCKLIST:
            continue
        # Basic sanity: subreddit names must start with letter or digit
        if not re.match(r"^[A-Za-z0-9_]{2,}$", name):
            continue
        seen.add(low)
        names.append(name)
    return names


async def scrape_top(limit: int = 1000, max_pages: int = 50) -> ScrapeResult:
    collected: list[str] = []
    seen: set[str] = set()
    pages_scanned = 0
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        for page in range(1, max_pages + 1):
            try:
                html = await fetch_page(client, page)
            except Exception:
                break
            pages_scanned += 1
            for name in extract_subreddits(html):
                low = name.lower()
                if low in seen:
                    continue
                seen.add(low)
                collected.append(name)
                if len(collected) >= limit:
                    return ScrapeResult(collected, pages_scanned)
    return ScrapeResult(collected, pages_scanned)


def write_csv(names: Iterable[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "name",
            "domain_label",
            "tags",
            "quality_score",
            "default_weight",
            "estimated_daily_posts",
        ])
        for n in names:
            writer.writerow([
                f"r/{n}",
                "",
                "",
                0.6,
                60,
                0,
            ])


def write_json(names: Iterable[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    items = [
        {
            "name": f"r/{n}",
            "domain_label": None,
            "tags": [],
            "quality_score": 0.6,
            "default_weight": 60,
            "estimated_daily_posts": 0,
            "categories": [],
            "priority": "medium",
            "avg_comment_length": 100,
            "description_keywords": {},
            "is_active": True,
        }
        for n in names
    ]
    payload = {"communities": items}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape Top Reddit communities")
    parser.add_argument("--limit", type=int, default=1000, help="Number of communities to collect")
    parser.add_argument("--max-pages", type=int, default=80, help="Maximum pages to scan")
    parser.add_argument("--basename", type=str, default=None, help="Output basename (without extension). Defaults to top{limit}_scraped")
    args = parser.parse_args()

    result = await scrape_top(limit=max(1, args.limit), max_pages=max(1, args.max_pages))
    root = Path(__file__).resolve().parents[2]
    out_dir = root / "backend" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    base = args.basename or f"top{args.limit}_scraped"
    csv_path = out_dir / f"{base}.csv"
    json_path = out_dir / f"{base}.json"
    write_csv(result.names, csv_path)
    write_json(result.names, json_path)
    print(f"✅ Scraped {len(result.names)} communities from {result.pages_scanned} pages.")
    print(f"CSV:  {csv_path}")
    print(f"JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
