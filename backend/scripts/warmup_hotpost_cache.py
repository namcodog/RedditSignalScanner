"""爆帖速递缓存预热。

Usage:
    cd backend
    export $(cat .env | grep -v '^#' | xargs)
    python scripts/warmup_hotpost_cache.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.schemas.hotpost import HotpostSearchRequest
from app.services.hotpost.service import HotpostService

DEFAULT_WARMUP_QUERIES = [
    {"query": "AI工具", "mode": "trending"},
    {"query": "Adobe", "mode": "rant"},
    {"query": "跨境电商", "mode": "opportunity"},
]


def _load_warmup_queries() -> list[dict[str, str]]:
    raw = os.getenv("HOTPOST_WARMUP_QUERIES")
    if not raw:
        return DEFAULT_WARMUP_QUERIES
    try:
        parsed = json.loads(raw)
    except Exception:
        return DEFAULT_WARMUP_QUERIES
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return DEFAULT_WARMUP_QUERIES


async def main() -> None:
    settings = get_settings()
    queries = _load_warmup_queries()

    async with SessionFactory() as db:
        service = HotpostService(settings=settings, db=db)
        try:
            for item in queries:
                query = str(item.get("query", "")).strip()
                mode = str(item.get("mode", "trending")).strip() or "trending"
                if not query:
                    continue
                print(f"warming up: {query} ({mode})")
                request = HotpostSearchRequest(query=query, mode=mode)
                await service.search(request, session_id="warmup-script")
        finally:
            await service.close()


if __name__ == "__main__":
    asyncio.run(main())
