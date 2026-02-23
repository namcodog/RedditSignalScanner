#!/usr/bin/env python3
"""
Incremental import for community_pool/community_cache.

 - Default behavior: only insert new communities; do NOT modify existing ones.
 - Optional --update-existing: update tier/priority (and categories/keywords if provided) for existing rows.
 - Does not delete or reactivate; admin界面仍负责停用/删除（is_active=false）。
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionFactory
from app.models.community_cache import CommunityCache
from app.models.community_pool import CommunityPool
from app.services.community_category_map_service import replace_community_category_map


def _normalise_name(name: str) -> str:
    raw = name.strip()
    if not raw:
        raise ValueError("community name is empty")
    if not raw.lower().startswith("r/"):
        raw = f"r/{raw}"
    # 保留原大小写，但用 r/ 前缀统一
    return raw


def _parse_json_field(value: str | None) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        obj = json.loads(value)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def load_items(path: Path, default_tier: str, default_priority: str) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"file not found: {path}")
    if path.suffix.lower() != ".csv":
        raise ValueError("only CSV is supported")

    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return []

    # Detect header
    header = [col.strip().lower() for col in rows[0]]
    has_header = "name" in header
    items: List[Dict[str, Any]] = []

    if has_header:
        dict_reader = csv.DictReader(open(path, "r", encoding="utf-8-sig"))
        for row in dict_reader:
            name = _normalise_name(row.get("name", ""))
            tier = (row.get("tier") or default_tier).strip().lower()
            priority = (row.get("priority") or default_priority).strip().lower()
            categories = _parse_json_field(row.get("categories"))
            description_keywords = _parse_json_field(row.get("description_keywords"))
            items.append(
                {
                    "name": name,
                    "tier": tier,
                    "priority": priority,
                    "categories": categories,
                    "description_keywords": description_keywords,
                }
            )
    else:
        for row in rows:
            if not row:
                continue
            name = row[0].strip()
            if not name or name.lower() == "社区名称":
                continue
            items.append(
                {
                    "name": _normalise_name(name),
                    "tier": default_tier,
                    "priority": default_priority,
                    "categories": {},
                    "description_keywords": {},
                }
            )
    return items


async def import_incremental(
    items: List[Dict[str, Any]],
    *,
    update_existing: bool,
    default_freq_hours: int,
) -> Dict[str, int]:
    now = datetime.now(timezone.utc)
    stats = {"inserted": 0, "updated": 0, "skipped": 0}

    async with SessionFactory() as session:
        names = [item["name"] for item in items]
        existing_rows = await session.execute(
            select(CommunityPool).where(CommunityPool.name.in_(names))
        )
        existing_map: Dict[str, CommunityPool] = {
            row.name: row for row in existing_rows.scalars().all()
        }

        pending_map_updates: list[tuple[CommunityPool, object | None]] = []

        for item in items:
            name = item["name"]
            tier = item["tier"] or "medium"
            priority = item["priority"] or tier
            raw_categories = item.get("categories")
            categories = raw_categories if raw_categories is not None else None
            description_keywords = item.get("description_keywords") or {}

            if name in existing_map:
                stats["skipped"] += 1
                if not update_existing:
                    continue
                pool_row = existing_map[name]
                pool_row.tier = tier
                pool_row.priority = priority
                if categories is not None:
                    await replace_community_category_map(
                        session,
                        community_id=pool_row.id,
                        categories=categories,
                    )
                if description_keywords:
                    pool_row.description_keywords = description_keywords
                stats["updated"] += 1
                continue

            pool = CommunityPool(
                name=name,
                tier=tier,
                priority=priority,
                categories=[],
                description_keywords=description_keywords,
                daily_posts=0,
                avg_comment_length=0,
                quality_score=0.5,
                is_active=True,
            )
            session.add(pool)
            pending_map_updates.append((pool, categories))

            cache = CommunityCache(
                community_name=name,
                last_crawled_at=now - timedelta(hours=default_freq_hours),
                ttl_seconds=3600,
                crawl_frequency_hours=default_freq_hours,
                quality_score=0.5,
                empty_hit=0,
                success_hit=0,
                failure_hit=0,
                is_active=True,
            )
            session.add(cache)
            stats["inserted"] += 1

        await session.flush()
        for pool, categories in pending_map_updates:
            if categories is None:
                continue
            await replace_community_category_map(
                session,
                community_id=pool.id,
                categories=categories,
            )

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Incrementally import communities (append-only by default)."
    )
    parser.add_argument(
        "-f",
        "--file",
        required=True,
        help="CSV file of communities (supports header with name,tier,priority,categories,description_keywords)",
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Allow updating existing communities' tier/priority (and provided categories/keywords).",
    )
    parser.add_argument(
        "--default-tier",
        default="medium",
        help="Tier used when not provided in CSV (default: medium).",
    )
    parser.add_argument(
        "--default-priority",
        default=None,
        help="Priority used when not provided; defaults to tier if omitted.",
    )
    parser.add_argument(
        "--default-frequency-hours",
        type=int,
        default=4,
        help="Initial crawl frequency hours for new cache rows (default: 4).",
    )
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    default_priority = args.default_priority or args.default_tier
    try:
        items = load_items(Path(args.file), args.default_tier, default_priority)
    except Exception as exc:  # pragma: no cover - CLI guardrail
        print(f"❌ failed to load file: {exc}")
        return 1

    if not items:
        print("✅ no items to import; nothing to do.")
        return 0

    stats = await import_incremental(
        items,
        update_existing=args.update_existing,
        default_freq_hours=args.default_frequency_hours,
    )
    print(
        f"✅ import finished: inserted={stats['inserted']}, "
        f"updated={stats['updated']}, skipped={stats['skipped']}"
    )
    return 0


def main() -> None:
    exit_code = asyncio.run(async_main())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
