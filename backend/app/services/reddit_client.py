from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Deque, Dict, Iterable, List, Optional, Sequence

# Delay aiohttp import to avoid event loop conflicts during pytest collection
if TYPE_CHECKING:
    pass

TOKEN_ENDPOINT = "https://www.reddit.com/api/v1/access_token"
API_BASE_URL = "https://oauth.reddit.com"
USER_AGENT_FALLBACK = "RedditSignalScanner/1.0 (+https://github.com/)"


class RedditAPIError(RuntimeError):
    """Raised when the Reddit API returns an unexpected response."""


class RedditAuthenticationError(RedditAPIError):
    """Raised when OAuth2 authentication fails."""


@dataclass(slots=True)
class RedditPost:
    """Structured representation of a Reddit submission."""

    id: str
    title: str
    selftext: str
    score: int
    num_comments: int
    created_utc: float
    subreddit: str
    author: str
    url: str
    permalink: str


class RedditAPIClient:
    """
    Async Reddit API client honouring the cache-first contract defined in PRD-03.

    The implementation keeps the surface minimal so tests can stub out the HTTP session
    without depending on external services.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str | None = None,
        *,
        rate_limit: int = 60,
        rate_limit_window: float = 60.0,
        request_timeout: float = 30.0,
        max_concurrency: int = 5,
        session: Any | None = None,  # aiohttp.ClientSession
    ) -> None:
        if not client_id or not client_secret:
            raise ValueError(
                "client_id and client_secret are required for Reddit API access."
            )

        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent or USER_AGENT_FALLBACK
        self.rate_limit = max(1, rate_limit)
        self.rate_limit_window = max(0.1, rate_limit_window)
        self.request_timeout = max(1.0, request_timeout)
        self._session: Any | None = session  # aiohttp.ClientSession
        self._session_owner = session is None
        self._auth_lock = asyncio.Lock()
        self._rate_lock = asyncio.Lock()
        self._request_times: Deque[float] = deque()
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

    async def __aenter__(self) -> "RedditAPIClient":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Dispose the underlying HTTP session when owned by the client."""
        if (
            self._session_owner
            and self._session is not None
            and not self._session.closed
        ):
            await self._session.close()

    async def authenticate(self) -> None:
        """
        Acquire (or refresh) the OAuth2 access token.

        The Reddit API allows application-only flows via client credentials. Tokens
        typically last 1 hour; we renew 60 seconds early to avoid race conditions.
        """
        import aiohttp  # Runtime import to avoid event loop conflicts

        if await self._has_valid_token():
            return

        async with self._auth_lock:
            if await self._has_valid_token():
                return

            session = await self._ensure_session()
            headers = {"User-Agent": self.user_agent}
            auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
            data = {"grant_type": "client_credentials"}
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)

            async with session.request(
                "POST",
                TOKEN_ENDPOINT,
                data=data,
                headers=headers,
                auth=auth,
                timeout=timeout,
            ) as response:
                if response.status >= 400:
                    text = await response.text()
                    raise RedditAuthenticationError(
                        f"Failed to authenticate with Reddit API (status={response.status}): {text}"
                    )
                payload: Dict[str, Any] = await response.json()

            token = payload.get("access_token")
            expires_in = int(payload.get("expires_in", 3600))
            if not token:
                raise RedditAuthenticationError(
                    "Reddit authentication response missing access_token."
                )

            buffer_seconds = min(60, max(5, int(expires_in * 0.1)))
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=expires_in - buffer_seconds
            )

            self.access_token = str(token)
            self.token_expires_at = expires_at

    async def fetch_subreddit_posts(
        self,
        subreddit: str,
        *,
        limit: int = 100,
        time_filter: str = "week",
        sort: str = "top",
    ) -> List[RedditPost]:
        """
        Fetch posts for a single subreddit honouring rate limits.

        Args:
            subreddit: Community name without the `r/` prefix.
            limit: Maximum posts to retrieve (Reddit caps at 100).
            time_filter: One of `hour`, `day`, `week`, `month`, `year`, `all`.
            sort: Listing strategy (`hot`, `new`, `top`).
        """
        if not subreddit:
            raise ValueError("subreddit must be a non-empty string.")
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100 (inclusive).")

        await self.authenticate()

        path = f"/r/{subreddit}/{sort}"
        url = f"{API_BASE_URL}{path}"
        params = {"limit": str(limit), "t": time_filter}
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": self.user_agent,
        }

        payload = await self._request_json("GET", url, headers=headers, params=params)
        return self._parse_posts(subreddit, payload)

    async def fetch_multiple_subreddits(
        self,
        subreddits: Sequence[str],
        *,
        limit_per_subreddit: int = 100,
        time_filter: str = "week",
        sort: str = "top",
    ) -> Dict[str, List[RedditPost]]:
        """Fetch multiple subreddits concurrently while respecting rate limits."""
        if not subreddits:
            return {}

        unique_subreddits = list(
            dict.fromkeys(name.strip() for name in subreddits if name.strip())
        )
        if not unique_subreddits:
            return {}

        await self.authenticate()

        async def _runner(name: str) -> List[RedditPost]:
            async with self._semaphore:
                return await self.fetch_subreddit_posts(
                    name,
                    limit=limit_per_subreddit,
                    time_filter=time_filter,
                    sort=sort,
                )

        tasks = [asyncio.create_task(_runner(name)) for name in unique_subreddits]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data: Dict[str, List[RedditPost]] = {}
        for subreddit, result in zip(unique_subreddits, results):
            if isinstance(result, Exception):
                raise RedditAPIError(
                    f"Failed to fetch subreddit {subreddit}: {result}"
                ) from result
            # Type guard: result is List[RedditPost] after Exception check
            assert isinstance(result, list), "Expected list of RedditPost"
            data[subreddit] = result
        return data

    async def search_posts(
        self,
        query: str,
        *,
        limit: int = 100,
        time_filter: str = "week",
        sort: str = "relevance",
    ) -> List[RedditPost]:
        """Search Reddit for posts matching a query.

        Args:
            query: Search query string
            limit: Maximum posts to retrieve (Reddit caps at 100)
            time_filter: One of `hour`, `day`, `week`, `month`, `year`, `all`
            sort: Sort strategy (`relevance`, `hot`, `top`, `new`, `comments`)

        Returns:
            List of matching Reddit posts
        """
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100 (inclusive)")

        await self.authenticate()

        url = f"{API_BASE_URL}/search"
        params = {
            "q": query.strip(),
            "limit": str(limit),
            "t": time_filter,
            "sort": sort,
            "type": "link",  # Only search for posts, not comments
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": self.user_agent,
        }

        payload = await self._request_json("GET", url, headers=headers, params=params)
        return self._parse_posts("all", payload)

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Issue an HTTP request with retry-once semantics for authentication failures."""
        import aiohttp  # Runtime import to avoid event loop conflicts

        session = await self._ensure_session()
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)
        last_error: Exception | None = None

        for attempt in range(2):
            await self._throttle()
            async with session.request(
                method,
                url,
                headers=headers,
                params=params,
                data=data,
                timeout=timeout,
            ) as response:
                if response.status == 401 and attempt == 0:
                    await self._invalidate_token()
                    await self.authenticate()
                    continue
                if response.status == 429:
                    # 速率限制错误 - 特别监控
                    logger.error(
                        "[RATE_LIMIT] Reddit API rate limit exceeded (429). "
                        "url=%s, rate_limit=%d req/%ds, current_requests=%d",
                        url,
                        self.rate_limit,
                        self.rate_limit_window,
                        len(self._request_times),
                    )
                    raise RedditAPIError(
                        "Reddit API rate limit exceeded. Please try again later."
                    )
                if response.status >= 500:
                    # P3-5 修复: 不暴露 Reddit API 原始错误文本
                    logger.error(
                        "Reddit API server error: status=%s, url=%s",
                        response.status,
                        url,
                    )
                    raise RedditAPIError(
                        f"Reddit API temporarily unavailable (status={response.status})"
                    )
                if response.status >= 400:
                    # P3-5 修复: 不暴露 Reddit API 原始错误文本
                    logger.warning(
                        "Reddit API client error: status=%s, url=%s",
                        response.status,
                        url,
                    )
                    raise RedditAPIError(
                        f"Reddit API request failed (status={response.status})"
                    )
                try:
                    payload: Dict[str, Any] = await response.json()
                except Exception as exc:  # pragma: no cover - defensive guard
                    logger.error("Invalid JSON response from Reddit API: %s", exc)
                    last_error = RedditAPIError("Invalid response format from Reddit API")
                else:
                    return payload

        if last_error is None:
            last_error = RedditAPIError("Reddit API returned invalid JSON payload.")
        raise last_error

    async def _ensure_session(self) -> Any:  # aiohttp.ClientSession
        import aiohttp  # Runtime import to avoid event loop conflicts

        if self._session is None or getattr(self._session, "closed", False):
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
            self._session_owner = True
        return self._session

    async def _has_valid_token(self) -> bool:
        if not self.access_token or not self.token_expires_at:
            return False
        return datetime.now(timezone.utc) < self.token_expires_at

    async def _invalidate_token(self) -> None:
        self.access_token = None
        self.token_expires_at = None

    async def _throttle(self) -> None:
        """
        Enforce the configured rate limit (requests per window).

        Uses a rolling deque of timestamps measured via `time.monotonic()` to avoid
        issues caused by system clock adjustments.
        """
        if self.rate_limit <= 0:
            return

        import time

        while True:
            async with self._rate_lock:
                now = time.monotonic()
                window_start = now - self.rate_limit_window
                self._discard_outdated_requests(window_start)

                if len(self._request_times) < self.rate_limit:
                    self._request_times.append(now)
                    return

                oldest = self._request_times[0]
                sleep_for = max(0.0, self.rate_limit_window - (now - oldest))
            await asyncio.sleep(sleep_for)

    def _discard_outdated_requests(self, threshold: float) -> None:
        while self._request_times and self._request_times[0] <= threshold:
            self._request_times.popleft()

    @staticmethod
    def _parse_posts(subreddit: str, payload: Dict[str, Any]) -> List[RedditPost]:
        data_section = payload.get("data", {})
        children: Iterable[Dict[str, Any]] = data_section.get("children", [])
        posts: List[RedditPost] = []

        for child in children:
            item = child.get("data", {})
            try:
                posts.append(
                    RedditPost(
                        id=str(item.get("id", "")),
                        title=str(item.get("title", "") or ""),
                        selftext=str(item.get("selftext", "") or ""),
                        score=int(item.get("score", 0) or 0),
                        num_comments=int(item.get("num_comments", 0) or 0),
                        created_utc=float(item.get("created_utc", 0.0) or 0.0),
                        subreddit=str(item.get("subreddit", subreddit) or subreddit),
                        author=str(item.get("author", "unknown") or "unknown"),
                        url=str(item.get("url", "") or ""),
                        permalink=f"https://reddit.com{item.get('permalink', '')}",
                    )
                )
            except (TypeError, ValueError) as exc:
                raise RedditAPIError(
                    f"Invalid post payload encountered: {exc}"
                ) from exc

        return posts


__all__ = [
    "RedditAPIClient",
    "RedditAPIError",
    "RedditAuthenticationError",
    "RedditPost",
]
