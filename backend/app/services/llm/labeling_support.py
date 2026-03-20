from __future__ import annotations

import json
from typing import Any, Sequence


POST_SCHEMA = {
    "content_type": "ask_question | user_review | news_sharing | discussion | rant | other",
    "main_intent": "complain | ask_help | share_solution | recommend_product | offtopic",
    "sentiment": "float (-1.0 to 1.0)",
    "pain_tags": ["string"],
    "aspect_tags": ["string"],
    "entities": {"known": ["string"], "new": ["string"]},
    "crossborder_signals": {"mentions_shipping": "bool", "mentions_tax": "bool"},
    "purchase_intent_score": "float (0.0 to 1.0)",
}

COMMENT_SCHEMA = {
    "actor_type": "buyer_ask | buyer_review | seller_operator | expert_sharing | other",
    "main_intent": "complain | ask_help | share_solution | recommend_product | offtopic",
    "sentiment": "float (-1.0 to 1.0)",
    "pain_tags": ["string"],
    "aspect_tags": ["string"],
    "entities": {"known": ["string"], "new": ["string"]},
    "crossborder_signals": {"mentions_shipping": "bool", "mentions_tax": "bool"},
    "purchase_intent_score": "float (0.0 to 1.0)",
}

POST_BATCH_SCHEMA = {
    "id": "int",
    **POST_SCHEMA,
}

COMMENT_BATCH_SCHEMA = {
    "id": "int",
    **COMMENT_SCHEMA,
}

SYSTEM_PROMPT = (
    "You are a strict market-intel classifier. "
    "Output JSON only. Use concise English tags. Do not invent facts."
)


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def safe_json_loads(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def safe_json_loads_any(raw: str) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def extract_batch_items(parsed: Any) -> list[dict[str, Any]]:
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        items = parsed.get("items")
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []


def build_post_prompt(
    *,
    title: str,
    body: str,
    subreddit: str,
    comments: Sequence[str],
    max_body_chars: int,
    max_comment_chars: int,
) -> list[dict[str, str]]:
    body_text = truncate(body, max_body_chars)
    comment_text = "\n".join(
        truncate(comment, max_comment_chars) for comment in comments[:2]
    )
    user = (
        f"Post from r/{subreddit}.\n"
        f"Title: {title}\n"
        f"Body: {body_text}\n"
        f"TopComments: {comment_text}\n\n"
        "Return JSON with this schema:\n"
        f"{json.dumps(POST_SCHEMA, ensure_ascii=True)}"
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def build_post_batch_prompt(
    *,
    items: Sequence[dict[str, Any]],
    max_body_chars: int,
    max_comment_chars: int,
) -> list[dict[str, str]]:
    payload: list[dict[str, Any]] = []
    for item in items:
        payload.append(
            {
                "id": item.get("id"),
                "subreddit": item.get("subreddit"),
                "title": truncate(str(item.get("title") or ""), max_body_chars),
                "body": truncate(str(item.get("body") or ""), max_body_chars),
                "comments": [
                    truncate(str(comment or ""), max_comment_chars)
                    for comment in (item.get("comments") or [])
                ],
            }
        )
    user = (
        "Return JSON array with objects in this schema:\n"
        f"{json.dumps(POST_BATCH_SCHEMA, ensure_ascii=True)}\n\n"
        f"Items:\n{json.dumps(payload, ensure_ascii=True)}"
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def build_comment_prompt(
    *,
    body: str,
    post_title: str,
    subreddit: str,
    max_body_chars: int,
) -> list[dict[str, str]]:
    body_text = truncate(body, max_body_chars)
    user = (
        f"Comment from r/{subreddit}.\n"
        f"PostTitle: {post_title}\n"
        f"Comment: {body_text}\n\n"
        "Return JSON with this schema:\n"
        f"{json.dumps(COMMENT_SCHEMA, ensure_ascii=True)}"
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


def build_comment_batch_prompt(
    *,
    items: Sequence[dict[str, Any]],
    max_body_chars: int,
) -> list[dict[str, str]]:
    payload: list[dict[str, Any]] = []
    for item in items:
        payload.append(
            {
                "id": item.get("id"),
                "subreddit": item.get("subreddit"),
                "post_title": truncate(str(item.get("post_title") or ""), max_body_chars),
                "comment": truncate(str(item.get("body") or ""), max_body_chars),
            }
        )
    user = (
        "Return JSON array with objects in this schema:\n"
        f"{json.dumps(COMMENT_BATCH_SCHEMA, ensure_ascii=True)}\n\n"
        f"Items:\n{json.dumps(payload, ensure_ascii=True)}"
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]


__all__ = [
    "COMMENT_BATCH_SCHEMA",
    "COMMENT_SCHEMA",
    "POST_BATCH_SCHEMA",
    "POST_SCHEMA",
    "build_comment_batch_prompt",
    "build_comment_prompt",
    "build_post_batch_prompt",
    "build_post_prompt",
    "extract_batch_items",
    "safe_json_loads",
    "safe_json_loads_any",
    "truncate",
]
