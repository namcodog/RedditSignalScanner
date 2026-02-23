from __future__ import annotations

import asyncio
import json
import os
import re
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.services.global_rate_limiter import GlobalRateLimiter
from app.services.hotpost.keywords import HotpostLexicon, load_default_hotpost_keywords
from app.services.hotpost.enrichment import enrich_opportunity_payload, enrich_rant_payload
from app.services.hotpost.cache import build_hotpost_cache_key, get_hotpost_cache_ttl_seconds
from app.services.hotpost.query_resolver import resolve_hotpost_query
from app.services.hotpost.report_llm import (
    apply_hotpost_llm_annotations,
    generate_hotpost_llm_report,
    merge_hotpost_llm_report,
)
from app.services.hotpost.report_export import export_markdown_report
from app.services.hotpost.detail_builder import (
    build_top_discovery_posts,
    build_top_rants,
    compute_need_urgency,
    compute_rant_intensity,
    extract_competitor_mentions,
)
from app.services.hotpost.repository import (
    create_hotpost_query,
    update_hotpost_query,
    insert_query_evidence_map,
    maybe_discover_community,
    upsert_evidence_post,
)
from app.services.hotpost.queue import HotpostQueueTracker
from app.services.hotpost.rules import (
    classify_pain_category,
    classify_intent_label,
    compute_signal_score,
    count_resonance,
    detect_discovery_signals,
    detect_opportunity_signals,
    detect_rant_signals,
    normalize_text,
)
from app.services.llm.clients.openai_client import OpenAIChatClient, resolve_llm_api_key
from app.services.reddit_client import RedditAPIClient, RedditPost
from app.schemas.hotpost import Hotpost, HotpostComment, HotpostSearchRequest, HotpostSearchResponse, PainPoint
from app.utils.url import normalize_reddit_url


DEFAULT_RATE_LIMIT = 100
DEFAULT_RATE_WINDOW = 600
COMMENTS_TTL_SECONDS = 2 * 60 * 60


class _NullRedditClient:
    async def search_subreddits(self, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        return []

    async def search_subreddit_page(self, *_args: Any, **_kwargs: Any) -> tuple[list[RedditPost], None]:
        return [], None

    async def search_posts(self, *_args: Any, **_kwargs: Any) -> list[RedditPost]:
        return []

    async def fetch_post_comments(self, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        return []

    async def close(self) -> None:
        return None


class HotpostService:
    def __init__(
        self,
        *,
        settings: Settings,
        db: AsyncSession,
        redis_client: Redis | None = None,
        lexicon: HotpostLexicon | None = None,
        reddit_client: RedditAPIClient | None = None,
    ) -> None:
        self._settings = settings
        self._db = db
        self._redis = redis_client or Redis.from_url(
            settings.reddit_cache_redis_url, decode_responses=True
        )
        self._lexicon = lexicon or load_default_hotpost_keywords()
        if reddit_client is not None:
            self._reddit = reddit_client
        elif settings.reddit_client_id and settings.reddit_client_secret:
            self._reddit = RedditAPIClient(
                settings.reddit_client_id,
                settings.reddit_client_secret,
                settings.reddit_user_agent,
                rate_limit=settings.reddit_rate_limit,
                rate_limit_window=settings.reddit_rate_limit_window_seconds,
                request_timeout=settings.reddit_request_timeout_seconds,
                max_concurrency=settings.reddit_max_concurrency,
            )
        elif settings.allow_mock_fallback or settings.environment.lower() == "test":
            self._reddit = _NullRedditClient()
        else:
            raise ValueError("REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET required for hotpost search")
        self._rate_limiter = GlobalRateLimiter(
            self._redis,
            limit=int(os.getenv("HOTPOST_RATE_LIMIT_MAX_REQUESTS", os.getenv("RATE_LIMIT_MAX_REQUESTS", DEFAULT_RATE_LIMIT))),
            window_seconds=int(os.getenv("HOTPOST_RATE_LIMIT_WINDOW_SECONDS", os.getenv("RATE_LIMIT_WINDOW_SECONDS", DEFAULT_RATE_WINDOW))),
            namespace="hotpost:qpm",
            client_id=settings.reddit_client_id or "default",
        )

    async def close(self) -> None:
        await self._reddit.close()

    def _resolve_mode(self, request: HotpostSearchRequest) -> str:
        if request.mode:
            return request.mode
        query = request.query.lower()
        rant_hints = ["口碑", "吐槽", "差评", "complaint", "rant", "issue", "problem", "broken", "hate"]
        opp_hints = ["推荐", "有没有", "替代", "recommend", "alternative", "looking for", "need", "best"]
        if any(h in query for h in rant_hints):
            return "rant"
        if any(h in query for h in opp_hints):
            return "opportunity"
        return "trending"

    @staticmethod
    def _split_search_queries(search_query: str, *, max_chars: int) -> list[str]:
        cleaned = " ".join((search_query or "").strip().split())
        if not cleaned:
            return []
        if len(cleaned) <= max_chars:
            return [cleaned]

        parts = re.split(r"\s+OR\s+", cleaned, flags=re.IGNORECASE)
        if len(parts) > 1:
            chunks: list[str] = []
            current: list[str] = []
            for part in parts:
                if not part:
                    continue
                candidate = " OR ".join(current + [part]) if current else part
                if len(candidate) > max_chars and current:
                    chunks.append(" OR ".join(current))
                    current = [part]
                else:
                    current.append(part)
            if current:
                chunks.append(" OR ".join(current))
            return chunks

        words = cleaned.split()
        chunks = []
        current = []
        for word in words:
            candidate = " ".join(current + [word]) if current else word
            if len(candidate) > max_chars and current:
                chunks.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            chunks.append(" ".join(current))
        return chunks

    @staticmethod
    def _resolve_time_filter(mode: str, request: HotpostSearchRequest) -> str:
        if request.time_filter:
            return request.time_filter
        if mode == "rant":
            return "all"
        if mode == "opportunity":
            return "month"
        return "all"

    def _resolve_sort(self, mode: str) -> str:
        if mode == "opportunity":
            return "relevance"
        if mode == "trending":
            return "top"
        return "top"

    async def _acquire_rate_budget(
        self,
        *,
        cost: int,
        queue_tracker: HotpostQueueTracker | None = None,
    ) -> None:
        wait_seconds = await self._rate_limiter.acquire(cost=cost)
        if wait_seconds > 0:
            if queue_tracker is not None:
                await queue_tracker.mark_waiting(estimated_wait_seconds=wait_seconds)
            await asyncio.sleep(float(wait_seconds))
            if queue_tracker is not None:
                await queue_tracker.mark_processing()

    async def _search_subreddit_posts(
        self,
        subreddit: str,
        query: str,
        *,
        sort: str,
        time_filter: str,
        max_posts: int,
        queue_tracker: HotpostQueueTracker | None = None,
    ) -> tuple[list[RedditPost], int]:
        posts: list[RedditPost] = []
        after: str | None = None
        calls = 0
        while len(posts) < max_posts:
            await self._acquire_rate_budget(cost=1, queue_tracker=queue_tracker)
            batch, after = await self._reddit.search_subreddit_page(
                subreddit,
                query,
                limit=min(100, max_posts - len(posts)),
                sort=sort,
                time_filter=time_filter,
                after=after,
            )
            posts.extend(batch)
            calls += 1
            if not after:
                break
        return posts, calls

    async def _fetch_comments(
        self,
        post_id: str,
        *,
        queue_tracker: HotpostQueueTracker | None = None,
    ) -> list[dict[str, Any]]:
        await self._acquire_rate_budget(cost=1, queue_tracker=queue_tracker)
        comments = await self._reddit.fetch_post_comments(
            post_id,
            sort="top",
            depth=1,
            limit=3,
            mode="topn",
        )
        trimmed: list[dict[str, Any]] = []
        for raw in comments[:3]:
            payload = dict(raw)
            body = str(payload.get("body") or "")
            payload["body"] = body[:400]
            trimmed.append(payload)
        return trimmed

    def _select_signals(self, mode: str, text: str) -> dict[str, list[str]]:
        if mode == "rant":
            return detect_rant_signals(text, self._lexicon)
        if mode == "opportunity":
            return detect_opportunity_signals(text, self._lexicon)
        return detect_discovery_signals(text, self._lexicon)

    def _sentiment_label(self, mode: str, text: str, signals: dict[str, list[str]]) -> str:
        if mode == "rant":
            if signals.get("strong") or signals.get("medium"):
                return "negative"
            return "neutral"
        discovery = detect_discovery_signals(text, self._lexicon)
        if discovery.get("positive"):
            return "positive"
        return "neutral"

    def _build_post(self, post: RedditPost, *, rank: int, signals: dict[str, list[str]]) -> Hotpost:
        text = normalize_text(f"{post.title} {post.selftext}")
        signal_score = compute_signal_score(signals, score=post.score, num_comments=post.num_comments)
        reddit_url = normalize_reddit_url(post.url, post.permalink)
        heat_score = post.score + post.num_comments * 2
        return Hotpost(
            rank=rank,
            id=post.id,
            title=post.title,
            body_preview=(post.selftext or "")[:500],
            score=post.score,
            num_comments=post.num_comments,
            heat_score=heat_score,
            rant_score=signal_score,
            rant_signals=[s for group in signals.values() for s in group],
            subreddit=post.subreddit,
            author=post.author,
            reddit_url=reddit_url,
            created_utc=post.created_utc,
            signals=[s for group in signals.values() for s in group],
            signal_score=signal_score,
            top_comments=[],
        )

    def _build_pain_points(self, posts: list[Hotpost], categories: list[str]) -> list[PainPoint]:
        counter = Counter(categories)
        points: list[PainPoint] = []
        for category, mentions in counter.most_common(5):
            sample_posts = [p for p in posts if p.subreddit and p.title and p.title]
            urls = [p.reddit_url for p in posts[:3]]
            severity = "high" if mentions >= 10 else "medium" if mentions >= 5 else "low"
            points.append(
                PainPoint(
                    category=category,
                    description=f"用户频繁提及 {category} 相关问题",
                    mentions=mentions,
                    severity=severity,
                    sample_quotes=[p.title for p in sample_posts[:2]],
                    evidence_urls=urls,
                )
            )
        return points

    def _confidence_level(self, evidence_count: int) -> str:
        if evidence_count <= 0:
            return "none"
        if evidence_count >= 20:
            return "high"
        if evidence_count >= 10:
            return "medium"
        return "low"

    async def _maybe_llm_summary(
        self,
        *,
        query: str,
        posts: list[Hotpost],
        confidence: str,
        sentiment_overview: dict[str, float] | None = None,
        community_distribution: dict[str, str] | None = None,
    ) -> str:
        if confidence in {"none", "low"}:
            return self._fallback_summary(
                posts,
                sentiment_overview=sentiment_overview,
                community_distribution=community_distribution,
            )
        api_key = resolve_llm_api_key()
        if not api_key:
            return self._fallback_summary(
                posts,
                sentiment_overview=sentiment_overview,
                community_distribution=community_distribution,
            )
        client = OpenAIChatClient(model=self._settings.llm_model_name)
        titles = "\n".join(f"- {p.title}" for p in posts[:10])
        prompt = (
            "请根据以下 Reddit 帖子标题，给出一句话洞察（不超过40字），"
            "只基于标题内容，不要编造：\n" + titles
        )
        content = await client.generate(prompt, temperature=0.3, max_tokens=120)
        return (content or "").strip() or self._fallback_summary(
            posts,
            sentiment_overview=sentiment_overview,
            community_distribution=community_distribution,
        )

    @staticmethod
    def _fallback_summary(
        posts: list[Hotpost],
        *,
        sentiment_overview: dict[str, float] | None = None,
        community_distribution: dict[str, str] | None = None,
    ) -> str:
        if not posts:
            return "暂无相关讨论，样本不足。"
        communities = {p.subreddit for p in posts if p.subreddit}
        signal_counts: Counter[str] = Counter()
        for post in posts:
            for signal in post.signals:
                signal_counts[signal] += 1
        parts = [f"找到 {len(posts)} 条相关讨论，来自 {len(communities)} 个社区。"]
        if community_distribution:
            top_communities = list(community_distribution.items())[:3]
            community_text = "、".join(f"{name}({pct})" for name, pct in top_communities)
            if community_text:
                parts.append(f"主要社区：{community_text}。")
        if signal_counts:
            top_signals = [name for name, _ in signal_counts.most_common(3)]
            parts.append(f"高频信号词：{'、'.join(top_signals)}。")
        if sentiment_overview:
            parts.append(
                "情绪分布："
                f"负向{sentiment_overview.get('negative', 0):.0%} / "
                f"中性{sentiment_overview.get('neutral', 0):.0%} / "
                f"正向{sentiment_overview.get('positive', 0):.0%}。"
            )
        return "".join(parts)

    async def search(
        self,
        request: HotpostSearchRequest,
        *,
        user_id: uuid.UUID | None = None,
        session_id: str | None = None,
        ip_hash: str | None = None,
    ) -> HotpostSearchResponse:
        start_time = time.monotonic()
        query_id = uuid.uuid4()

        mode = self._resolve_mode(request)
        time_filter = self._resolve_time_filter(mode, request)
        sort = self._resolve_sort(mode)

        llm_client = None
        enable_translation = os.getenv("ENABLE_HOTPOST_QUERY_TRANSLATION", "true").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        if enable_translation and resolve_llm_api_key():
            llm_client = OpenAIChatClient(model=self._settings.llm_model_name)
        resolution = await resolve_hotpost_query(
            request.query,
            redis_client=self._redis,
            llm_client=llm_client,
        )
        search_query = resolution.search_query or request.query
        keywords = resolution.keywords or search_query.split()
        subreddits = request.subreddits or (resolution.subreddits if resolution.subreddits else None)

        notes: list[str] = []
        max_query_chars = int(os.getenv("HOTPOST_QUERY_MAX_CHARS", "50"))
        max_query_splits = int(os.getenv("HOTPOST_MAX_QUERY_SPLITS", "3"))
        query_parts = self._split_search_queries(search_query, max_chars=max_query_chars)
        if len(query_parts) > max_query_splits:
            query_parts = query_parts[:max_query_splits]
            notes.append(f"关键词过长，已拆分为 {max_query_splits} 次查询（已截断）")
        elif len(query_parts) > 1:
            notes.append(f"关键词过长，已拆分为 {len(query_parts)} 次查询")

        cache_key = build_hotpost_cache_key(search_query, mode, subreddits)
        cache_ttl_seconds = get_hotpost_cache_ttl_seconds(mode)

        await create_hotpost_query(
            self._db,
            query_id=query_id,
            query=request.query,
            mode=mode,
            time_filter=time_filter,
            subreddits=request.subreddits,
            user_id=user_id,
            session_id=session_id,
            ip_hash=ip_hash,
            evidence_count=0,
            community_count=0,
            confidence="none",
            from_cache=False,
            latency_ms=None,
            api_calls=None,
        )
        queue_tracker = HotpostQueueTracker(
            self._redis,
            str(query_id),
            ttl_seconds=cache_ttl_seconds,
        )
        await queue_tracker.mark_processing()

        cached_raw = await self._redis.get(cache_key)
        if cached_raw:
            payload = json.loads(cached_raw)
            payload["from_cache"] = True
            payload["search_time"] = datetime.now(timezone.utc).isoformat()
            await update_hotpost_query(
                self._db,
                query_id=query_id,
                evidence_count=payload.get("evidence_count", 0),
                community_count=len(payload.get("communities", [])),
                confidence=payload.get("confidence", "low"),
                from_cache=True,
                latency_ms=int((time.monotonic() - start_time) * 1000),
                api_calls=0,
                subreddits=request.subreddits,
            )
            await queue_tracker.mark_completed()
            return HotpostSearchResponse(**payload)

        api_calls = 0
        if mode == "opportunity" and request.subreddits is None:
            subreddits = None
        if not subreddits and mode != "opportunity":
            await self._acquire_rate_budget(cost=1, queue_tracker=queue_tracker)
            suggestions = await self._reddit.search_subreddits(
                query_parts[0] if query_parts else search_query,
                limit=5,
                include_nsfw=False,
            )
            subreddits = [
                s["name"].lower()
                if str(s["name"]).startswith("r/")
                else f"r/{s['name'].lower()}"
                for s in suggestions
            ]
            api_calls += 1

        posts: list[RedditPost] = []
        seen_post_ids: set[str] = set()
        max_posts_per_sub = min(100, max(30, request.limit))
        if subreddits:
            for query_part in (query_parts or [search_query]):
                for sub in subreddits:
                    batch, calls = await self._search_subreddit_posts(
                        sub,
                        query_part,
                        sort=sort,
                        time_filter=time_filter,
                        max_posts=max_posts_per_sub,
                        queue_tracker=queue_tracker,
                    )
                    api_calls += calls
                    for post in batch:
                        if post.id in seen_post_ids:
                            continue
                        seen_post_ids.add(post.id)
                        posts.append(post)
        else:
            for query_part in (query_parts or [search_query]):
                await self._acquire_rate_budget(cost=1, queue_tracker=queue_tracker)
                batch = await self._reddit.search_posts(
                    query_part,
                    limit=min(100, request.limit),
                    time_filter=time_filter,
                    sort=sort,
                )
                api_calls += 1
                for post in batch:
                    if post.id in seen_post_ids:
                        continue
                    seen_post_ids.add(post.id)
                    posts.append(post)

        filtered: list[Hotpost] = []
        categories: list[str] = []
        sentiment_labels: list[str] = []
        signal_groups_list: list[dict[str, list[str]]] = []
        relevance_filtered = 0
        enable_relevance_filter = os.getenv("ENABLE_HOTPOST_RELEVANCE_FILTER", "true").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        relevance_terms = [term.lower() for term in keywords if term and term.isascii()]
        for post in posts:
            text = normalize_text(f"{post.title} {post.selftext}")
            signals = self._select_signals(mode, text)
            if mode in {"rant", "opportunity"}:
                if not any(signals.values()):
                    continue
            if mode == "opportunity" and enable_relevance_filter and relevance_terms:
                relevance_score = 0
                for term in relevance_terms:
                    if term and term in text:
                        relevance_score += 1
                if relevance_score == 0:
                    relevance_filtered += 1
                    continue
            category = classify_pain_category(text, self._lexicon)
            categories.append(category)
            sentiment_labels.append(self._sentiment_label(mode, text, signals))
            signal_groups_list.append(signals)
            filtered.append(self._build_post(post, rank=len(filtered) + 1, signals=signals))
            if len(filtered) >= request.limit:
                break

        top_posts = filtered[: request.limit]
        if relevance_filtered:
            notes.append(f"已过滤 {relevance_filtered} 条低相关帖子")

        # Comments and evidence mapping
        comments_cache: dict[str, list[dict[str, Any]]] = {}
        all_comments: list[HotpostComment] = []
        for idx, post in enumerate(top_posts[:30], start=1):
            comments = await self._fetch_comments(post.id, queue_tracker=queue_tracker)
            top_comment_refs: list[dict[str, Any]] = []
            hotpost_comments: list[HotpostComment] = []
            for comment in comments:
                fullname = comment.get("name") or comment.get("fullname")
                permalink = comment.get("permalink")
                body = comment.get("body")
                score = int(comment.get("score") or 0)
                author = comment.get("author")
                top_comment_refs.append(
                    {
                        "comment_fullname": fullname,
                        "permalink": permalink,
                        "score": score,
                    }
                )
                hot_comment = HotpostComment(
                    comment_fullname=fullname,
                    author=author,
                    body=body,
                    score=score,
                    permalink=permalink,
                )
                hotpost_comments.append(hot_comment)
                all_comments.append(hot_comment)
            post.top_comments = hotpost_comments

            evidence = await upsert_evidence_post(
                self._db,
                probe_source="hotpost",
                source_query=search_query,
                source_post_id=post.id,
                subreddit=post.subreddit,
                title=post.title,
                summary=post.body_preview,
                score=post.score,
                num_comments=post.num_comments,
                post_created_at=datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                evidence_score=int(post.signal_score),
            )
            await insert_query_evidence_map(
                self._db,
                query_id=query_id,
                evidence_id=evidence.id,
                rank=idx,
                signal_score=post.signal_score,
                signals=post.signals,
                top_comment_refs=top_comment_refs,
            )
            comments_cache[str(evidence.id)] = [c.model_dump() for c in hotpost_comments]

        await self._redis.setex(
            f"hotpost:comments:{query_id}",
            COMMENTS_TTL_SECONDS,
            json.dumps(comments_cache, ensure_ascii=False),
        )

        communities = [p.subreddit for p in top_posts]
        for subreddit, count in Counter(communities).items():
            await maybe_discover_community(
                self._db,
                subreddit=subreddit,
                evidence_count=count,
                query=request.query,
                keywords=keywords,
            )

        evidence_count = len(top_posts)
        community_counts = Counter(communities)
        community_distribution = {
            sub: f"{count / evidence_count * 100:.0f}%" if evidence_count else "0%"
            for sub, count in community_counts.most_common(5)
        }
        sentiment_counts = Counter(sentiment_labels)
        sentiment_overview = {
            "positive": sentiment_counts.get("positive", 0) / evidence_count if evidence_count else 0.0,
            "neutral": sentiment_counts.get("neutral", 0) / evidence_count if evidence_count else 0.0,
            "negative": sentiment_counts.get("negative", 0) / evidence_count if evidence_count else 0.0,
        }
        confidence = self._confidence_level(evidence_count)
        rant_intensity = compute_rant_intensity(signal_groups_list) if mode == "rant" else None
        need_urgency = compute_need_urgency(signal_groups_list) if mode == "opportunity" else None

        summary = await self._maybe_llm_summary(
            query=request.query,
            posts=top_posts,
            confidence=confidence,
            sentiment_overview=sentiment_overview,
            community_distribution=community_distribution,
        )
        pain_points = None
        if mode == "rant":
            pain_points = self._build_pain_points(top_posts, categories)

        me_too_count = count_resonance([c.model_dump() for c in all_comments], self._lexicon)
        opportunities = None
        if mode == "opportunity":
            opportunities = [
                {
                    "summary": "用户在讨论中表达了需求缺口",
                    "me_too_count": me_too_count,
                }
            ]

        llm_report = None
        enable_llm_report = os.getenv("ENABLE_HOTPOST_LLM_REPORT", "true").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        api_key = resolve_llm_api_key()
        if enable_llm_report and api_key and evidence_count > 0:
            max_tokens = int(
                os.getenv(
                    "HOTPOST_LLM_MAX_TOKENS",
                    os.getenv("OPENROUTER_MAX_TOKENS", "4096"),
                )
            )
            temperature = float(
                os.getenv(
                    "HOTPOST_LLM_TEMPERATURE",
                    os.getenv("OPENROUTER_TEMPERATURE", "0.3"),
                )
            )
            posts_payload = [
                {
                    "id": post.id,
                    "title": post.title,
                    "score": post.score,
                    "comments": post.num_comments,
                    "subreddit": post.subreddit,
                    "url": post.reddit_url,
                    "heat_score": post.heat_score,
                    "created_utc": post.created_utc,
                    "signals": post.signals,
                }
                for post in top_posts
            ]
            comments_payload = [
                {
                    "body": comment.body,
                    "score": comment.score,
                    "author": comment.author,
                    "permalink": comment.permalink,
                }
                for comment in all_comments
            ]
            try:
                llm_report = await generate_hotpost_llm_report(
                    mode=mode,
                    query=request.query,
                    time_filter=time_filter,
                    posts_data=posts_payload,
                    comments_data=comments_payload,
                    llm_client=OpenAIChatClient(model=self._settings.llm_model_name),
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except Exception:
                llm_report = None

        debug_info = {
            "query_source": resolution.source,
            "search_query": search_query,
            "query_parts": query_parts,
            "keywords": keywords,
            "time_filter": time_filter,
            "sort": sort,
            "subreddits": subreddits or [],
            "raw_posts": len(posts),
            "filtered_posts": len(filtered),
            "relevance_filtered": relevance_filtered,
        }

        response_payload = {
            "query_id": str(query_id),
            "query": request.query,
            "mode": mode,
            "search_time": datetime.now(timezone.utc),
            "from_cache": False,
            "status": "success",
            "summary": summary,
            "top_posts": top_posts,
            "key_comments": sorted(all_comments, key=lambda c: c.score or 0, reverse=True)[:5],
            "pain_points": pain_points,
            "opportunities": opportunities,
            "trending_keywords": None,
            "communities": list(community_counts.keys()),
            "related_queries": [],
            "evidence_count": evidence_count,
            "community_distribution": community_distribution,
            "sentiment_overview": sentiment_overview,
            "rant_intensity": rant_intensity,
            "need_urgency": need_urgency,
            "confidence": confidence,
            "notes": notes,
            "debug_info": debug_info,
        }

        response_payload = merge_hotpost_llm_report(response_payload, llm_report)
        response_payload = apply_hotpost_llm_annotations(response_payload, llm_report)

        opportunity_strength: str | None = None
        if mode == "rant":
            category_counts = Counter(categories)
            response_payload = enrich_rant_payload(
                response_payload,
                category_counts=category_counts,
                lexicon=self._lexicon,
                fallback_quotes=[p.title for p in top_posts if p.title][:3],
                evidence_count=evidence_count,
            )
            if not response_payload.get("competitor_mentions"):
                response_payload["competitor_mentions"] = extract_competitor_mentions(
                    top_posts,
                    query=request.query,
                )

            intent_counts = Counter()
            for post in top_posts:
                text = normalize_text(f"{post.title} {post.body_preview or ''}")
                intent_counts[classify_intent_label(text, self._lexicon)] += 1
            total_intents = sum(intent_counts.values())
            total_mentions = intent_counts.get("already_left", 0) + intent_counts.get("considering", 0)
            percentage = total_mentions / total_intents if total_intents else 0.0
            response_payload["migration_intent"] = {
                "already_left": f"{intent_counts.get('already_left', 0) / total_intents * 100:.0f}%"
                if total_intents
                else "0%",
                "considering": f"{intent_counts.get('considering', 0) / total_intents * 100:.0f}%"
                if total_intents
                else "0%",
                "staying_reluctantly": f"{intent_counts.get('staying_reluctantly', 0) / total_intents * 100:.0f}%"
                if total_intents
                else "0%",
                "total_mentions": total_mentions,
                "percentage": round(percentage, 4),
                "status_distribution": {
                    "already_left": intent_counts.get("already_left", 0) / total_intents if total_intents else 0.0,
                    "considering": intent_counts.get("considering", 0) / total_intents if total_intents else 0.0,
                    "staying": intent_counts.get("staying_reluctantly", 0) / total_intents if total_intents else 0.0,
                },
            }

        if mode == "opportunity":
            opportunity_strength = "weak"
            if evidence_count >= 20 and me_too_count >= 5:
                opportunity_strength = "strong"
            elif evidence_count >= 10:
                opportunity_strength = "medium"
            response_payload["opportunity_strength"] = opportunity_strength
            response_payload = enrich_opportunity_payload(
                response_payload,
                me_too_count=me_too_count,
                opportunity_strength=opportunity_strength,
            )

        if mode == "rant":
            response_payload["top_rants"] = build_top_rants(top_posts)
            migration = response_payload.get("migration_intent") or {}
            destinations: list[dict[str, object]] = []
            competitors = response_payload.get("competitor_mentions") or []
            for comp in competitors:
                if hasattr(comp, "model_dump"):
                    comp_data = comp.model_dump()
                elif isinstance(comp, dict):
                    comp_data = comp
                else:
                    continue
                destinations.append(
                    {
                        "name": comp_data.get("name"),
                        "mentions": comp_data.get("mentions"),
                        "sentiment": comp_data.get("sentiment"),
                    }
                )
            if destinations:
                migration["destinations"] = destinations
            if not migration.get("key_quote") and top_posts:
                first_comments = top_posts[0].top_comments or []
                if first_comments:
                    migration["key_quote"] = first_comments[0].body
            response_payload["migration_intent"] = migration

        if mode == "opportunity":
            response_payload["top_discovery_posts"] = build_top_discovery_posts(top_posts)
            response_payload["opportunity_strength"] = opportunity_strength
            market = response_payload.get("market_opportunity")
            if isinstance(market, dict):
                if opportunity_strength:
                    market.setdefault("strength", opportunity_strength)
                response_payload["market_opportunity"] = market

        if evidence_count < 10:
            response_payload["reliability_note"] = f"当前样本量 {evidence_count} 条，样本有限，仅供预览。"
        else:
            response_payload["reliability_note"] = f"基于 {evidence_count} 条证据帖的抽样结果。"

        response_payload["next_steps"] = {
            "deepdive_available": True,
            "deepdive_token": None,
            "suggested_keywords": keywords[:5],
        }

        enable_markdown = os.getenv("ENABLE_HOTPOST_MARKDOWN_EXPORT", "true").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        if enable_markdown:
            response_payload["markdown_report"] = export_markdown_report(response_payload)

        response_payload["evidence_count"] = evidence_count
        response_payload["community_distribution"] = community_distribution
        response_payload["sentiment_overview"] = sentiment_overview
        response_payload["confidence"] = confidence

        response = HotpostSearchResponse(**response_payload)

        if llm_report:
            await self._redis.setex(
                f"hotpost:llm_report:{query_id}",
                cache_ttl_seconds,
                json.dumps(llm_report, ensure_ascii=False),
            )

        await update_hotpost_query(
            self._db,
            query_id=query_id,
            evidence_count=evidence_count,
            community_count=len(community_counts),
            confidence=confidence,
            from_cache=False,
            latency_ms=int((time.monotonic() - start_time) * 1000),
            api_calls=api_calls,
            subreddits=subreddits,
        )

        await self._redis.setex(
            cache_key,
            cache_ttl_seconds,
            response.model_dump_json(),
        )
        await self._redis.setex(
            f"hotpost:result:{query_id}",
            cache_ttl_seconds,
            response.model_dump_json(),
        )

        return response


__all__ = ["HotpostService"]
