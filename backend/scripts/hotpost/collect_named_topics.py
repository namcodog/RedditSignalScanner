from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.services.hotpost.named_topic_candidate_collector import (
    build_custom_named_topic_watch,
    collect_named_topic_candidates,
)
from app.services.hotpost.named_topic_watch_profiles import load_named_topic_watch_profile
from app.services.hotpost.named_topic_watchlist import get_default_named_topic_preset, resolve_named_topic_watchlist


def main() -> None:
    load_backend_env()
    default_preset = get_default_named_topic_preset()
    parser = argparse.ArgumentParser(description="Hotpost 点名热点专项检索")
    parser.add_argument("--preset", default=default_preset)
    parser.add_argument("--watch-profile")
    parser.add_argument("--watch-profile-config")
    parser.add_argument("--topic-id", action="append", default=[])
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--scope")
    parser.add_argument("--topic-pack")
    parser.add_argument("--topic-cluster", action="append", default=[])
    parser.add_argument("--subreddit", action="append", default=[])
    parser.add_argument("--time-filter", choices=["day", "week", "month"], default=None)
    parser.add_argument("--candidate-cap", type=int, default=4)
    parser.add_argument("--mode", choices=["safe", "harvest"], default="safe")
    parser.add_argument("--discover-only", action="store_true")
    parser.add_argument("--no-persist", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    watches = _resolve_watches(args)
    items = asyncio.run(
        collect_named_topic_candidates(
            watches,
            mode=args.mode,
            persist=not args.no_persist,
            enrich_comments=not args.discover_only,
        )
    )
    payload = {
        "watch_count": len(watches),
        "candidate_count": len(items),
        "persisted": not args.no_persist,
        "discover_only": bool(args.discover_only),
        "candidate_ids": [item.candidate_id for item in items],
        "items": [
            {
                "candidate_id": item.candidate_id,
                "scope_id": item.source_scope_id,
                "topic_pack_id": item.topic_pack_id,
                "subreddit": item.matched_subreddit,
                "score": item.score,
                "num_comments": item.num_comments,
                "title": item.title,
            }
            for item in items
        ],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"watch_count={payload['watch_count']} candidate_count={payload['candidate_count']} persisted={payload['persisted']}")
    for item in payload["items"]:
        print(
            f"{item['candidate_id']} | {item['scope_id']} | {item['topic_pack_id']} | "
            f"{item['subreddit']} | {item['score']}/{item['num_comments']} | {item['title']}"
        )


def _resolve_watches(args: argparse.Namespace):
    if args.watch_profile:
        return load_named_topic_watch_profile(
            args.watch_profile,
            config_path=args.watch_profile_config,
            time_filter_override=args.time_filter,
        )
    if args.query:
        if not args.scope or not args.topic_pack or not args.subreddit:
            raise SystemExit("Custom query mode requires --scope, --topic-pack and at least one --subreddit.")
        return [
            build_custom_named_topic_watch(
                topic_id=(args.topic_id[0] if args.topic_id else "custom-topic"),
                scope_id=args.scope,
                topic_pack_id=args.topic_pack,
                topic_cluster_ids=list(args.topic_cluster),
                queries=list(args.query),
                subreddits=list(args.subreddit),
                time_filter=args.time_filter or "week",
                candidate_cap=args.candidate_cap,
            )
        ]
    watches = resolve_named_topic_watchlist(list(args.topic_id), preset=args.preset)
    if not args.time_filter:
        return watches
    return [replace(watch, time_filter=args.time_filter) for watch in watches]


if __name__ == "__main__":
    main()
