#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.services.community_pool_loader import CommunityPoolLoader, CommunityProfile
from app.services.incremental_crawler import IncrementalCrawler
from app.services.reddit_client import RedditAPIClient


def load_cfg() -> Mapping[str, Any]:
    for p in [Path("backend/config/crawler.yml"), Path("config/crawler.yml")]:
        if p.exists():
            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {}


def tier_by_name(cfg: Mapping[str, Any], name: str) -> Mapping[str, Any] | None:
    tiers = cfg.get("tiers") or []
    for t in tiers:
        if str(t.get("name","")) == name:
            return t
    return None


def all_match_tiers_for_scope(cfg: Mapping[str, Any], scope: str) -> set[str]:
    if scope.lower() == "all":
        s: set[str] = set()
        for t in (cfg.get("tiers") or []):
            for v in (t.get("match_tiers") or []):
                s.add(str(v).lower())
        return s
    t = tier_by_name(cfg, scope)
    if not t:
        return set()
    return {str(v).lower() for v in (t.get("match_tiers") or [])}


def resolve_sort_from_mix(mix: Mapping[str, Any] | None, default: str) -> str:
    if not mix:
        return default
    try:
        known = {k: float(v) for k, v in mix.items() if k in {"top","new","hot","rising"}}
        if not known:
            return default
        return max(known.items(), key=lambda x: x[1])[0]
    except Exception:
        return default


async def crawl_once(scope: str, force_refresh: bool, limit: int) -> dict[str, Any]:
    cfg = load_cfg()
    g = cfg.get("global") or {}
    default_limit = int(g.get("post_limit", 100))
    default_time_filter = str(g.get("time_filter", "month"))
    default_sort = str(g.get("sort", "top"))
    default_ttl = int(g.get("hot_cache_ttl_hours", 24))

    allowed = all_match_tiers_for_scope(cfg, scope)
    settings = get_settings()

    async with SessionFactory() as db:
        loader = CommunityPoolLoader(db)
        if force_refresh:
            await loader.load_seed_communities()
        seeds = await loader.load_community_pool(force_refresh=force_refresh)
    # filter seeds by allowed tiers (if scope != all)
    def _match(p: CommunityProfile) -> bool:
        if not allowed:
            return True
        try:
            return str(p.tier).lower() in allowed
        except Exception:
            return True

    selected = [p for p in seeds if _match(p)]
    if limit > 0:
        selected = selected[:limit]

    async def _run_for_profiles(profiles: list[CommunityProfile]) -> list[dict[str, Any]]:
        client = RedditAPIClient(
            settings.reddit_client_id,
            settings.reddit_client_secret,
            settings.reddit_user_agent,
            rate_limit=settings.reddit_rate_limit,
            rate_limit_window=settings.reddit_rate_limit_window_seconds,
            request_timeout=settings.reddit_request_timeout_seconds,
            max_concurrency=settings.reddit_max_concurrency,
        )
        results: list[dict[str, Any]] = []
        async with client:
            sem = asyncio.Semaphore( max(1, int(g.get("concurrency", 2))) )

            async def worker(p: CommunityProfile) -> dict[str, Any]:
                async with sem:
                    # resolve per-tier
                    tcfg = None
                    for t in (cfg.get("tiers") or []):
                        if str(p.tier).lower() in {str(x).lower() for x in (t.get("match_tiers") or [])}:
                            tcfg = t
                            break
                    limit = int((tcfg or {}).get("post_limit", default_limit))
                    tfilter = str((tcfg or {}).get("time_filter", default_time_filter))
                    sort = resolve_sort_from_mix((tcfg or {}).get("sort_mix"), default_sort)
                    ttl = int((tcfg or {}).get("hot_cache_ttl_hours", default_ttl))

                    async with SessionFactory() as crawl_db:
                        crawler = IncrementalCrawler(db=crawl_db, reddit_client=client, hot_cache_ttl_hours=ttl)
                        return await crawler.crawl_community_incremental(p.name, limit=limit, time_filter=tfilter, sort=sort)

            batches: list[list[CommunityProfile]] = []
            bs = int(g.get("batch_size", 12))
            for i in range(0, len(profiles), max(1, bs)):
                batches.append(profiles[i:i+max(1, bs)])
            for b in batches:
                parts = await asyncio.gather(*[worker(p) for p in b], return_exceptions=True)
                for p, outcome in zip(b, parts):
                    if isinstance(outcome, Exception):
                        results.append({"community": p.name, "status": "failed", "error": str(outcome)})
                    else:
                        results.append(outcome)
        return results

    res = await _run_for_profiles(selected)
    total_new = sum(int(x.get("new_posts",0)) for x in res if isinstance(x, dict))
    succ = sum(1 for x in res if isinstance(x, dict) and x.get("watermark_updated"))
    fail = sum(1 for x in res if isinstance(x, dict) and x.get("status") == "failed")
    payload = {
        "scope": scope,
        "force_refresh": bool(force_refresh),
        "limit": limit,
        "total": len(selected),
        "succeeded": succ,
        "failed": fail,
        "total_new_posts": total_new,
        "communities": res,
    }
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path("reports/local-acceptance")
    out.mkdir(parents=True, exist_ok=True)
    (out / f"crawl-once-{scope}-{ts}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="T1", choices=["T1","T2","T3","all"], help="Tier scope to crawl once")
    ap.add_argument("--force-refresh", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="Max communities to crawl (0 = no limit)")
    args = ap.parse_args()
    return 0 if asyncio.run(crawl_once(args.scope, args.force_refresh, args.limit)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
