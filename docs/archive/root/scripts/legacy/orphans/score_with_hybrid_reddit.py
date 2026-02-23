#!/usr/bin/env python3
from __future__ import annotations

"""
Score communities using HybridMatcher with layered v2.1 semantic lexicon.

Inputs:
  --lexicon backend/config/semantic_sets/crossborder_v2.1.yml
  --communities ecommerce AmazonSeller Shopify dropship dropshipping
  --posts-per 12
  --time-filter month  --sort top

Outputs:
  backend/reports/local-acceptance/hybrid_score_communities.csv

Notes:
  - Uses RedditAPIClient (same as score_with_semantic.py) to fetch posts.
  - Aggregates coverage/density/purity similar to v0 script，但匹配由 HybridMatcher 提供。
"""

import argparse
import asyncio
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Tuple

from app.core.config import get_settings
from app.services.reddit_client import RedditAPIClient, RedditAPIError

from app.services.analysis.hybrid_matcher import HybridMatcher, Term


def _load_lex_v21(path: Path) -> Dict[str, List[Term]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    layers = data.get("layers", {})
    out: Dict[str, List[Term]] = {}
    for layer, cats in layers.items():
        arr: List[Term] = []
        for cat, items in cats.items():
            for it in items:
                arr.append(
                    Term(
                        canonical=str(it.get("canonical", "")),
                        aliases=list(it.get("aliases", [])),
                        precision_tag=str(it.get("precision_tag", "phrase")),
                        category=cat,
                        weight=float(it.get("weight", 1.0)),
                    )
                )
        out[layer] = arr
    return out


async def _fetch_posts(client: RedditAPIClient, subreddit: str, *, limit: int, time_filter: str, sort: str) -> List[str]:
    raw = subreddit[2:] if subreddit.lower().startswith("r/") else subreddit
    try:
        posts = await client.fetch_subreddit_posts(raw, limit=limit, time_filter=time_filter, sort=sort)
    except (RedditAPIError, Exception):
        return []
    texts: List[str] = []
    for p in posts:
        if p.title:
            texts.append(p.title)
        if p.selftext:
            texts.append(p.selftext)
    return texts


def _token_count(texts: List[str]) -> int:
    import re
    pat = re.compile(r"[A-Za-z][A-Za-z0-9\-+/]{2,}")
    total = 0
    for t in texts:
        total += len(pat.findall(t or ""))
    return max(1, total)


def _score_with_hybrid(texts: List[str], matcher: HybridMatcher) -> Tuple[float, Dict[str, float]]:
    # 命中统计（以帖子为单位的覆盖）
    hit_posts = 0
    total_tokens = _token_count(texts)
    mentions = 0

    for txt in texts:
        res = matcher.match_text(txt)
        if res:
            hit_posts += 1
        mentions += sum(r.count for r in res)

    coverage = hit_posts / max(1, len(texts))
    density = min(1.0, mentions / max(10.0, total_tokens / 50.0))
    purity = 1.0  # 无 exclude 列表时默认为 1

    alpha, beta, gamma = 0.5, 0.3, 0.2
    score = (coverage ** alpha) * (density ** beta) * (purity ** gamma)
    return float(score), {
        "coverage": float(coverage),
        "density": float(density),
        "purity": float(purity),
        "mentions": float(mentions),
        "posts": float(len(texts)),
        "tokens": float(total_tokens),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Hybrid matcher scoring for communities")
    ap.add_argument("--lexicon", type=Path, default=Path("backend/config/semantic_sets/crossborder_v2.1.yml"))
    ap.add_argument("--communities", nargs="*", default=["ecommerce", "AmazonSeller", "Shopify", "dropship", "dropshipping"]) 
    ap.add_argument("--posts-per", type=int, default=12)
    ap.add_argument("--time-filter", default="month")
    ap.add_argument("--sort", default="top")
    args = ap.parse_args()

    # 加载词库
    lex = _load_lex_v21(args.lexicon)

    # 社区→层 映射
    layer_by_sub = {
        "ecommerce": "L1",
        "AmazonSeller": "L2",
        "Shopify": "L2",
        "dropship": "L3",
        "dropshipping": "L4",
    }

    # Reddit API 客户端
    settings = get_settings()
    client = RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=max(2, settings.reddit_max_concurrency // 2),
    )

    rows: List[Dict[str, object]] = []

    async def _run() -> None:
        async with client:
            for sub in args.communities:
                layer = layer_by_sub.get(sub, "L1")
                terms = lex.get(layer, [])
                matcher = HybridMatcher(terms, enable_semantic=False)
                texts = await _fetch_posts(client, sub, limit=args.posts_per, time_filter=args.time_filter, sort=args.sort)
                score, detail = _score_with_hybrid(texts, matcher)
                rows.append({
                    "subreddit": sub,
                    "layer": layer,
                    "posts": int(detail["posts"]),
                    "coverage": round(detail["coverage"], 4),
                    "density": round(detail["density"], 4),
                    "purity": round(detail["purity"], 4),
                    "mentions": int(detail["mentions"]),
                    "score": round(score * 100.0, 2),
                })

    import asyncio
    asyncio.run(_run())

    out = Path("backend/reports/local-acceptance/hybrid_score_communities.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["subreddit", "layer", "posts", "coverage", "density", "purity", "mentions", "score"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(json.dumps({"status": "ok", "rows": rows, "output": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
