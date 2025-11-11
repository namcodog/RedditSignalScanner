from __future__ import annotations

"""
Semantic scoring v0 using a YAML lexicon (coverage × density × purity).

Inputs:
  - --lexicon backend/config/semantic_sets/crossborder.yml
  - --input backend/data/crossborder_candidates.json (default)
  - --limit N (only first N communities)
  - --posts-per 10 (posts per subreddit)
  - --topn 200 (generate TopN per theme)

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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import yaml

import logging
from app.core.config import get_settings
from app.services.reddit_client import RedditAPIClient, RedditAPIError


logger = logging.getLogger(__name__)


@dataclass
class ThemeLexicon:
    brands: List[str]
    features: List[str]
    pain_points: List[str]
    aliases: Dict[str, List[str]]
    exclude: List[str]
    weights: Dict[str, float]

    def all_terms(self) -> List[str]:
        return sorted(set(self.brands + self.features + self.pain_points))


def load_lexicon(path: Path) -> Dict[str, ThemeLexicon]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: Dict[str, ThemeLexicon] = {}
    for theme, cfg in (data.get("themes") or {}).items():
        out[theme] = ThemeLexicon(
            brands=list(cfg.get("brands") or []),
            features=list(cfg.get("features") or []),
            pain_points=list(cfg.get("pain_points") or []),
            aliases=dict(cfg.get("aliases") or {}),
            exclude=list(cfg.get("exclude") or []),
            weights=dict(cfg.get("weights") or {"brands": 1.5, "features": 1.0, "pain_points": 1.2}),
        )
    return out


def compile_patterns(terms: Iterable[str]) -> List[Tuple[str, re.Pattern[str]]]:
    pats: List[Tuple[str, re.Pattern[str]]] = []
    for t in terms:
        t = t.strip()
        if not t:
            continue
        esc = re.escape(t)
        if re.search(r"[A-Za-z]", t):
            pat = re.compile(rf"\b{esc}\b", re.IGNORECASE)
        else:
            pat = re.compile(esc, re.IGNORECASE)
        pats.append((t, pat))
    return pats


_TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9\-+/]{2,}")


def token_count(texts: List[str]) -> int:
    total = 0
    for txt in texts:
        total += len(_TOKEN.findall(txt or ""))
    return max(1, total)


async def fetch_posts(client: RedditAPIClient, subreddit: str, *, limit: int, time_filter: str, sort: str) -> List[str]:
    raw = subreddit[2:] if subreddit.lower().startswith("r/") else subreddit
    try:
        posts = await client.fetch_subreddit_posts(raw, limit=limit, time_filter=time_filter, sort=sort)
    except (RedditAPIError, Exception) as exc:  # treat as empty
        logger.warning("fetch_posts failed for %s: %s", subreddit, exc)
        return []
    texts: List[str] = []
    for p in posts:
        texts.append(p.title or "")
        if p.selftext:
            texts.append(p.selftext)
    return texts


def score_theme(texts: List[str], theme: ThemeLexicon) -> Tuple[float, Dict[str, float]]:
    # Prepare patterns
    terms = theme.all_terms()
    term_pats = compile_patterns(terms)
    excl_pats = compile_patterns(theme.exclude)

    # Count hits
    hits: Dict[str, int] = {t: 0 for t in terms}
    excl_hits = 0
    for t, pat in term_pats:
        for txt in texts:
            m = pat.findall(txt)
            if m:
                hits[t] += len(m)
    for _t, pat in excl_pats:
        for txt in texts:
            excl_hits += len(pat.findall(txt))

    unique = sum(1 for k, v in hits.items() if v > 0)
    total_terms = max(1, len(terms))
    coverage = unique / total_terms

    total_tokens = token_count(texts)
    total_mentions = sum(hits.values())
    density = min(1.0, total_mentions / max(10.0, total_tokens / 50.0))  # ~ 50 tokens → 1 mention baseline

    purity = 1.0 - (excl_hits / max(1.0, excl_hits + total_mentions))

    # multiplicative score, stabilised
    alpha, beta, gamma = 0.5, 0.3, 0.2
    score = (coverage ** alpha) * (density ** beta) * (purity ** gamma)
    score = max(0.0, min(1.0, float(score)))
    return score, {
        "coverage": coverage,
        "density": density,
        "purity": purity,
        "mentions": float(total_mentions),
        "unique_terms": float(unique),
        "tokens": float(total_tokens),
    }


async def main() -> None:
    ap = argparse.ArgumentParser(description="Semantic scoring with lexicon v0")
    ap.add_argument("--lexicon", type=Path, default=Path("backend/config/semantic_sets/crossborder.yml"))
    ap.add_argument("--input", type=Path, default=Path("backend/data/crossborder_candidates.json"))
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--posts-per", type=int, default=10)
    ap.add_argument("--topn", type=int, default=200)
    args = ap.parse_args()

    # Load input
    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    items = payload.get("communities") or payload
    names: List[str] = [str((it.get("name") if isinstance(it, Mapping) else it) or "").strip() for it in items]
    names = [n if n.startswith("r/") else f"r/{n}" for n in names if n]
    if args.limit and args.limit > 0:
        names = names[: args.limit]

    # Load lexicon
    lex = load_lexicon(args.lexicon)
    themes = ["what_to_sell", "how_to_sell", "where_to_sell", "how_to_source"]

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

    out_rows: List[Dict[str, Any]] = []
    per_theme_top: Dict[str, List[Dict[str, Any]]] = {t: [] for t in themes}

    async with client:
        sem = asyncio.Semaphore(6)

        async def process_one(name: str) -> None:
            async with sem:
                texts = await fetch_posts(client, name, limit=args.posts_per, time_filter="month", sort="top")
                metrics: Dict[str, Any] = {"name": name, "posts_sampled": len(texts)}
                for t in themes:
                    score, detail = score_theme(texts, lex[t])
                    metrics[f"semantic_score_{t}"] = round(score * 100.0, 2)
                    metrics[f"coverage_{t}"] = round(detail["coverage"], 4)
                    metrics[f"density_{t}"] = round(detail["density"], 4)
                    metrics[f"purity_{t}"] = round(detail["purity"], 4)
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


if __name__ == "__main__":
    asyncio.run(main())
