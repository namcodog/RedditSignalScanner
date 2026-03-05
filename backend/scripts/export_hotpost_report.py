from __future__ import annotations

import argparse
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.schemas.hotpost import HotpostSearchRequest
from app.services.hotpost.report_export import export_markdown_report
from app.services.hotpost.service import HotpostService


def _default_output_path(query: str) -> Path:
    safe = "".join(ch if ch.isalnum() else "_" for ch in query).strip("_") or "hotpost"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return Path("reports") / f"hotpost_report_{safe}_{ts}.md"


async def _run(
    query: str,
    mode: str,
    output: Path,
    subreddits: list[str] | None,
    time_filter: str | None,
    limit: int,
) -> None:
    settings = get_settings()
    async with SessionFactory() as db:
        service = HotpostService(settings=settings, db=db)
        try:
            request = HotpostSearchRequest(
                query=query,
                mode=mode,
                subreddits=subreddits,
                time_filter=time_filter,
                limit=limit,
            )
            response = await service.search(request, session_id="hotpost-export")
        finally:
            await service.close()

    payload = response.model_dump()
    md = export_markdown_report(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(md, encoding="utf-8")
    print(f"✅ Markdown report saved: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Hotpost markdown report")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--mode", default="trending", choices=["trending", "rant", "opportunity"])
    parser.add_argument("--subreddits", nargs="+", default=None, help="指定目标 subreddit 列表，如 r/SexToys r/sextoys")
    parser.add_argument("--time-filter", default=None, choices=["week", "month", "year", "all"], help="时间窗口")
    parser.add_argument("--limit", type=int, default=30, help="最大帖子数")
    parser.add_argument("--output", default="", help="Output markdown path")
    args = parser.parse_args()

    output = Path(args.output) if args.output else _default_output_path(args.query)
    asyncio.run(
        _run(
            args.query,
            args.mode,
            output,
            args.subreddits,
            args.time_filter,
            args.limit,
        )
    )


if __name__ == "__main__":
    main()
