from __future__ import annotations

import argparse
import asyncio
import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set

from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.community_pool import CommunityPool
from app.services.community_category_map_service import replace_community_category_map


THEMES = [
    "what_to_sell",
    "how_to_sell",
    "where_to_sell",
    "how_to_source",
]


@dataclass
class Entry:
    name: str
    themes: Set[str] = field(default_factory=set)
    scores: Dict[str, float] = field(default_factory=dict)


def _norm_name(name: str) -> str:
    n = (name or "").strip()
    if not n:
        return n
    return n if n.startswith("r/") else f"r/{n}"


def load_toplist_csv(path: Path, theme: str) -> Dict[str, Entry]:
    data: Dict[str, Entry] = {}
    if not path.exists():
        return data
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = (row.get("name") or "").strip()
            if not raw:
                continue
            name = _norm_name(raw)
            e = data.get(name) or Entry(name=name)
            e.themes.add(theme)
            # try parse weighted score for this theme (0-100 scale)
            score_key = f"weighted_score_{theme}"
            try:
                s = float(row.get(score_key) or 0.0)
            except Exception:
                s = 0.0
            e.scores[theme] = s
            data[name] = e
    return data


async def upsert_pool(entries: Dict[str, Entry], what_only_low: bool, export_csv: Path | None) -> Dict[str, int]:
    stats = {"inserted": 0, "updated": 0, "total": 0, "high": 0, "medium": 0, "low": 0}
    rows_for_export: List[Dict[str, str]] = []
    async with SessionFactory() as db:
        for name, entry in entries.items():
            # priority/tier mapping
            theme_count = len(entry.themes)
            if theme_count >= 2:
                priority = tier = "high"
            else:
                # single-list case
                only_theme = next(iter(entry.themes)) if entry.themes else ""
                if what_only_low and only_theme == "what_to_sell":
                    priority = tier = "low"
                else:
                    priority = tier = "medium"

            stats[priority] += 1

            # categories: crossborder and per-theme tag
            categories = ["crossborder"] + [f"crossborder:{t}" for t in sorted(entry.themes)]
            # description keywords: record source themes and scores for traceability
            desc = {
                "source_lists": sorted(entry.themes),
                "scores": {k: round(v, 2) for k, v in entry.scores.items()},
            }

            # derive a quality score in 0-1 range from available weighted scores
            if entry.scores:
                q = sum(entry.scores.values()) / (len(entry.scores) * 100.0)
            else:
                q = 0.6

            # upsert
            stmt = select(CommunityPool).where(CommunityPool.name == name)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                existing.tier = tier
                existing.priority = priority
                existing.description_keywords = desc
                existing.daily_posts = existing.daily_posts or 0
                existing.avg_comment_length = existing.avg_comment_length or 100
                existing.quality_score = float(q)
                existing.is_active = True
                await replace_community_category_map(
                    db,
                    community_id=existing.id,
                    categories=categories,
                )
                stats["updated"] += 1
            else:
                pool = CommunityPool(
                    name=name,
                    tier=tier,
                    priority=priority,
                    categories=[],
                    description_keywords=desc,
                    daily_posts=0,
                    avg_comment_length=100,
                    quality_score=float(q),
                    is_active=True,
                )
                db.add(pool)
                await db.flush()
                await replace_community_category_map(
                    db,
                    community_id=pool.id,
                    categories=categories,
                )
                stats["inserted"] += 1

            rows_for_export.append(
                {
                    "name": name,
                    "priority": priority,
                    "themes": ",".join(sorted(entry.themes)),
                    "quality_score": f"{q:.2f}",
                }
            )

        await db.commit()

    stats["total"] = stats["inserted"] + stats["updated"]

    # optional export for manual verification
    if export_csv:
        export_csv.parent.mkdir(parents=True, exist_ok=True)
        with export_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "priority", "themes", "quality_score"])
            writer.writeheader()
            for r in sorted(rows_for_export, key=lambda x: (x["priority"], x["name"])):
                writer.writerow(r)
    return stats


async def main() -> None:
    parser = argparse.ArgumentParser(description="Import crossborder toplists into community_pool")
    parser.add_argument(
        "--lists",
        nargs="*",
        type=Path,
        help="CSV files to import (defaults to four crossborder top200 lists)",
    )
    parser.add_argument(
        "--export-csv",
        type=Path,
        default=Path("backend/reports/local-acceptance/crossborder_pool_freeze.csv"),
        help="Export a flat list for manual verification",
    )
    parser.add_argument(
        "--what-only-low",
        action="store_true",
        help="When a subreddit appears only in what_to_sell list, set priority=low",
    )
    args = parser.parse_args()

    default_paths = [
        Path("reports/local-acceptance/crossborder-what_to_sell-top200.csv"),
        Path("reports/local-acceptance/crossborder-how_to_sell-top200.csv"),
        Path("reports/local-acceptance/crossborder-where_to_sell-top200.csv"),
        Path("reports/local-acceptance/crossborder-how_to_source-top200.csv"),
    ]
    files = args.lists if args.lists else default_paths

    merged: Dict[str, Entry] = {}
    theme_by_file: Dict[Path, str] = {}
    # infer theme from filename
    for p in files:
        name = p.name
        theme = None
        for t in THEMES:
            if t in name:
                theme = t
                break
        if not theme:
            # fallback: ask user to ensure filename contains theme; skip
            continue
        theme_by_file[p] = theme
        part = load_toplist_csv(p, theme)
        for k, v in part.items():
            if k in merged:
                merged[k].themes.update(v.themes)
                merged[k].scores.update(v.scores)
            else:
                merged[k] = v

    stats = await upsert_pool(merged, what_only_low=args.what_only_low, export_csv=args.export_csv)
    print("✅ Toplists imported into community_pool")
    print(f"   - Inserted: {stats['inserted']}")
    print(f"   - Updated:  {stats['updated']}")
    print(f"   - Total:    {stats['total']}")
    print(f"   - Priority distribution → high={stats['high']}, medium={stats['medium']}, low={stats['low']}")
    if args.export_csv:
        print(f"   - Export:    {args.export_csv}")


if __name__ == "__main__":
    asyncio.run(main())
