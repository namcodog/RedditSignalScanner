from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from app.services.infrastructure.reddit_client import RedditAPIError, RedditPost


def _coerce_created_utc(value: Any, iso_value: Any = None) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(iso_value, str) and iso_value:
        return datetime.fromisoformat(iso_value.replace("Z", "+00:00")).timestamp()
    return 0.0


def _full_reddit_permalink(permalink: str | None, post_id: str) -> str:
    raw = (permalink or "").strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw
    if raw.startswith("/"):
        return f"https://www.reddit.com{raw}"
    return f"https://www.reddit.com/comments/{post_id}"


def _normalize_sociavault_posts(payload: dict[str, Any]) -> list[RedditPost]:
    posts_payload = (((payload.get("data") or {}).get("posts")) or {})
    if isinstance(posts_payload, list):
        entries = posts_payload
    elif isinstance(posts_payload, dict):
        entries = list(posts_payload.values())
    else:
        entries = []

    posts: list[RedditPost] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        raw_id = str(item.get("post_id") or item.get("id") or "").strip()
        post_id = raw_id.removeprefix("t3_")
        if not post_id:
            continue
        subreddit = item.get("subreddit")
        if isinstance(subreddit, dict):
            subreddit_name = str(subreddit.get("name") or "").strip()
        else:
            subreddit_name = str(subreddit or "").strip()
        permalink = str(item.get("permalink") or "").strip()
        posts.append(
            RedditPost(
                id=post_id,
                title=str(item.get("title") or "").strip(),
                selftext=str(item.get("selftext") or item.get("body") or "").strip(),
                score=int(item.get("score") or item.get("votes") or item.get("ups") or 0),
                num_comments=int(item.get("num_comments") or item.get("comment_count") or 0),
                created_utc=_coerce_created_utc(item.get("created_utc") or item.get("created_at"), item.get("created_at_iso")),
                subreddit=subreddit_name,
                author=str(item.get("author") or item.get("author_name") or "").strip(),
                url=str(item.get("url") or _full_reddit_permalink(permalink, post_id)),
                permalink=permalink or f"/comments/{post_id}",
            )
        )
    return posts


def _flatten_sociavault_comments(payload: dict[str, Any], *, limit: int | None = None) -> list[dict[str, Any]]:
    comments_payload = (((payload.get("data") or {}).get("comments")) or {})
    if isinstance(comments_payload, list):
        entries = comments_payload
    elif isinstance(comments_payload, dict):
        entries = list(comments_payload.values())
    else:
        entries = []

    results: list[dict[str, Any]] = []

    def _walk(nodes: list[Any]) -> None:
        for node in nodes:
            if limit is not None and len(results) >= limit:
                return
            if not isinstance(node, dict):
                continue
            results.append(
                {
                    "id": str(node.get("id") or "").strip(),
                    "body": str(node.get("body") or "").strip(),
                    "score": int(node.get("score") or 0),
                    "author": str(node.get("author") or "").strip(),
                    "permalink": str(node.get("url") or node.get("permalink") or "").strip(),
                    "depth": int(node.get("depth") or 0),
                }
            )
            replies = node.get("replies")
            if isinstance(replies, dict):
                if isinstance(replies.get("items"), dict):
                    _walk(list(replies["items"].values()))
                elif isinstance(replies.get("items"), list):
                    _walk(replies["items"])
            elif isinstance(replies, list):
                _walk(replies)

    _walk(entries)
    return results[:limit] if limit is not None else results


@dataclass(slots=True)
class SociaVaultRedditClient:
    api_key: str
    base_url: str
    request_timeout: float = 20.0
    _client: httpx.AsyncClient | None = field(init=False, default=None)
    _post_urls: dict[str, str] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    async def __aenter__(self) -> "SociaVaultRedditClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def should_skip_comment_fetch(self) -> bool:
        return False

    def get_ratelimit_snapshot(self) -> dict[str, Any]:
        return {"provider": "sociavault"}

    async def fetch_subreddit_posts(
        self,
        subreddit: str,
        *,
        limit: int = 25,
        time_filter: str = "day",
        sort: str = "hot",
        after: str | None = None,
    ) -> tuple[list[RedditPost], None]:
        params: dict[str, Any] = {"subreddit": subreddit, "sort": sort}
        if sort == "top":
            params["timeframe"] = time_filter
        payload = await self._request_json("/scrape/reddit/subreddit", params=params)
        posts = _normalize_sociavault_posts(payload)[:limit]
        self._remember_posts(posts)
        return posts, None

    async def search_subreddit_page(
        self,
        subreddit: str,
        query: str,
        *,
        limit: int = 25,
        sort: str = "relevance",
        time_filter: str = "day",
        restrict_sr: bool | None = None,
        syntax: str | None = None,
        after: str | None = None,
    ) -> tuple[list[RedditPost], None]:
        params = {
            "subreddit": subreddit,
            "query": query,
            "sort": sort,
            "timeframe": time_filter,
        }
        payload = await self._request_json("/scrape/reddit/subreddit/search", params=params)
        posts = _normalize_sociavault_posts(payload)[:limit]
        self._remember_posts(posts)
        return posts, None

    async def fetch_post_comments(
        self,
        post_id: str,
        *,
        sort: str = "confidence",
        depth: int = 1,
        limit: int = 50,
        mode: str = "topn",
        comment_timeout: float | None = None,
        smart_config: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        post_url = self._post_urls.get(post_id) or f"https://www.reddit.com/comments/{post_id}"
        payload = await self._request_json("/scrape/reddit/post/comments", params={"url": post_url})
        max_items = limit if mode == "topn" else None
        return _flatten_sociavault_comments(payload, limit=max_items)

    async def _request_json(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        client = await self._ensure_client()
        try:
            response = await client.get(
                f"{self.base_url}{path}",
                params=params,
                headers={"x-api-key": self.api_key},
            )
        except httpx.TimeoutException as exc:
            raise RedditAPIError(f"SociaVault Reddit request timed out: {path}") from exc
        except httpx.HTTPError as exc:
            raise RedditAPIError(f"SociaVault Reddit request failed: {path}") from exc
        if response.status_code >= 400:
            raise RedditAPIError(f"SociaVault Reddit request failed (status={response.status_code})")
        payload = response.json()
        if not isinstance(payload, dict):
            raise RedditAPIError("SociaVault Reddit returned invalid payload.")
        if payload.get("success") is False:
            raise RedditAPIError(str(payload.get("error") or "SociaVault Reddit request failed."))
        return payload

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.request_timeout)
        return self._client

    def _remember_posts(self, posts: list[RedditPost]) -> None:
        for post in posts:
            self._post_urls[post.id] = _full_reddit_permalink(post.permalink, post.id)


__all__ = [
    "SociaVaultRedditClient",
    "_flatten_sociavault_comments",
    "_normalize_sociavault_posts",
]
