#!/usr/bin/env python3
from __future__ import annotations

"""
Score subreddits for cross-border e-commerce themes using Reddit API.

Inputs (auto-detected, overridable by args):
  - backend/data/top5000_subreddits.json or backend/data/top5000_enriched.csv

Outputs:
  - backend/data/<basename>_scored.csv
  - reports/local-acceptance/crossborder-<theme>-top200.csv

Scoring (Option B - balanced):
  A: Scale & Activity (0..30)
     - subscribers (0..12), posts/day (0..10), comments/day (0..8)
  B: Content (simplified 0..15)
     - relevance ratio by theme (0..10), spam ratio inverse (0..5)
  C: User composition (0..10)
     - top10 author contribution ratio within reasonable band

Weighted score per theme = (A/30*wA + B/15*wB + C/10*wC) * 100
Gates: min_posts, min_relevance, max_spam_ratio (per config)
"""

import argparse
import asyncio
import csv
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml  # type: ignore

from app.core.config import get_settings
from app.services.reddit_client import API_BASE_URL, RedditAPIClient, RedditAPIError


@dataclass
class Theme:
    name: str
    include: List[str]
    aliases: List[str]
    exclude: List[str]
    stopwords: List[str]


def _load_lexicon(dir_path: Path, theme: str) -> Theme:
    path = dir_path / f"{theme}.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Theme(
        name=theme,
        include=[str(x).lower() for x in data.get("include_keywords", [])],
        aliases=[str(x).lower() for x in data.get("aliases", [])],
        exclude=[str(x).lower() for x in data.get("exclude", [])],
        stopwords=[str(x).lower() for x in data.get("stopwords", [])],
    )


def _load_scoring_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _normalise_name(name: str) -> str:
    n = name.strip()
    return n if n.lower().startswith("r/") else f"r/{n}"


def _load_names(input_path: Optional[Path]) -> List[str]:
    root = Path(__file__).resolve().parents[2]
    candidates = [
        input_path,
        root / "backend/data/top5000_subreddits.json",
        root / "backend/data/top5000_enriched.csv",
        root / "backend/data/top1000_subreddits.json",
        root / "backend/data/top1000_enriched.csv",
    ]
    for p in candidates:
        if not p:
            continue
        if p.exists():
            if p.suffix.lower() == ".json":
                payload = json.loads(p.read_text(encoding="utf-8"))
                items = payload.get("communities") or payload.get("seed_communities") or []
                names = []
                for it in items:
                    n = _normalise_name(str(it.get("name", "")))
                    if n:
                        names.append(n)
                return names
            else:
                # CSV
                rows = list(csv.DictReader(p.open("r", encoding="utf-8")))
                names = []
                for r in rows:
                    n = _normalise_name(str(r.get("name", "")))
                    if n:
                        names.append(n)
                return names
    raise FileNotFoundError("No suitable input found for names list")


async def _fetch_about(client: RedditAPIClient, name: str) -> dict[str, Any]:
    await client.authenticate()
    headers = {"Authorization": f"Bearer {client.access_token}", "User-Agent": client.user_agent}
    sub = name.lstrip("r/")
    url = f"{API_BASE_URL}/r/{sub}/about"
    return await client._request_json("GET", url, headers=headers, params=None, data=None)  # type: ignore[attr-defined]


def _score_A(subscribers: int, posts: List[dict[str, Any]]) -> float:
    # A1 subscribers (0..12)
    if subscribers >= 100_000:
        a1 = 12
    elif subscribers >= 50_000:
        a1 = 11
    elif subscribers >= 10_000:
        a1 = 10
    elif subscribers >= 5_000:
        a1 = 8
    elif subscribers >= 1_000:
        a1 = 6
    elif subscribers >= 500:
        a1 = 4
    else:
        a1 = 2

    # posts/day and comments/day over sample time span
    if not posts:
        return float(a1)
    created = sorted([p["created_utc"] for p in posts])
    if not created:
        days = 1.0
    else:
        span = max(1.0, (max(created) - min(created)) / (24 * 3600.0))
        days = span
    count = len(posts)
    total_comments = sum(int(p.get("num_comments", 0) or 0) for p in posts)
    ppd = count / days
    cpd = total_comments / days

    # A2 posts/day (0..10)
    if ppd >= 100:
        a2 = 10
    elif ppd >= 50:
        a2 = 8
    elif ppd >= 20:
        a2 = 6
    elif ppd >= 10:
        a2 = 4
    elif ppd >= 5:
        a2 = 2
    else:
        a2 = 0

    # A3 comments/day (0..8)
    if cpd >= 500:
        a3 = 8
    elif cpd >= 200:
        a3 = 6
    elif cpd >= 50:
        a3 = 4
    elif cpd >= 10:
        a3 = 2
    else:
        a3 = 0

    return float(a1 + a2 + a3)


def _score_B(posts: List[dict[str, Any]], theme: Theme, spam_keywords: List[str]) -> tuple[float, float, float]:
    if not posts:
        return 0.0, 0.0, 0.0
    include = [w.lower() for w in (theme.include + theme.aliases)]
    stop = set(theme.stopwords)
    excl = set(theme.exclude)

    def norm(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").lower()

    sample = posts[:]
    checked = 0
    hits = 0
    spam = 0
    for p in sample[:30]:
        text = norm(p.get("title", "") + " " + p.get("selftext", ""))
        checked += 1
        if any(s in text for s in spam_keywords):
            spam += 1
        # exclude
        if any(e in text for e in excl):
            continue
        if any(sw in text for sw in stop):
            continue
        if any(w in text for w in include):
            hits += 1
    if checked == 0:
        return 0.0, 0.0, 0.0
    relevance = hits / checked
    spam_ratio = spam / checked

    # B1 (0..10)
    if relevance >= 0.8:
        b1 = 10
    elif relevance >= 0.6:
        b1 = 8
    elif relevance >= 0.4:
        b1 = 5
    else:
        b1 = 2
    # B4 (0..5)
    if spam_ratio < 0.1:
        b4 = 5
    elif spam_ratio < 0.2:
        b4 = 4
    elif spam_ratio < 0.3:
        b4 = 2
    else:
        b4 = 0
    return float(b1 + b4), float(relevance), float(spam_ratio)


def _score_C(posts: List[dict[str, Any]]) -> float:
    if not posts:
        return 0.0
    authors = Counter([str(p.get("author", "")) for p in posts if p.get("author")])
    total = sum(authors.values())
    top10 = sum(v for _, v in authors.most_common(10))
    if total <= 0:
        return 0.0
    ratio = top10 / total
    # C1（集中度）
    if 0.3 <= ratio <= 0.5:
        c1 = 10
    elif ratio > 0.5:
        c1 = 7
    elif ratio > 0.15:
        c1 = 8
    else:
        c1 = 4
    # 简化：不再单独计算 C2，控制在 0..10
    return float(min(10, c1))


async def score_one(
    client: RedditAPIClient,
    name: str,
    *,
    sample_posts: int,
    time_filter: str,
    sort: str,
) -> dict[str, Any]:
    sub = name.lstrip("r/")
    about = {}
    posts_raw: List[dict[str, Any]] = []
    try:
        about_payload = await _fetch_about(client, name)
        about = about_payload.get("data", {})
    except Exception:
        about = {}
    try:
        posts = await client.fetch_subreddit_posts(
            sub,
            limit=min(100, max(10, sample_posts)),
            time_filter=time_filter,
            sort=sort,
        )
        posts_raw = [
            {
                "title": p.title,
                "selftext": p.selftext,
                "num_comments": p.num_comments,
                "created_utc": p.created_utc,
                "author": p.author,
            }
            for p in posts
        ]
    except RedditAPIError:
        posts_raw = []

    subscribers = int(about.get("subscribers", 0) or 0)
    A = _score_A(subscribers, posts_raw)
    return {
        "name": name,
        "subscribers": subscribers,
        "posts_sampled": len(posts_raw),
        "A": A,
        "posts": posts_raw,
    }


def _weighted_score(A: float, B: float, C: float, w: dict[str, float]) -> float:
    # normalize components then scale to 100
    an = A / 30.0
    bn = B / 15.0
    cn = C / 10.0
    v = (an * w.get("A", 0) + bn * w.get("B", 0) + cn * w.get("C", 0)) * 100.0
    return float(round(max(0.0, min(100.0, v)), 2))


def _load_completed_names(scored_path: Path) -> set[str]:
    if not scored_path.exists():
        return set()
    done: set[str] = set()
    try:
        with scored_path.open("r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                n = str(row.get("name", "")).strip()
                if n:
                    done.add(n)
    except Exception:
        return set()
    return done


async def main() -> int:
    parser = argparse.ArgumentParser(description="Score cross-border ecom communities")
    parser.add_argument("--input", default=None, help="Input JSON/CSV path")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument(
        "--themes",
        default="what_to_sell,how_to_sell,where_to_sell,how_to_source",
        help="Comma-separated themes",
    )
    parser.add_argument("--topn", type=int, default=200)
    parser.add_argument("--resume", action="store_true", help="Skip names already present in scored CSV")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    input_path = Path(args.input) if args.input else None

    # Load config
    cfg = _load_scoring_config(root / "backend/config/crossborder_scoring.yml")
    sample_posts = int(cfg.get("sample", {}).get("posts_per_subreddit", 30))
    time_filter = str(cfg.get("sample", {}).get("time_filter", "month"))
    sort = str(cfg.get("sample", {}).get("sort", "new"))
    weights = cfg.get("weights", {})
    gates = cfg.get("gates", {})
    spam_kw: List[str] = [str(x).lower() for x in (cfg.get("spam_keywords", []) or [])]

    # Load themes
    theme_names = [t.strip() for t in args.themes.split(",") if t.strip()]
    lex_dir = root / "backend/config/lexicons/cross_border"
    themes: dict[str, Theme] = {t: _load_lexicon(lex_dir, t) for t in theme_names}

    # Load community names
    names = _load_names(input_path)[: args.limit]

    # Reddit API client
    settings = get_settings()
    client = RedditAPIClient(
        settings.reddit_client_id,
        settings.reddit_client_secret,
        settings.reddit_user_agent,
        rate_limit=min(30, settings.reddit_rate_limit),
        rate_limit_window=settings.reddit_rate_limit_window_seconds,
        request_timeout=min(20.0, settings.reddit_request_timeout_seconds),
        max_concurrency=max(1, settings.reddit_max_concurrency // 2),
    )

    results: List[dict[str, Any]] = []
    async with client:
        sem = asyncio.Semaphore(max(1, settings.reddit_max_concurrency // 2))

        async def runner(n: str) -> None:
            async with sem:
                r = await score_one(
                    client,
                    n,
                    sample_posts=sample_posts,
                    time_filter=time_filter,
                    sort=sort,
                )
                results.append(r)

        # Resume support: skip already scored names in output CSV
        out_dir = root / "backend/data"
        out_dir.mkdir(parents=True, exist_ok=True)
        base = (input_path.stem if input_path else "top5000_subreddits") + "_scored.csv"
        scored_path = out_dir / base
        completed = _load_completed_names(scored_path) if args.resume else set()
        pending = [n for n in names if _normalise_name(n) not in completed]
        tasks = [asyncio.create_task(runner(n.lstrip("r/"))) for n in pending]
        await asyncio.gather(*tasks, return_exceptions=False)

    # Compute B/C and theme scores
    rows: List[dict[str, Any]] = []
    for r in results:
        posts = r.get("posts", [])
        A = float(r.get("A", 0.0))
        C = _score_C(posts)
        per_theme_scores: dict[str, float] = {}
        per_theme_rel: dict[str, float] = {}
        per_theme_spam: dict[str, float] = {}
        for t, theme in themes.items():
            B, rel, spam = _score_B(posts, theme, spam_kw)
            w = weights.get(t, {"A": 0.3, "B": 0.5, "C": 0.2})
            per_theme_scores[t] = _weighted_score(A, B, C, w)
            per_theme_rel[t] = rel
            per_theme_spam[t] = spam

        row = {
            "name": r["name"],
            "subscribers": r["subscribers"],
            "posts_sampled": r["posts_sampled"],
            "A": round(A, 2),
            "C": round(C, 2),
        }
        for t in theme_names:
            row[f"relevance_{t}"] = round(per_theme_rel[t], 3)
            row[f"spam_ratio_{t}"] = round(per_theme_spam[t], 3)
            row[f"weighted_score_{t}"] = per_theme_scores[t]
        rows.append(row)

    # Write scored CSV (resume-friendly: merge with existing if --resume)
    out_dir = root / "backend/data"
    out_dir.mkdir(parents=True, exist_ok=True)
    base = (input_path.stem if input_path else "top5000_subreddits") + "_scored.csv"
    scored_path = out_dir / base
    fieldnames = [
        "name",
        "subscribers",
        "posts_sampled",
        "A",
        "C",
    ] + [f"relevance_{t}" for t in theme_names] + [f"spam_ratio_{t}" for t in theme_names] + [f"weighted_score_{t}" for t in theme_names]
    # Merge when resume: keep unique by name, prefer latest rows
    if args.resume and scored_path.exists():
        existing: dict[str, dict[str, Any]] = {}
        with scored_path.open("r", encoding="utf-8") as fh:
            r = csv.DictReader(fh)
            for row in r:
                existing[str(row.get("name", ""))] = row
        for row in rows:
            existing[row["name"]] = {**existing.get(row["name"], {}), **row}
        merged = list(existing.values())
        with scored_path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            for row in merged:
                w.writerow(row)
    else:
        with scored_path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            for row in rows:
                w.writerow(row)

    # Theme top lists
    rep_dir = root / "reports/local-acceptance"
    rep_dir.mkdir(parents=True, exist_ok=True)
    for t in theme_names:
        gate_min_posts = int(gates.get("min_posts_analyzed", 20))
        gate_min_rel = float(gates.get("min_relevance", 0.3))
        gate_max_spam = float(gates.get("max_spam_ratio", 0.2))
        filtered = [
            r for r in rows
            if r["posts_sampled"] >= gate_min_posts
            and r[f"relevance_{t}"] >= gate_min_rel
            and r[f"spam_ratio_{t}"] <= gate_max_spam
        ]
        top_sorted = sorted(filtered, key=lambda x: x[f"weighted_score_{t}"], reverse=True)[: args.topn]
        outp = rep_dir / f"crossborder-{t}-top{args.topn}.csv"
        with outp.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames)
            w.writeheader()
            for row in top_sorted:
                w.writerow(row)

    print(f"✅ Scored {len(rows)} communities → {scored_path}")
    for t in theme_names:
        print(f"Top list: reports/local-acceptance/crossborder-{t}-top{args.topn}.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
