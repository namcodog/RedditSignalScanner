from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.scripts_support.env_loader import load_backend_env
from app.services.infrastructure.reddit_collect_client import build_collect_reddit_client


def _build_default_reddit_client() -> Any:
    load_backend_env()
    return build_collect_reddit_client(
        request_timeout=20.0,
        search_timeout=12.0,
        max_concurrency=1,
        low_quota_remaining_threshold=12,
        low_quota_cooldown_seconds=20.0,
        stop_comment_fetch_below_remaining=18,
        max_consecutive_rate_limit_errors=3,
    )


async def _authenticate(reddit: Any) -> None:
    auth_target = getattr(reddit, "primary", reddit)
    authenticate = getattr(auth_target, "authenticate", None)
    if authenticate is not None:
        await authenticate()


async def run_reddit_preflight(
    *,
    reddit_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    checks = {
        "oauth_token": "pending",
        "minimal_listing": "pending",
    }
    factory = reddit_factory or _build_default_reddit_client

    async with factory() as reddit:
        try:
            await _authenticate(reddit)
        except Exception as exc:
            checks["oauth_token"] = "failed"
            checks["minimal_listing"] = "skipped"
            return {
                "ok": False,
                "checks": checks,
                "error": str(exc),
            }

        checks["oauth_token"] = "ok"
        try:
            await reddit.fetch_subreddit_posts(
                "OpenAI",
                sort="hot",
                time_filter="day",
                limit=1,
            )
        except Exception as exc:
            checks["minimal_listing"] = "failed"
            result = {
                "ok": False,
                "checks": checks,
                "error": str(exc),
            }
        else:
            checks["minimal_listing"] = "ok"
            result = {
                "ok": True,
                "checks": checks,
            }

        if hasattr(reddit, "get_collect_stats"):
            result["collect_stats"] = reddit.get_collect_stats()
        return result


def main() -> int:
    result = asyncio.run(run_reddit_preflight())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
