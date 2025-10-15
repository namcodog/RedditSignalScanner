#!/usr/bin/env python3
"""
Day 13 预热爬虫触发脚本。

运行方式：
    python backend/scripts/trigger_initial_crawl.py --force-refresh
"""

from __future__ import annotations

import argparse
from typing import Any, Dict

from celery.result import AsyncResult

from app.tasks.crawler_task import crawl_seed_communities


def trigger(force_refresh: bool) -> Dict[str, Any]:
    result: AsyncResult = crawl_seed_communities.delay(force_refresh=force_refresh)
    print(f"[INFO] 已派发任务: {result.id}")
    response = result.get(timeout=None)
    print("[RESULT]", response)
    return response


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger initial crawl for seed communities.")
    parser.add_argument(
        "--force-refresh",
        dest="force_refresh",
        action="store_true",
        help="在触发前强制刷新社区池缓存。",
    )
    args = parser.parse_args()
    trigger(args.force_refresh)


if __name__ == "__main__":
    main()
