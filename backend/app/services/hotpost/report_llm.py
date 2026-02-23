from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from app.services.hotpost.prompts import PROMPT_TEMPLATES
from app.schemas.hotpost import (
    CompetitorMention,
    ExistingTool,
    HotpostTopic,
    HotpostTopicEvidence,
    MarketOpportunity,
    MigrationIntent,
    PainPoint,
    TopQuote,
    UnmetNeed,
    UnmetNeedEvidence,
    UserSegment,
)

logger = logging.getLogger(__name__)


class HotpostLLMClient(Protocol):
    async def generate(
        self,
        prompt: str | list[dict[str, str]],
        *,
        response_format: dict[str, str] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        ...


LLM_MERGE_FIELDS = {
    "summary",
    "topics",
    "trending_keywords",
    "pain_points",
    "competitor_mentions",
    "migration_intent",
    "top_quotes",
    "unmet_needs",
    "existing_tools",
    "user_segments",
    "market_opportunity",
}


def _get_post_value(post: Any, field: str) -> Any:
    if isinstance(post, dict):
        return post.get(field)
    if hasattr(post, field):
        return getattr(post, field)
    if hasattr(post, "model_dump"):
        return post.model_dump().get(field)
    return None


def _set_post_value(post: Any, field: str, value: Any) -> None:
    if isinstance(post, dict):
        post[field] = value
        return
    if hasattr(post, field):
        try:
            setattr(post, field, value)
        except Exception:
            return


def _build_evidence_from_post(post: Any) -> dict[str, Any]:
    title = _get_post_value(post, "title")
    score = _get_post_value(post, "score")
    comments = _get_post_value(post, "num_comments")
    subreddit = _get_post_value(post, "subreddit")
    url = _get_post_value(post, "reddit_url")
    key_quote = None
    top_comments = _get_post_value(post, "top_comments") or []
    if isinstance(top_comments, list) and top_comments:
        first = top_comments[0]
        if isinstance(first, dict):
            key_quote = first.get("body")
        elif hasattr(first, "body"):
            key_quote = getattr(first, "body")
    return {
        "title": title,
        "score": score,
        "comments": comments,
        "subreddit": subreddit,
        "url": url,
        "key_quote": key_quote,
    }


def _build_evidence_post(post: Any) -> dict[str, Any]:
    if isinstance(post, dict):
        payload = dict(post)
    elif hasattr(post, "model_dump"):
        payload = post.model_dump()
    else:
        payload = {}
    if "rant_score" not in payload and payload.get("signal_score") is not None:
        payload["rant_score"] = payload.get("signal_score")
    if "rant_signals" not in payload and payload.get("signals") is not None:
        payload["rant_signals"] = payload.get("signals")
    return payload


def _attach_evidence_from_ids(
    items: list[dict[str, Any]] | None,
    posts_by_id: dict[str, Any],
) -> None:
    if not items:
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        evidence_ids = item.pop("evidence_post_ids", None)
        if not evidence_ids:
            continue
        evidence: list[dict[str, Any]] = []
        evidence_posts: list[dict[str, Any]] = []
        for post_id in evidence_ids:
            post = posts_by_id.get(str(post_id))
            if not post:
                continue
            evidence.append(_build_evidence_from_post(post))
            evidence_posts.append(_build_evidence_post(post))
        item["evidence"] = evidence
        item["evidence_posts"] = evidence_posts


def apply_hotpost_llm_annotations(
    base: dict[str, Any],
    llm_report: dict[str, Any] | None,
) -> dict[str, Any]:
    if not llm_report:
        return base
    merged = dict(base)
    posts = merged.get("top_posts") or []
    posts_by_id = {
        str(_get_post_value(post, "id")): post
        for post in posts
        if _get_post_value(post, "id")
    }

    annotations = llm_report.get("post_annotations") or {}
    if isinstance(annotations, dict):
        for post_id, meta in annotations.items():
            if post_id not in posts_by_id:
                continue
            why = None
            if isinstance(meta, dict):
                why = meta.get("why_relevant")
            if why:
                _set_post_value(posts_by_id[post_id], "why_relevant", why)

    for field in ("topics", "pain_points", "unmet_needs"):
        items = merged.get(field)
        if isinstance(items, list):
            _attach_evidence_from_ids(items, posts_by_id)

    return merged


def _safe_json_loads(payload: str) -> dict[str, Any] | None:
    try:
        return json.loads(payload)
    except Exception:
        try:
            start = payload.find("{")
            end = payload.rfind("}")
            if start >= 0 and end > start:
                return json.loads(payload[start : end + 1])
        except Exception:
            return None
    return None


def render_hotpost_prompt(
    *,
    mode: str,
    query: str,
    time_filter: str,
    posts_data: list[dict[str, Any]],
    comments_data: list[dict[str, Any]],
) -> str:
    if mode not in PROMPT_TEMPLATES:
        raise ValueError(f"Unsupported hotpost mode: {mode}")
    template = PROMPT_TEMPLATES[mode]
    escaped = template.replace("{", "{{").replace("}", "}}")
    for token in ("query", "time_filter", "posts_json", "comments_json"):
        escaped = escaped.replace(f"{{{{{token}}}}}", f"{{{token}}}")
    posts_json = json.dumps(posts_data, ensure_ascii=False, indent=2)
    comments_json = json.dumps(comments_data, ensure_ascii=False, indent=2)
    return escaped.format(
        query=query,
        time_filter=time_filter,
        posts_json=posts_json,
        comments_json=comments_json,
    )


def merge_hotpost_llm_report(
    base: dict[str, Any],
    llm_report: dict[str, Any] | None,
) -> dict[str, Any]:
    if not llm_report:
        return base
    merged = dict(base)
    for field in LLM_MERGE_FIELDS:
        if field not in llm_report:
            continue
        value = llm_report.get(field)
        if value is None:
            continue
        merged[field] = value
    return merged


def _filter_model_fields(
    payload: dict[str, Any],
    *,
    model_cls: Any,
    extra_allow: set[str] | None = None,
) -> tuple[dict[str, Any], set[str]]:
    allowed = set(getattr(model_cls, "model_fields", {}).keys())
    if extra_allow:
        allowed |= extra_allow
    unknown = set(payload.keys()) - allowed
    cleaned = {k: v for k, v in payload.items() if k in allowed}
    return cleaned, unknown


def sanitize_llm_report(llm_report: dict[str, Any]) -> dict[str, Any]:
    if not llm_report:
        return llm_report
    cleaned: dict[str, Any] = {}
    unknown_top = set(llm_report.keys()) - (LLM_MERGE_FIELDS | {"post_annotations"})
    if unknown_top:
        logger.warning("Hotpost LLM report dropped unknown top fields: %s", sorted(unknown_top))

    for field in LLM_MERGE_FIELDS:
        if field not in llm_report:
            continue
        value = llm_report.get(field)
        if value is None:
            continue
        if field == "topics" and isinstance(value, list):
            items = []
            for item in value:
                if not isinstance(item, dict):
                    continue
                topic, unknown = _filter_model_fields(
                    item, model_cls=HotpostTopic, extra_allow={"evidence_post_ids"}
                )
                if unknown:
                    logger.warning("Hotpost LLM report dropped topic fields: %s", sorted(unknown))
                evidence = topic.get("evidence")
                if isinstance(evidence, list):
                    filtered_evidence = []
                    for ev in evidence:
                        if not isinstance(ev, dict):
                            continue
                        ev_clean, ev_unknown = _filter_model_fields(ev, model_cls=HotpostTopicEvidence)
                        if ev_unknown:
                            logger.warning("Hotpost LLM report dropped topic evidence fields: %s", sorted(ev_unknown))
                        filtered_evidence.append(ev_clean)
                    topic["evidence"] = filtered_evidence
                items.append(topic)
            cleaned[field] = items
            continue

        if field == "pain_points" and isinstance(value, list):
            items = []
            for item in value:
                if not isinstance(item, dict):
                    continue
                point, unknown = _filter_model_fields(
                    item, model_cls=PainPoint, extra_allow={"evidence_post_ids"}
                )
                if unknown:
                    logger.warning("Hotpost LLM report dropped pain_point fields: %s", sorted(unknown))
                items.append(point)
            cleaned[field] = items
            continue

        if field == "unmet_needs" and isinstance(value, list):
            items = []
            for item in value:
                if not isinstance(item, dict):
                    continue
                need, unknown = _filter_model_fields(
                    item, model_cls=UnmetNeed, extra_allow={"evidence_post_ids"}
                )
                if unknown:
                    logger.warning("Hotpost LLM report dropped unmet_need fields: %s", sorted(unknown))
                evidence = need.get("evidence")
                if isinstance(evidence, list):
                    filtered_evidence = []
                    for ev in evidence:
                        if not isinstance(ev, dict):
                            continue
                        ev_clean, ev_unknown = _filter_model_fields(ev, model_cls=UnmetNeedEvidence)
                        if ev_unknown:
                            logger.warning("Hotpost LLM report dropped unmet_need evidence fields: %s", sorted(ev_unknown))
                        filtered_evidence.append(ev_clean)
                    need["evidence"] = filtered_evidence
                items.append(need)
            cleaned[field] = items
            continue

        if field == "competitor_mentions" and isinstance(value, list):
            items = []
            for item in value:
                if not isinstance(item, dict):
                    continue
                comp, unknown = _filter_model_fields(item, model_cls=CompetitorMention)
                if unknown:
                    logger.warning("Hotpost LLM report dropped competitor fields: %s", sorted(unknown))
                items.append(comp)
            cleaned[field] = items
            continue

        if field == "existing_tools" and isinstance(value, list):
            items = []
            for item in value:
                if not isinstance(item, dict):
                    continue
                tool, unknown = _filter_model_fields(item, model_cls=ExistingTool)
                if unknown:
                    logger.warning("Hotpost LLM report dropped existing_tool fields: %s", sorted(unknown))
                items.append(tool)
            cleaned[field] = items
            continue

        if field == "user_segments" and isinstance(value, list):
            items = []
            for item in value:
                if not isinstance(item, dict):
                    continue
                seg, unknown = _filter_model_fields(item, model_cls=UserSegment)
                if unknown:
                    logger.warning("Hotpost LLM report dropped user_segment fields: %s", sorted(unknown))
                items.append(seg)
            cleaned[field] = items
            continue

        if field == "market_opportunity" and isinstance(value, dict):
            market, unknown = _filter_model_fields(value, model_cls=MarketOpportunity)
            if unknown:
                logger.warning("Hotpost LLM report dropped market_opportunity fields: %s", sorted(unknown))
            cleaned[field] = market
            continue

        if field == "migration_intent" and isinstance(value, dict):
            intent, unknown = _filter_model_fields(value, model_cls=MigrationIntent)
            if unknown:
                logger.warning("Hotpost LLM report dropped migration_intent fields: %s", sorted(unknown))
            cleaned[field] = intent
            continue

        if field == "top_quotes" and isinstance(value, list):
            items = []
            for item in value:
                if not isinstance(item, dict):
                    continue
                quote, unknown = _filter_model_fields(item, model_cls=TopQuote)
                if unknown:
                    logger.warning("Hotpost LLM report dropped top_quote fields: %s", sorted(unknown))
                items.append(quote)
            cleaned[field] = items
            continue

        cleaned[field] = value

    annotations = llm_report.get("post_annotations")
    if isinstance(annotations, dict):
        cleaned_annotations: dict[str, dict[str, Any]] = {}
        for post_id, meta in annotations.items():
            if not isinstance(meta, dict):
                continue
            why = meta.get("why_relevant")
            if why:
                cleaned_annotations[str(post_id)] = {"why_relevant": why}
        cleaned["post_annotations"] = cleaned_annotations
    return cleaned


async def generate_hotpost_llm_report(
    *,
    mode: str,
    query: str,
    time_filter: str,
    posts_data: list[dict[str, Any]],
    comments_data: list[dict[str, Any]],
    llm_client: HotpostLLMClient,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any] | None:
    prompt = render_hotpost_prompt(
        mode=mode,
        query=query,
        time_filter=time_filter,
        posts_data=posts_data,
        comments_data=comments_data,
    )
    content = await llm_client.generate(
        prompt,
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=max_tokens,
    )
    parsed = _safe_json_loads(content or "")
    if not parsed:
        return None
    return sanitize_llm_report(parsed)


__all__ = [
    "generate_hotpost_llm_report",
    "render_hotpost_prompt",
    "merge_hotpost_llm_report",
    "apply_hotpost_llm_annotations",
    "HotpostLLMClient",
    "sanitize_llm_report",
]
