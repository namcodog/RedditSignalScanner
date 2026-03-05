from __future__ import annotations

"""
Semantic scoring (refactored) using UnifiedLexicon + SemanticScorer.

Inputs:
  - --lexicon backend/config/semantic_sets/unified_lexicon.yml (default to crossborder_v2.2_calibrated.yml)
  - --input backend/data/crossborder_candidates.json (default)
  - --limit N (only first N communities)
  - --posts-per 10 (posts per subreddit)
  - --topn 200 (generate TopN per theme)
  - --enable-layered (use layered scoring, default true)

Outputs:
  - backend/data/crossborder_semantic_scored.csv (per sub aggregated scores)
  - reports/local-acceptance/crossborder-semantic-{theme}-top{topn}.csv
"""

import argparse
import asyncio
import csv
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import logging
import sqlalchemy as sa

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.infrastructure.reddit_client import RedditAPIClient, RedditAPIError
from app.services.semantic import UnifiedLexicon, SemanticScorer


logger = logging.getLogger(__name__)


_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9\-+/]{2,}")


def token_count(texts: List[str]) -> int:
    total = 0
    for txt in texts:
        total += len(_TOKEN.findall(txt or ""))
    return max(1, total)


def _clean_texts(raw_texts: Iterable[Any]) -> List[str]:
    """Normalize and filter texts to avoid non-string TypeError."""
    cleaned: List[str] = []
    for t in raw_texts:
        if isinstance(t, bytes):
            try:
                s = t.decode("utf-8", errors="ignore")
            except Exception:
                continue
        else:
            s = str(t) if t is not None else ""
        s = s.strip()
        if not s:
            continue
        cleaned.append(s)
    return cleaned


async def fetch_posts_from_reddit(
    client: RedditAPIClient,
    subreddit: str,
    *,
    limit: int,
    time_filter: str,
    sort: str,
) -> List[str]:
    raw = subreddit[2:] if subreddit.lower().startswith("r/") else subreddit
    try:
        posts = await client.fetch_subreddit_posts(raw, limit=limit, time_filter=time_filter, sort=sort)
    except (RedditAPIError, Exception) as exc:  # treat as empty
        logger.warning("fetch_posts failed for %s: %s", subreddit, exc)
        return []
    texts: List[str] = []
    for p in posts:
        # Handle both Post objects and dict/list responses
        if isinstance(p, dict):
            texts.append(p.get("title", "") or "")
            if p.get("selftext"):
                texts.append(p["selftext"])
        elif isinstance(p, list):
            # Skip nested lists
            continue
        elif hasattr(p, "title"):
            texts.append(p.title or "")
            if hasattr(p, "selftext") and p.selftext:
                texts.append(p.selftext)
    return texts


async def fetch_posts_from_db(subreddit: str, *, limit: int) -> tuple[List[str], int]:
    """Fetch recent post texts for a subreddit from local DB (posts_raw + comments).

    Returns (texts, posts_sampled).
    """
    raw = subreddit[2:] if subreddit.lower().startswith("r/") else subreddit
    sub_key = raw.lower()
    texts: List[str] = []
    posts_sampled = 0

    async with SessionFactory() as session:
        # Posts from posts_raw (current version, last 12 months)
        stmt_posts = sa.text(
            """
            SELECT title, body
            FROM posts_raw
            WHERE lower(subreddit) = :sub
              AND is_current = true
              AND created_at >= (NOW() - INTERVAL '12 months')
            ORDER BY created_at DESC
            LIMIT :limit
            """
        )
        result_posts = await session.execute(stmt_posts, {"sub": sub_key, "limit": limit})
        rows = result_posts.fetchall()
        posts_sampled = len(rows)
        for title, body in rows:
            if title:
                texts.append(title)
            if body:
                texts.append(body)

        # Optional: a bit of recent comments to enrich context
        stmt_comments = sa.text(
            """
            SELECT body
            FROM comments
            WHERE lower(subreddit) = :sub
              AND created_utc >= (NOW() - INTERVAL '12 months')
            ORDER BY created_utc DESC
            LIMIT :climit
            """
        )
        result_comments = await session.execute(stmt_comments, {"sub": sub_key, "climit": max(limit, 20)})
        for (body,) in result_comments.fetchall():
            if body:
                texts.append(body)

    cleaned = _clean_texts(texts)
    return cleaned, posts_sampled


def score_theme_refactored(texts: List[str], scorer: SemanticScorer, theme: str) -> Dict[str, float]:
    res = scorer.score_theme(texts, theme)
    return {
        "overall": round(res.overall_score, 2),
        "coverage": round(res.coverage, 4),
        "density": round(res.density, 4),
        "purity": round(res.purity, 4),
        "mentions": float(res.mentions),
        "unique_terms": float(res.unique_terms),
        "tokens": float(res.tokens),
    }


async def main() -> None:
    ap = argparse.ArgumentParser(description="Semantic scoring with lexicon v0")
    ap.add_argument("--lexicon", type=Path, default=Path("backend/config/semantic_sets/unified_lexicon.yml"))
    ap.add_argument("--input", type=Path, default=Path("backend/data/crossborder_candidates.json"))
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--posts-per", type=int, default=10)
    ap.add_argument("--topn", type=int, default=200)
    ap.add_argument("--enable-layered", action="store_true", default=True)
    ap.add_argument(
        "--from-pool",
        action="store_true",
        default=False,
        help="If set, ignore --input and score only communities present in community_pool.",
    )
    args = ap.parse_args()

    # Load input community list
    if args.from_pool:
        # 仅从当前 community_pool 中读取社区列表
        async with SessionFactory() as session:
            result = await session.execute(
                sa.text(
                    "SELECT name FROM community_pool "
                    "WHERE is_active = true "
                    "ORDER BY tier, name"
                )
            )
            names: List[str] = [str(row[0]).strip() for row in result.fetchall() if row[0]]
    else:
        if not args.input.exists():
            raise SystemExit(f"Input not found: {args.input}")
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        items = payload.get("communities") or payload
        names = [str((it.get("name") if isinstance(it, Mapping) else it) or "").strip() for it in items]
        names = [n if n.startswith("r/") else f"r/{n}" for n in names if n]

    if args.limit and args.limit > 0:
        names = names[: args.limit]

    # Load lexicon via UnifiedLexicon
    ulex = UnifiedLexicon(args.lexicon)
    themes = list((ulex._themes or {}).keys()) or ["what_to_sell", "how_to_sell", "where_to_sell", "how_to_source"]
    scorer = SemanticScorer(ulex, enable_layered=bool(args.enable_layered))

    out_rows: List[Dict[str, Any]] = []
    per_theme_top: Dict[str, List[Dict[str, Any]]] = {t: [] for t in themes}

    # Reddit client kept仅作为兜底，正常优先走本地 posts_raw + comments
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

    async with client:
        sem = asyncio.Semaphore(6)

        async def process_one(name: str) -> None:
            async with sem:
                # 1) 优先从本地数据库取样文本
                texts, posts_sampled = await fetch_posts_from_db(name, limit=args.posts_per)

                # 2) 如本地完全无数据，可选兜底 Reddit（避免阻塞）
                if not texts:
                    fallback = await fetch_posts_from_reddit(
                        client,
                        name,
                        limit=args.posts_per,
                        time_filter="month",
                        sort="top",
                    )
                    texts = _clean_texts(fallback)
                    posts_sampled = len(texts)

                metrics: Dict[str, Any] = {"name": name, "posts_sampled": posts_sampled}
                if not texts:
                    # 无文本样本，直接记录空分
                    for t in themes:
                        metrics[f"semantic_score_{t}"] = 0.0
                        metrics[f"coverage_{t}"] = 0.0
                        metrics[f"density_{t}"] = 0.0
                        metrics[f"purity_{t}"] = 0.0
                    out_rows.append(metrics)
                    return

                for t in themes:
                    detail = score_theme_refactored(texts, scorer, t)
                    metrics[f"semantic_score_{t}"] = detail["overall"]
                    metrics[f"coverage_{t}"] = detail["coverage"]
                    metrics[f"density_{t}"] = detail["density"]
                    metrics[f"purity_{t}"] = detail["purity"]
                out_rows.append(metrics)

        await asyncio.gather(*[process_one(n) for n in names])

    # write combined scored table
    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = repo_root / "backend"
    out_csv = backend_dir / "data" / "crossborder_semantic_scored.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "name",
        "posts_sampled",
        *[f"semantic_score_{t}" for t in themes],
        *[f"coverage_{t}" for t in themes],
        *[f"density_{t}" for t in themes],
        *[f"purity_{t}" for t in themes],
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in out_rows:
            writer.writerow(r)

    # top lists per theme
    report_dir = repo_root / "reports" / "local-acceptance"
    report_dir.mkdir(parents=True, exist_ok=True)
    for theme in themes:
        key = f"semantic_score_{theme}"
        sorted_rows = sorted(out_rows, key=lambda x: x.get(key, 0.0), reverse=True)[: args.topn]
        outp = report_dir / f"crossborder-semantic-{theme}-top{args.topn}.csv"
        with outp.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "name",
                    "posts_sampled",
                    key,
                    f"coverage_{theme}",
                    f"density_{theme}",
                    f"purity_{theme}",
                ],
            )
            writer.writeheader()
            for r in sorted_rows:
                writer.writerow(
                    {
                        "name": r["name"],
                        "posts_sampled": r["posts_sampled"],
                        key: r.get(key, 0.0),
                        f"coverage_{theme}": r.get(f"coverage_{theme}", 0.0),
                        f"density_{theme}": r.get(f"density_{theme}", 0.0),
                        f"purity_{theme}": r.get(f"purity_{theme}", 0.0),
                    }
                )

    print(f"✅ Semantic scored table: {out_csv}")
    print("Top lists:")
    for theme in themes:
        print(f" - {theme}: reports/local-acceptance/crossborder-semantic-{theme}-top{args.topn}.csv")

    # 将语义评分回写到 community_pool.semantic_quality_score（仅更新存在的社区）
    async with SessionFactory() as session:
        for r in out_rows:
            name = str(r.get("name") or "").strip()
            if not name:
                continue
            scores: List[float] = []
            for t in themes:
                val = r.get(f"semantic_score_{t}")
                if isinstance(val, (int, float)):
                    scores.append(float(val))
            if not scores:
                continue
            # 简单取平均作为整体语义质量分，并夹在 [0, 1] 区间
            avg_score = sum(scores) / len(scores)
            score = max(0.0, min(1.0, avg_score))
            await session.execute(
                sa.text(
                    "UPDATE community_pool "
                    "SET semantic_quality_score = :score "
                    "WHERE name = :name"
                ),
                {"score": score, "name": name},
            )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
