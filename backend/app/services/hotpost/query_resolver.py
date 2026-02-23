from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Iterable, Literal

from redis.asyncio import Redis

from app.services.llm.clients.openai_client import OpenAIChatClient
from app.utils.subreddit import normalize_subreddit_name


_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")


@dataclass(frozen=True)
class HotpostQueryResolution:
    original_query: str
    search_query: str
    keywords: list[str]
    subreddits: list[str]
    source: Literal["original", "cache", "llm", "fallback"]


def _contains_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text or ""))


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _safe_json_loads(payload: str) -> dict[str, Any] | None:
    try:
        return json.loads(payload)
    except Exception:
        # Try to extract the first JSON object if the model wrapped it with text.
        try:
            start = payload.find("{")
            end = payload.rfind("}")
            if start >= 0 and end > start:
                return json.loads(payload[start : end + 1])
        except Exception:
            return None
    return None


def _sanitize_keywords(items: Iterable[Any]) -> list[str]:
    cleaned: list[str] = []
    for item in items:
        value = str(item or "").strip()
        if not value or _contains_cjk(value):
            continue
        cleaned.append(value)
    return cleaned


def _sanitize_subreddits(items: Iterable[Any]) -> list[str]:
    cleaned: list[str] = []
    for item in items:
        value = normalize_subreddit_name(str(item or "").strip())
        if not value:
            continue
        cleaned.append(value)
    return _dedupe(cleaned)


async def resolve_hotpost_query(
    query: str,
    *,
    redis_client: Redis | None,
    llm_client: OpenAIChatClient | None,
) -> HotpostQueryResolution:
    original = (query or "").strip()
    if not original:
        return HotpostQueryResolution(
            original_query=original,
            search_query=original,
            keywords=[],
            subreddits=[],
            source="original",
        )

    if not _contains_cjk(original):
        return HotpostQueryResolution(
            original_query=original,
            search_query=original,
            keywords=[],
            subreddits=[],
            source="original",
        )

    cache_ttl = int(os.getenv("HOTPOST_QUERY_TRANSLATE_TTL_SECONDS", "86400"))
    cache_key = (
        "hotpost:query_translate:"
        + hashlib.sha256(original.lower().encode("utf-8")).hexdigest()
    )
    if redis_client is not None:
        cached = await redis_client.get(cache_key)
        if cached:
            cached_payload = _safe_json_loads(cached)
            if cached_payload:
                return HotpostQueryResolution(
                    original_query=original,
                    search_query=str(cached_payload.get("search_query") or original).strip()
                    or original,
                    keywords=list(cached_payload.get("keywords") or []),
                    subreddits=list(cached_payload.get("subreddits") or []),
                    source="cache",
                )

    if llm_client is None:
        return HotpostQueryResolution(
            original_query=original,
            search_query=original,
            keywords=[],
            subreddits=[],
            source="fallback",
        )

    system = (
        "你是 Reddit 搜索关键词解析助手。将中文问题转换为英文搜索词。"
        "只输出 JSON，不要多余文字。"
        "字段：query_en（字符串），keywords（数组），subreddits（数组）。"
        "关键词和社区名必须是英文。社区名可带或不带 r/ 前缀。"
        "每个数组最多 6 个。"
    )
    user = f"用户输入: {original}"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    try:
        content = await llm_client.generate(
            messages,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=int(os.getenv("HOTPOST_QUERY_TRANSLATE_MAX_TOKENS", "200")),
        )
    except Exception:
        content = ""

    parsed = _safe_json_loads(content or "")
    if not parsed:
        return HotpostQueryResolution(
            original_query=original,
            search_query=original,
            keywords=[],
            subreddits=[],
            source="fallback",
        )

    query_en = str(parsed.get("query_en") or "").strip()
    if _contains_cjk(query_en):
        query_en = ""

    keywords = _sanitize_keywords(parsed.get("keywords") or [])
    subreddits = _sanitize_subreddits(parsed.get("subreddits") or [])

    search_query = query_en or " ".join(keywords[:3]) or original
    resolution = HotpostQueryResolution(
        original_query=original,
        search_query=search_query,
        keywords=keywords,
        subreddits=subreddits,
        source="llm",
    )

    if redis_client is not None:
        await redis_client.setex(
            cache_key,
            cache_ttl,
            json.dumps(
                {
                    "search_query": resolution.search_query,
                    "keywords": resolution.keywords,
                    "subreddits": resolution.subreddits,
                },
                ensure_ascii=False,
            ),
        )

    return resolution


__all__ = ["HotpostQueryResolution", "resolve_hotpost_query"]
