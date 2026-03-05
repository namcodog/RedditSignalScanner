from __future__ import annotations

import asyncio
from collections import deque
import logging
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


class RedditGlobalRateLimitExceeded(RedditAPIError):
    """Raised when the global token bucket denies the request (fail-fast mode)."""

    def __init__(self, *, wait_seconds: int) -> None:
        super().__init__(f"Global rate limit exceeded; wait {int(wait_seconds)}s")
        self.wait_seconds = int(wait_seconds)


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
        max_retries: int = 3,  # 429 错误最大重试次数
        retry_backoff_base: float = 5.0,  # 指数退避基础等待时间（秒）
        session: Any | None = None,  # aiohttp.ClientSession
        global_rate_limiter: Any | None = None,
        fail_fast_on_global_rate_limit: bool = False,
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
        self.max_retries = max(0, max_retries)
        self.retry_backoff_base = max(1.0, retry_backoff_base)
        self._session: Any | None = session  # aiohttp.ClientSession
        self._session_owner = session is None
        self._auth_lock = asyncio.Lock()
        self._rate_lock = asyncio.Lock()
        self._request_times: Deque[float] = deque()
        self._semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        # 动态速率限制监控
        self._ratelimit_remaining: Optional[int] = None
        self._ratelimit_reset: Optional[datetime] = None
        # 可选的分布式全局速率限制器（Redis）
        self._global_limiter = global_rate_limiter
        self._fail_fast_on_global_rate_limit = bool(fail_fast_on_global_rate_limit)
        # Module logger
        global logger
        logger = logging.getLogger(__name__)

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
        after: str | None = None,
    ) -> tuple[List[RedditPost], str | None]:
        """
        Fetch posts for a single subreddit honouring rate limits.

        Args:
            subreddit: Community name without the `r/` prefix.
            limit: Maximum posts to retrieve (Reddit caps at 100 per request).
            time_filter: One of `hour`, `day`, `week`, `month`, `year`, `all`.
            sort: Listing strategy (`hot`, `new`, `top`).
            after: Pagination cursor (fullname of last post from previous request).
        """
        if not subreddit:
            raise ValueError("subreddit must be a non-empty string.")
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100 (inclusive).")

        # Ensure clean subreddit name (remove 'r/' prefix if present)
        clean_name = subreddit[2:] if subreddit.startswith("r/") else subreddit

        await self.authenticate()

        path = f"/r/{clean_name}/{sort}"
        url = f"{API_BASE_URL}{path}"
        params = {"limit": str(limit), "t": time_filter}
        if after:
            params["after"] = after
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": self.user_agent,
        }

        payload = await self._request_json("GET", url, headers=headers, params=params)
        posts = self._parse_posts(subreddit, payload)

        # Extract 'after' cursor for pagination
        next_after = payload.get("data", {}).get("after")

        return posts, next_after

    async def fetch_subreddit_posts_paginated(
        self,
        subreddit: str,
        *,
        max_posts: int = 1000,
        time_filter: str = "all",
        sort: str = "top",
    ) -> List[RedditPost]:
        """
        Fetch posts with automatic pagination (up to Reddit's limit of ~1000 posts).

        Args:
            subreddit: Community name without the `r/` prefix.
            max_posts: Maximum posts to retrieve (Reddit API limit is ~1000).
            time_filter: One of `hour`, `day`, `week`, `month`, `year`, `all`.
            sort: Listing strategy (`hot`, `new`, `top`).

        Returns:
            List of posts (up to max_posts or Reddit's limit, whichever is lower).
        """
        all_posts: List[RedditPost] = []
        after: str | None = None

        while len(all_posts) < max_posts:
            batch_size = min(100, max_posts - len(all_posts))

            posts, next_after = await self.fetch_subreddit_posts(
                subreddit=subreddit,
                limit=batch_size,
                time_filter=time_filter,
                sort=sort,
                after=after,
            )

            if not posts:
                break  # No more posts available

            all_posts.extend(posts)

            if not next_after:
                break  # Reached the end

            after = next_after

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

        return all_posts

    async def fetch_comprehensive_posts(
        self,
        subreddit: str,
        *,
        time_filter: str = "all",
        max_per_strategy: int = 1000,
    ) -> List[RedditPost]:
        """
        Fetch comprehensive posts using multiple sorting strategies.

        Combines top, new, and hot posts to get maximum coverage (up to 3000 unique posts).

        Args:
            subreddit: Community name without the `r/` prefix.
            time_filter: One of `hour`, `day`, `week`, `month`, `year`, `all`.
            max_per_strategy: Maximum posts per sorting strategy (default 1000).

        Returns:
            List of unique posts (deduplicated by post ID).
        """
        import asyncio

        # Fetch posts using three different strategies concurrently
        tasks = [
            self.fetch_subreddit_posts_paginated(
                subreddit=subreddit,
                max_posts=max_per_strategy,
                time_filter=time_filter,
                sort="top",
            ),
            self.fetch_subreddit_posts_paginated(
                subreddit=subreddit,
                max_posts=max_per_strategy,
                time_filter=time_filter,
                sort="new",
            ),
            self.fetch_subreddit_posts_paginated(
                subreddit=subreddit,
                max_posts=max_per_strategy,
                time_filter=time_filter,
                sort="hot",
            ),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Deduplicate posts by ID
        posts_dict: Dict[str, RedditPost] = {}

        for result in results:
            if isinstance(result, Exception):
                # Log error but continue with other results
                logger.warning(f"Strategy failed for r/{subreddit}: {result}")
                continue

            for post in result:
                if post.id not in posts_dict:
                    posts_dict[post.id] = post

        unique_posts = list(posts_dict.values())
        logger.info(
            f"📊 r/{subreddit}: 抓取 {len(unique_posts)} 个不重复帖子 "
            f"(top={len(results[0]) if not isinstance(results[0], Exception) else 0}, "
            f"new={len(results[1]) if not isinstance(results[1], Exception) else 0}, "
            f"hot={len(results[2]) if not isinstance(results[2], Exception) else 0})"
        )

        return unique_posts

    async def fetch_subreddit_posts_by_timestamp(
        self,
        subreddit: str,
        *,
        start_epoch: int,
        end_epoch: int,
        sort: str = "new",
        max_posts: int = 1000,
        after: str | None = None,
    ) -> tuple[List[RedditPost], str | None]:
        """
        Fetch posts using search API with timestamp range to overcome listing cap.

        Args:
            subreddit: name without r/
            start_epoch: inclusive unix epoch seconds
            end_epoch: inclusive unix epoch seconds
            sort: 'new' or 'top'
            max_posts: safety cap per slice
        """
        await self.authenticate()

        # Ensure clean subreddit name
        clean_name = subreddit[2:] if subreddit.startswith("r/") else subreddit

        collected: List[RedditPost] = []
        cursor_after: str | None = after
        while len(collected) < max_posts:
            limit = min(100, max_posts - len(collected))
            path = f"/r/{clean_name}/search"
            url = f"{API_BASE_URL}{path}"
            # Cloudsearch/Lucene syntax timestamp query
            q = f"timestamp:{int(start_epoch)}..{int(end_epoch)}"
            params = {
                "q": q,
                "restrict_sr": "1",
                "syntax": "cloudsearch",
                "sort": sort,
                "limit": str(limit),
                "t": "all",
            }
            if cursor_after:
                params["after"] = cursor_after
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": self.user_agent,
            }
            payload = await self._request_json("GET", url, headers=headers, params=params)
            posts = self._parse_posts(subreddit, payload)
            if not posts:
                break
            collected.extend(posts)
            cursor_after = payload.get("data", {}).get("after")
            if not cursor_after:
                break
            await asyncio.sleep(0.5)
        return collected, cursor_after

    async def fetch_posts_by_time_slices(
        self,
        subreddit: str,
        *,
        slices: List[tuple[int, int]],
        per_slice_max: int = 1000,
        sort: str = "new",
    ) -> List[RedditPost]:
        """
        Fetch posts across multiple timestamp slices and deduplicate by ID.
        """
        all_posts: Dict[str, RedditPost] = {}
        for start_ts, end_ts in slices:
            try:
                batch, _cursor_after = await self.fetch_subreddit_posts_by_timestamp(
                    subreddit=subreddit,
                    start_epoch=start_ts,
                    end_epoch=end_ts,
                    sort=sort,
                    max_posts=per_slice_max,
                )
                for p in batch:
                    if p.id not in all_posts:
                        all_posts[p.id] = p
            except Exception as exc:
                logger.warning("Slice fetch failed r/%s [%s..%s]: %s", subreddit, start_ts, end_ts, exc)
                continue
        return list(all_posts.values())

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
                posts, _ = await self.fetch_subreddit_posts(
                    name,
                    limit=limit_per_subreddit,
                    time_filter=time_filter,
                    sort=sort,
                )
                return posts

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

    async def search_subreddit_page(
        self,
        subreddit: str,
        query: str,
        *,
        limit: int = 100,
        sort: str = "new",
        time_filter: str = "all",
        restrict_sr: int | str = 1,
        syntax: str | None = "cloudsearch",
        after: str | None = None,
    ) -> tuple[List[RedditPost], str | None]:
        """
        Search within a specific subreddit using Reddit's search endpoint.

        This supports pagination via the `after` token returned in the
        response payload under `data.after`.

        Args:
            subreddit: Subreddit name (without r/)
            query: Search query; for time slicing use `timestamp:START..END`
            limit: Page size (max 100)
            sort: Sort strategy (`new` recommended for time slicing)
            time_filter: One of `hour`, `day`, `week`, `month`, `year`, `all`
            restrict_sr: 1 to restrict to the subreddit
            syntax: `cloudsearch` to enable timestamp range queries
            after: Pagination token from previous page (payload.data.after)

        Returns:
            (posts, next_after)
        """
        if not subreddit:
            raise ValueError("subreddit must be provided")
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100 (inclusive)")

        # Ensure clean subreddit name
        clean_name = subreddit[2:] if subreddit.startswith("r/") else subreddit

        await self.authenticate()

        url = f"{API_BASE_URL}/r/{clean_name}/search"
        params: Dict[str, str] = {
            "q": query.strip(),
            "limit": str(limit),
            "sort": sort,
            "restrict_sr": str(restrict_sr),
        }
        # 当使用 timestamp:START..END 查询时，避免再传 t（time_filter），以减少冲突
        if "timestamp:" not in query:
            params["t"] = time_filter
        if syntax:
            params["syntax"] = syntax
        if after:
            params["after"] = after
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": self.user_agent,
        }

        payload = await self._request_json("GET", url, headers=headers, params=params)
        posts = self._parse_posts(subreddit, payload)
        next_after = None
        try:
            next_after = payload.get("data", {}).get("after")
        except Exception:
            next_after = None
        return posts, next_after

    async def search_subreddits(
        self,
        query: str,
        *,
        limit: int = 20,
        after: str | None = None,
        include_nsfw: bool = False,
    ) -> list[dict[str, Any]]:
        """Search subreddits by keyword with built-in 429 backoff."""
        if not query:
            return []
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100 (inclusive).")

        await self.authenticate()
        url = f"{API_BASE_URL}/subreddits/search"
        params: Dict[str, str] = {"q": query, "limit": str(limit)}
        if after:
            params["after"] = after
        if include_nsfw:
            params["include_over_18"] = "on"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": self.user_agent,
        }
        payload = await self._request_json("GET", url, headers=headers, params=params)
        items: list[dict[str, Any]] = []
        try:
            for child in payload.get("data", {}).get("children", []):
                data = child.get("data") or {}
                name = data.get("display_name_prefixed") or data.get("display_name")
                if not name:
                    continue
                items.append(
                    {
                        "name": str(name),
                        "subscribers": int(data.get("subscribers") or 0),
                        "over18": bool(data.get("over18") or False),
                        "public_description": data.get("public_description") or "",
                        "created_utc": float(data.get("created_utc") or 0.0),
                    }
                )
        except Exception:
            logger.exception("Failed to parse subreddit search response for %s", query)
        return items

    async def fetch_post_comments(
        self,
        post_id: str,
        *,
        sort: str = "confidence",
        depth: int = 1,
        limit: int = 50,
        mode: str = "topn",
        smart_config: dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """Fetch comments for a single post.

        P0: use `/comments/{id}.json` and flatten the listing. Full-tree expansion
        via `/api/morechildren` is reserved for a later iteration.
        """
        if not post_id:
            raise ValueError("post_id must be provided")

        logger.debug("fetch_post_comments: start post_id=%s sort=%s depth=%s limit=%s mode=%s", post_id, sort, depth, limit, mode)

        await self.authenticate()
        logger.debug("fetch_post_comments: authenticated post_id=%s", post_id)

        url = f"{API_BASE_URL}/comments/{post_id}.json"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": self.user_agent,
        }

        # 为避免网络异常或 Redis 限流导致单个帖子无限等待，这里再增加一层总超时保护
        import asyncio as _asyncio

        async def _fetch_listing(
            *, sort_value: str, depth_value: int, limit_value: int
        ) -> Dict[str, Any] | None:
            params: Dict[str, str] = {
                "limit": str(max(1, min(500, limit_value))),
                "depth": str(max(0, depth_value)),
                "sort": sort_value,
                "raw_json": "1",
            }
            try:
                payload = await _asyncio.wait_for(
                    self._request_json("GET", url, headers=headers, params=params),
                    timeout=float(self.request_timeout) + 10.0,
                )
            except _asyncio.TimeoutError:
                logger.warning(
                    "fetch_post_comments timeout: post_id=%s url=%s timeout=%.1fs",
                    post_id,
                    url,
                    float(self.request_timeout) + 10.0,
                )
                return None

            logger.debug("fetch_post_comments: got payload for post_id=%s", post_id)

            # The /comments endpoint returns a list [post_listing, comments_listing]
            try:
                return payload[1]
            except Exception:
                return payload

        from app.services.crawl.comments_parser import (
            compute_smart_shallow_limits,
            flatten_reddit_comments,
            parse_morechildren_things,
            select_smart_shallow_comments,
        )

        if mode == "smart_shallow":
            cfg = smart_config or {}
            base_top_limit = int(cfg.get("smart_top_limit") or 30)
            base_new_limit = int(cfg.get("smart_new_limit") or 20)
            base_reply_top_limit = int(cfg.get("smart_reply_top_limit") or 15)
            reply_per_top = int(cfg.get("smart_reply_per_top") or 1)
            total_limit = int(cfg.get("smart_total_limit") or limit or 50)
            total_limit = max(1, min(500, total_limit))
            base_top_limit = max(1, min(200, base_top_limit))
            base_new_limit = max(0, min(200, base_new_limit))
            base_reply_top_limit = max(0, min(base_top_limit, base_reply_top_limit))
            reply_per_top = max(0, min(3, reply_per_top))

            top_limit, new_limit, reply_top_limit = compute_smart_shallow_limits(
                total_limit=total_limit,
                base_top_limit=base_top_limit,
                base_new_limit=base_new_limit,
                base_reply_top_limit=base_reply_top_limit,
                reply_per_top=reply_per_top,
            )
            effective_depth = max(depth, 2 if reply_per_top > 0 else 1)

            top_sort = str(cfg.get("smart_top_sort") or "top")
            new_sort = str(cfg.get("smart_new_sort") or "new")

            def _fetch_limit_for(
                limit_value: int, reply_top_limit_value: int, replies_per_top: int
            ) -> int:
                target = limit_value + reply_top_limit_value * replies_per_top
                target = max(limit_value + 10, target)
                return max(1, min(500, target))

            top_listing = (
                await _fetch_listing(
                    sort_value=top_sort,
                    depth_value=effective_depth,
                    limit_value=_fetch_limit_for(
                        top_limit, reply_top_limit, reply_per_top
                    ),
                )
                if top_limit > 0
                else None
            )
            new_listing = (
                await _fetch_listing(
                    sort_value=new_sort,
                    depth_value=effective_depth,
                    limit_value=max(
                        _fetch_limit_for(new_limit, 0, 0),
                        min(500, total_limit),
                    ),
                )
                if new_limit > 0
                else None
            )

            top_comments = (
                flatten_reddit_comments(top_listing, max_items=None)
                if top_listing
                else []
            )
            new_comments = (
                flatten_reddit_comments(new_listing, max_items=None)
                if new_listing
                else []
            )

            return select_smart_shallow_comments(
                top_comments=top_comments,
                new_comments=new_comments,
                top_limit=top_limit,
                new_limit=new_limit,
                reply_top_limit=reply_top_limit,
                reply_per_top=reply_per_top,
                total_limit=total_limit,
            )

        comments_listing = await _fetch_listing(
            sort_value=sort, depth_value=depth, limit_value=limit
        )
        if comments_listing is None:
            return []

        if mode == "topn":
            return flatten_reddit_comments(
                comments_listing, max_items=limit if mode == "topn" else None
            )

        # full mode: gather all "more" children and iterate /api/morechildren
        initial = flatten_reddit_comments(comments_listing, max_items=None)
        # collect "more" children ids from the initial payload
        raw_children_lists: List[List[str]] = []
        try:
            children_nodes = comments_listing.get("data", {}).get("children", [])
            for node in children_nodes:
                if node.get("kind") == "more":
                    ids = node.get("data", {}).get("children") or []
                    if ids:
                        raw_children_lists.append([str(x) for x in ids])
        except Exception:
            pass

        all_comments: List[Dict[str, Any]] = list(initial)
        pending: List[str] = []
        for ids in raw_children_lists:
            pending.extend(ids)

        # chunk and fetch up to 100 at a time
        def _chunks(seq: List[str], size: int = 100) -> List[List[str]]:
            return [seq[i : i + size] for i in range(0, len(seq), size)]

        link_id = f"t3_{post_id}"
        while pending:
            batch = pending[:100]
            pending = pending[100:]
            data = {
                "api_type": "json",
                "link_id": link_id,
                "children": ",".join(batch),
                "limit_children": "False",
                "sort": sort,
                "raw_json": "1",
            }
            url_more = f"{API_BASE_URL}/api/morechildren"
            payload_more = await self._request_json(
                "POST", url_more, headers=headers, data=data
            )
            comments_more, more_ids_lists = parse_morechildren_things(payload_more)
            all_comments.extend(comments_more)
            for ids in more_ids_lists:
                pending.extend(ids)

        return all_comments

    async def fetch_subreddit_about(self, subreddit: str) -> Dict[str, Any]:
        if not subreddit:
            raise ValueError("subreddit must be provided")
        clean_name = subreddit[2:] if subreddit.startswith("r/") else subreddit
        await self.authenticate()
        url = f"{API_BASE_URL}/r/{clean_name}/about"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": self.user_agent,
        }
        payload = await self._request_json("GET", url, headers=headers)
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        out: Dict[str, Any] = {
            "subscribers": data.get("subscribers"),
            "active_user_count": data.get("accounts_active") or data.get("active_user_count"),
            "over18": bool(data.get("over18") or data.get("over_18")),
        }
        return out

    async def fetch_subreddit_rules(self, subreddit: str) -> str:
        if not subreddit:
            raise ValueError("subreddit must be provided")
        clean_name = subreddit[2:] if subreddit.startswith("r/") else subreddit
        await self.authenticate()
        url = f"{API_BASE_URL}/r/{clean_name}/about/rules"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": self.user_agent,
        }
        payload = await self._request_json("GET", url, headers=headers)
        rules = []
        try:
            for rule in payload.get("rules", []) or []:
                title = str(rule.get("short_name") or "").strip()
                desc = str(rule.get("description") or "").strip()
                if title or desc:
                    rules.append(f"{title}: {desc}" if desc else title)
        except Exception:
            rules = []
        text_rules = "; ".join(rules)[:4000]
        return text_rules

    async def list_subreddit_page(
        self,
        subreddit: str,
        *,
        sort: str = "new",
        limit: int = 100,
        after: str | None = None,
    ) -> tuple[List[RedditPost], str | None]:
        if not subreddit:
            raise ValueError("subreddit must be provided")
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100 (inclusive)")

        clean_name = subreddit[2:] if subreddit.startswith("r/") else subreddit
        await self.authenticate()
        url = f"{API_BASE_URL}/r/{clean_name}/{sort}"
        params: Dict[str, str] = {"limit": str(limit)}
        if after:
            params["after"] = after
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": self.user_agent,
        }
        payload = await self._request_json("GET", url, headers=headers, params=params)
        posts = self._parse_posts(subreddit, payload)
        next_after = None
        try:
            next_after = payload.get("data", {}).get("after")
        except Exception:
            next_after = None
        return posts, next_after

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Issue an HTTP request with retry semantics for auth failures and rate limits.

        Implements exponential backoff for 429 (rate limit) errors.
        """
        import aiohttp  # Runtime import to avoid event loop conflicts

        session = await self._ensure_session()
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)
        last_error: Exception | None = None
        retry_count_429 = 0  # 429 错误重试计数器

        for attempt in range(2):
            await self._throttle()
            try:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    data=data,
                    timeout=timeout,
                ) as response:
                    # 提取 Reddit 速率限制响应头
                    self._update_ratelimit_info(response)

                    if response.status == 401 and attempt == 0:
                        await self._invalidate_token()
                        await self.authenticate()
                        continue

                    if response.status == 429:
                        # 速率限制错误 - 使用指数退避重试
                        retry_count_429 += 1
                        if retry_count_429 <= self.max_retries:
                            # 如果有 Retry-After，优先使用
                            retry_after = response.headers.get("Retry-After")
                            backoff_seconds = None
                            if retry_after:
                                try:
                                    backoff_seconds = float(retry_after)
                                except Exception:
                                    backoff_seconds = None
                            # 否则退回到指数退避
                            if backoff_seconds is None:
                                backoff_seconds = min(
                                    self.retry_backoff_base * (2 ** (retry_count_429 - 1)),
                                    60.0,  # 最大等待 60 秒
                                )
                            logger.warning(
                                "[RATE_LIMIT] Reddit API rate limit (429), retry %d/%d after %.1fs. "
                                "url=%s, remaining=%s, reset_at=%s",
                                retry_count_429,
                                self.max_retries,
                                backoff_seconds,
                                url,
                                self._ratelimit_remaining,
                                self._ratelimit_reset.isoformat() if self._ratelimit_reset else "unknown",
                            )
                            await asyncio.sleep(backoff_seconds)
                            continue  # 重试请求
                        else:
                            # 超过最大重试次数
                            logger.error(
                                "[RATE_LIMIT] Reddit API rate limit exceeded after %d retries. "
                                "url=%s, rate_limit=%d req/%.0fs, current_requests=%d",
                                self.max_retries,
                                url,
                                self.rate_limit,
                                self.rate_limit_window,
                                len(self._request_times),
                            )
                            raise RedditAPIError(
                                f"Reddit API rate limit exceeded after {self.max_retries} retries."
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
                    # Graceful handling for not found/private subs: treat as empty
                    if response.status in (403, 404):
                        logger.info(
                            "Reddit API client info: status=%s (treated as empty), url=%s",
                            response.status,
                            url,
                        )
                        return {}
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
                        logger.warning("Invalid JSON response from Reddit API (attempt=%s): %s", attempt + 1, exc)
                        if attempt == 0:
                            continue
                        # Treat as empty to avoid aborting long runs
                        return {}
                    else:
                        return payload
            except asyncio.TimeoutError:
                logger.warning("Reddit API request timeout (attempt=%s): %s", attempt + 1, url)
                if attempt == 0:
                    continue
                # Return empty payload on persistent timeout
                return {}
            except Exception as exc:
                # Network-level disconnects or client errors (e.g., ServerDisconnectedError)
                try:
                    import aiohttp  # type: ignore
                except Exception:
                    aiohttp = None  # type: ignore
                logger.warning("Reddit API connection error (attempt=%s): %s", attempt + 1, exc)
                if attempt == 0:
                    # brief backoff before retry
                    await asyncio.sleep(0.5)
                    continue
                return {}

        if last_error is None:
            last_error = RedditAPIError("Reddit API returned invalid JSON payload.")
        raise last_error

    async def _ensure_session(self) -> Any:  # aiohttp.ClientSession
        import aiohttp  # Runtime import to avoid event loop conflicts

        if self._session is None or getattr(self._session, "closed", False):
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout, trust_env=True)
            self._session_owner = True
        return self._session

    async def _has_valid_token(self) -> bool:
        if not self.access_token or not self.token_expires_at:
            return False
        return datetime.now(timezone.utc) < self.token_expires_at

    async def _invalidate_token(self) -> None:
        self.access_token = None
        self.token_expires_at = None

    def _update_ratelimit_info(self, response: Any) -> None:
        """从 Reddit API 响应头中提取速率限制信息。

        Reddit API 返回以下响应头：
        - X-Ratelimit-Remaining: 剩余请求配额
        - X-Ratelimit-Reset: 配额重置时间（Unix 时间戳）
        - X-Ratelimit-Used: 已使用请求数
        """
        try:
            remaining_str = response.headers.get("X-Ratelimit-Remaining")
            reset_str = response.headers.get("X-Ratelimit-Reset")

            if remaining_str is not None:
                self._ratelimit_remaining = int(float(remaining_str))

            if reset_str is not None:
                reset_timestamp = int(float(reset_str))
                self._ratelimit_reset = datetime.fromtimestamp(reset_timestamp, tz=timezone.utc)

            # 如果剩余配额很少，记录警告
            if self._ratelimit_remaining is not None and self._ratelimit_remaining < 10:
                logger.warning(
                    "[RATE_LIMIT] Low remaining quota: %d requests left, resets at %s",
                    self._ratelimit_remaining,
                    self._ratelimit_reset.isoformat() if self._ratelimit_reset else "unknown",
                )
        except (ValueError, TypeError) as exc:
            # 解析失败不影响主流程
            logger.debug("Failed to parse rate limit headers: %s", exc)

    async def _throttle(self) -> None:
        """
        Enforce the configured rate limit (requests per window).

        Uses a rolling deque of timestamps measured via `time.monotonic()` to avoid
        issues caused by system clock adjustments.
        """
        # 全局分布式限流（若配置）
        if getattr(self, "_global_limiter", None) is not None:
            wait = 0
            try:
                wait = int(await self._global_limiter.acquire())
            except Exception:
                # 全局限流出错不阻断请求，回退到本地限流
                wait = 0

            if wait and wait > 0:
                if getattr(self, "_fail_fast_on_global_rate_limit", False):
                    raise RedditGlobalRateLimitExceeded(wait_seconds=wait)

                # 防止因为 Redis 中残留的高计数导致首次请求等待一个完整窗口（例如 600 秒）
                # 对全局限流器返回的等待时间做上限裁剪，保证脚本不会长时间“看起来卡死”
                max_backoff = min(float(self.rate_limit_window), 60.0)
                sleep_for = min(float(wait), max_backoff)
                if sleep_for > 0:
                    logger.debug(
                        "Global rate limiter backoff: raw_wait=%s, sleep_for=%.1fs, window=%.1fs",
                        wait,
                        sleep_for,
                        self.rate_limit_window,
                    )
                    await asyncio.sleep(sleep_for)

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
