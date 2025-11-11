from __future__ import annotations

from typing import Optional


def normalize_reddit_url(url: Optional[str] = None, permalink: Optional[str] = None) -> str:
    """Return an absolute reddit post URL when possible.

    Rules:
    - Prefer a full URL that already contains reddit domain.
    - If `url` is relative like "/r/..." or missing but `permalink` is present,
      build "https://www.reddit.com{permalink}".
    - If `url` is full but not a reddit domain and `permalink` exists, prefer the permalink.
    - Fallback to "https://www.reddit.com" to avoid empty values.
    """

    def _is_full(u: str) -> bool:
        return u.startswith("http://") or u.startswith("https://")

    def _is_reddit(u: str) -> bool:
        return "reddit.com" in u or "redd.it" in u

    # 1) If url is full and reddit-like, return it
    if url:
        u = url.strip()
        if _is_full(u) and _is_reddit(u):
            return u
        # relative like /r/foo/comments/...
        if u.startswith("/r/"):
            return f"https://www.reddit.com{u}"

    # 2) Try permalink
    if permalink:
        p = permalink.strip()
        if _is_full(p):
            if _is_reddit(p):
                return p
        if p.startswith("/r/") or p.startswith("/comments/") or p.startswith("/r/"):
            return f"https://www.reddit.com{p}"

    # 3) If url is full but non-reddit and we have nothing else, keep it
    if url:
        u = url.strip()
        if _is_full(u):
            return u

    # 4) Final fallback
    return "https://www.reddit.com"


__all__ = ["normalize_reddit_url"]

