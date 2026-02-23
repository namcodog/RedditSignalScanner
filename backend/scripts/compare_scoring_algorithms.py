from __future__ import annotations

"""
Compare layered vs legacy semantic scoring and produce a delta report.

Inputs:
  --lexicon backend/config/semantic_sets/unified_lexicon.yml
  --input backend/data/crossborder_candidates.json (list or {communities: [...]})
  --limit 100
  --posts-per 10
  --topn 200
  --use-reddit (optional; default true). If disabled, expects --input-posts JSONL.

Outputs:
  backend/data/semantic_compare.csv with per theme old/new scores and deltas.
  Prints Pearson-like correlation (approx; using numpy if available else fallback).
"""

import argparse
import asyncio
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

from app.core.config import get_settings
from app.services.reddit_client import RedditAPIClient, RedditAPIError
from app.services.semantic import UnifiedLexicon, SemanticScorer


async def fetch_posts(client: RedditAPIClient, subreddit: str, *, limit: int, time_filter: str, sort: str) -> List[str]:
    raw = subreddit[2:] if subreddit.lower().startswith("r/") else subreddit
    try:
        posts = await client.fetch_subreddit_posts(raw, limit=limit, time_filter=time_filter, sort=sort)
    except (RedditAPIError, Exception):  # treat as empty
        return []
    texts: List[str] = []
    for p in posts:
        if isinstance(p, dict):
            texts.append(p.get("title", "") or "")
            if p.get("selftext"):
                texts.append(p["selftext"])
        elif hasattr(p, "title"):
            texts.append(p.title or "")
            if hasattr(p, "selftext") and p.selftext:
                texts.append(p.selftext)
    return texts


def _corr(a: List[float], b: List[float]) -> float:
    try:
        import numpy as np  # type: ignore

        if not a or not b or len(a) != len(b):
            return 0.0
        aa = np.array(a, dtype=float)
        bb = np.array(b, dtype=float)
        if aa.std() == 0 or bb.std() == 0:
            return 0.0
        return float(np.corrcoef(aa, bb)[0, 1])
    except Exception:
        # Fallback: Spearman-like rank correlation approx
        if not a or not b or len(a) != len(b):
            return 0.0
        order_a = {v: i for i, v in enumerate(sorted(a))}
        order_b = {v: i for i, v in enumerate(sorted(b))}
        xs = [order_a[v] for v in a]
        ys = [order_b[v] for v in b]
        mean_x = sum(xs) / len(xs)
        mean_y = sum(ys) / len(ys)
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        denx = sum((x - mean_x) ** 2 for x in xs) or 1.0
        deny = sum((y - mean_y) ** 2 for y in ys) or 1.0
        return float(num / (denx ** 0.5 * deny ** 0.5))


async def main() -> None:
    ap = argparse.ArgumentParser(description="Compare layered vs legacy semantic scoring")
    ap.add_argument("--lexicon", type=Path, default=Path("backend/config/semantic_sets/unified_lexicon.yml"))
    ap.add_argument("--input", type=Path, default=Path("backend/data/crossborder_candidates.json"))
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--posts-per", type=int, default=10)
    ap.add_argument("--topn", type=int, default=200)
    ap.add_argument("--use-reddit", action="store_true", default=True)
    args = ap.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    items = payload.get("communities") or payload
    names: List[str] = [str((it.get("name") if isinstance(it, Mapping) else it) or "").strip() for it in items]
    names = [n if n.startswith("r/") else f"r/{n}" for n in names if n]
    if args.limit and args.limit > 0:
        names = names[: args.limit]

    ulex = UnifiedLexicon(args.lexicon)
    themes = list((ulex._themes or {}).keys()) or ["what_to_sell", "how_to_sell", "where_to_sell", "how_to_source"]
    scorer_new = SemanticScorer(ulex, enable_layered=True)
    scorer_old = SemanticScorer(ulex, enable_layered=False)

    settings = get_settings()
    client = RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=settings.reddit_rate_limit,
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=settings.reddit_request_timeout_seconds,
        max_concurrency=max(2, settings.reddit_max_concurrency // 2),
    ) if args.use_reddit else None

    rows: List[Dict[str, Any]] = []
    async def process_one(name: str) -> None:
        texts: List[str] = []
        if client is not None:
            texts = await fetch_posts(client, name, limit=args.posts_per, time_filter="month", sort="top")
        metrics: Dict[str, Any] = {"name": name, "posts_sampled": len(texts)}
        for t in themes:
            new = scorer_new.score_theme(texts, t).overall_score
            old = scorer_old.score_theme(texts, t).overall_score
            metrics[f"new_{t}"] = round(new, 2)
            metrics[f"old_{t}"] = round(old, 2)
            metrics[f"delta_{t}"] = round(new - old, 2)
        rows.append(metrics)

    if client is not None:
        async with client:
            await asyncio.gather(*[process_one(n) for n in names])
    else:
        # No Reddit client: still run empty texts to exercise code path
        await asyncio.gather(*[process_one(n) for n in names])

    # Save report
    repo_root = Path(__file__).resolve().parents[2]
    out_csv = repo_root / "backend" / "data" / "semantic_compare.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        fieldnames = list(rows[0].keys())
    else:
        fieldnames = ["name", "posts_sampled"] + [f"new_{t}" for t in themes] + [f"old_{t}" for t in themes] + [f"delta_{t}" for t in themes]
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # Print correlation summary
    for t in themes:
        a = [float(r.get(f"new_{t}", 0.0)) for r in rows]
        b = [float(r.get(f"old_{t}", 0.0)) for r in rows]
        print(f"Theme={t}: correlation(new,old) = {_corr(a,b):.3f}")
    print(f"✅ Compare report written: {out_csv}")


if __name__ == "__main__":
    asyncio.run(main())

