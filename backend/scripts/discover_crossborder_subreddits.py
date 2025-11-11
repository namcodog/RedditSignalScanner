#!/usr/bin/env python3
from __future__ import annotations

"""
Discover cross‑border e‑commerce related subreddits using an intent→search→expand
pipeline and export candidates for scoring.

Inputs (args/env):
  --keywords: comma‑separated queries (e.g., "amazon,fba,shopify,etsy,dropship")
  --limit: target unique subreddit count cap (default 10000)
  --per-query-sr: subreddits/search per query cap (default 100)
  --per-query-posts: posts search per query cap (default 100)
  --time-filter: hour/day/week/month/year/all (default month)
  --sort: relevance | new | top | hot (default relevance)
  --export-csv: path to write CSV (default backend/data/crossborder_candidates.csv)
  --export-json: path to write JSON (default backend/data/crossborder_candidates.json)

Outputs:
  CSV/JSON with fields: name, sr_hits, post_hits, author_bonus, domain_hits, total_weight

Notes:
  - Uses RedditAPIClient for auth/search posts; uses client.request for subreddit search.
  - 403/404 are treated as empty by the client; we ignore those gracefully.
  - Author co‑occurrence bonus is heuristic (+0.5 per subreddit when an author
    appears across multiple subreddits within the sampled posts).
  - Domain signals are based on platform domains (amazon/etsy/shopify/...)
"""

import argparse
import asyncio
import csv
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import urlparse

import yaml  # type: ignore

from app.core.config import get_settings
from app.services.reddit_client import API_BASE_URL, RedditAPIClient


log = logging.getLogger(__name__)


PLATFORM_DOMAINS = (
    "amazon.",
    "etsy.",
    "shopify.",
    "walmart.",
    "aliexpress.",
    "lazada.",
    "shopee.",
    "temu.com",
    "shein.com",
)


def norm_name(name: str) -> str:
    n = (name or "").strip()
    if not n:
        return n
    return n if n.lower().startswith("r/") else f"r/{n}"


async def subreddit_search(client: RedditAPIClient, query: str, *, limit: int = 100) -> List[str]:
    await client.authenticate()
    headers = {"Authorization": f"Bearer {client.access_token}", "User-Agent": client.user_agent}
    url = f"{API_BASE_URL}/subreddits/search"
    params = {"q": query, "limit": str(min(100, max(1, limit)))}
    payload = await client._request_json("GET", url, headers=headers, params=params, data=None)  # type: ignore[attr-defined]
    names: List[str] = []
    for child in (payload.get("data", {}) or {}).get("children", []) or []:
        data = child.get("data", {}) or {}
        dn = data.get("display_name") or data.get("display_name_prefixed") or ""
        if dn:
            names.append(norm_name(str(dn)))
    return names


def extract_domain(url: str) -> str:
    try:
        netloc = urlparse(url or "").netloc.lower()
        return netloc
    except Exception:
        return ""


@dataclass
class Candidate:
    name: str
    sr_hits: int = 0
    post_hits: int = 0
    author_bonus: float = 0.0
    domain_hits: int = 0

    @property
    def total_weight(self) -> float:
        # Heuristic: subreddit search weight x2, posts x1, authors x0.5, domain x1
        return float(round(self.sr_hits * 2 + self.post_hits * 1 + self.author_bonus * 0.5 + self.domain_hits * 1, 2))


async def discover(
    *,
    queries: List[str],
    sr_limit: int,
    posts_limit: int,
    time_filter: str,
    sort: str,
    hard_cap: int,
) -> Dict[str, Candidate]:
    settings = get_settings()
    client = RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=min(60, settings.reddit_rate_limit),
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=min(20.0, settings.reddit_request_timeout_seconds),
        max_concurrency=max(1, settings.reddit_max_concurrency // 2),
    )
    candidates: Dict[str, Candidate] = {}
    author_subs: Dict[str, Set[str]] = defaultdict(set)

    async with client:
        # 1) subreddit search
        for q in queries:
            names = await subreddit_search(client, q, limit=sr_limit)
            for n in names:
                if n not in candidates:
                    candidates[n] = Candidate(name=n)
                candidates[n].sr_hits += 1
            if len(candidates) >= hard_cap:
                break

        # 2) post search (反推子版块 + 作者/域名信号)
        for q in queries:
            posts = await client.search_posts(q, limit=min(100, max(10, posts_limit)), time_filter=time_filter, sort=sort)
            for p in posts:
                sub = norm_name(p.subreddit)
                if sub not in candidates:
                    candidates[sub] = Candidate(name=sub)
                candidates[sub].post_hits += 1
                # author co-occurrence set
                if p.author:
                    author_subs[p.author].add(sub)
                # domain signal
                dom = extract_domain(p.url)
                if dom and any(dom.endswith(d.strip('.')) or d in dom for d in PLATFORM_DOMAINS):
                    candidates[sub].domain_hits += 1
            if len(candidates) >= hard_cap:
                break

        # 3) author co-occurrence bonus
        for subs in author_subs.values():
            if len(subs) <= 1:
                continue
            for s in subs:
                if s in candidates:
                    candidates[s].author_bonus += 1.0

    # Cap to hard limit by weight-desc
    if len(candidates) > hard_cap:
        pruned = dict(sorted(candidates.items(), key=lambda kv: kv[1].total_weight, reverse=True)[:hard_cap])
        return pruned
    return candidates


def write_outputs(candidates: Dict[str, Candidate], csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    # CSV
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["name", "sr_hits", "post_hits", "author_bonus", "domain_hits", "total_weight"])
        for c in sorted(candidates.values(), key=lambda c: c.total_weight, reverse=True):
            w.writerow([c.name, c.sr_hits, c.post_hits, round(c.author_bonus, 2), c.domain_hits, c.total_weight])
    # JSON (communities list + details)
    payload = {
        "communities": [
            {
                "name": c.name,
                "sr_hits": c.sr_hits,
                "post_hits": c.post_hits,
                "author_bonus": round(c.author_bonus, 2),
                "domain_hits": c.domain_hits,
                "total_weight": c.total_weight,
            }
            for c in sorted(candidates.values(), key=lambda c: c.total_weight, reverse=True)
        ]
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Discover cross-border subreddits")
    p.add_argument("--keywords", type=str, default="amazon,fba,shopify,etsy,dropship,ecommerce,tiktok shop,aliexpress,walmart,etsy sellers,lazada,shopee,kickstarter,indiegogo,product research,winning product")
    p.add_argument("--limit", type=int, default=10000)
    p.add_argument("--per-query-sr", type=int, default=100)
    p.add_argument("--per-query-posts", type=int, default=100)
    p.add_argument("--time-filter", type=str, default="month")
    p.add_argument("--sort", type=str, default="relevance")
    p.add_argument("--export-csv", type=str, default="backend/data/crossborder_candidates.csv")
    p.add_argument("--export-json", type=str, default="backend/data/crossborder_candidates.json")
    args = p.parse_args()

    queries = [q.strip() for q in args.keywords.split(",") if q.strip()]
    candidates = asyncio.run(
        discover(
            queries=queries,
            sr_limit=max(10, args.per_query_sr),
            posts_limit=max(10, args.per_query_posts),
            time_filter=args.time_filter,
            sort=args.sort,
            hard_cap=max(100, args.limit),
        )
    )

    csv_path = Path(args.export_csv)
    json_path = Path(args.export_json)
    write_outputs(candidates, csv_path, json_path)
    print(f"✅ Discovered {len(candidates)} candidate subreddits")
    print(f"CSV:  {csv_path}")
    print(f"JSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

