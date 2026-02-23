from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.services.llm.clients.gemini_client import GeminiChatClient


_POST_SCHEMA = {
    "content_type": "ask_question | user_review | news_sharing | discussion | rant | other",
    "main_intent": "complain | ask_help | share_solution | recommend_product | offtopic",
    "sentiment": "float (-1.0 to 1.0)",
    "pain_tags": ["string"],
    "aspect_tags": ["string"],
    "entities": {"known": ["string"], "new": ["string"]},
    "crossborder_signals": {"mentions_shipping": "bool", "mentions_tax": "bool"},
    "purchase_intent_score": "float (0.0 to 1.0)",
}

_COMMENT_SCHEMA = {
    "actor_type": "buyer_ask | buyer_review | seller_operator | expert_sharing | other",
    "main_intent": "complain | ask_help | share_solution | recommend_product | offtopic",
    "sentiment": "float (-1.0 to 1.0)",
    "pain_tags": ["string"],
    "aspect_tags": ["string"],
    "entities": {"known": ["string"], "new": ["string"]},
    "crossborder_signals": {"mentions_shipping": "bool", "mentions_tax": "bool"},
    "purchase_intent_score": "float (0.0 to 1.0)",
}

_POST_BATCH_SCHEMA = {
    "id": "int",
    **_POST_SCHEMA,
}

_COMMENT_BATCH_SCHEMA = {
    "id": "int",
    **_COMMENT_SCHEMA,
}


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def _safe_json_loads(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _safe_json_loads_any(raw: str) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _extract_batch_items(parsed: Any) -> list[dict[str, Any]]:
    if isinstance(parsed, list):
        return [p for p in parsed if isinstance(p, dict)]
    if isinstance(parsed, dict):
        items = parsed.get("items")
        if isinstance(items, list):
            return [p for p in items if isinstance(p, dict)]
    return []


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _normalize_post_analysis(data: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "content_type": str(data.get("content_type") or "other").strip().lower(),
        "main_intent": str(data.get("main_intent") or "offtopic").strip().lower(),
        "sentiment": float(data.get("sentiment") or 0.0),
        "pain_tags": _coerce_list(data.get("pain_tags")),
        "aspect_tags": _coerce_list(data.get("aspect_tags")),
        "entities": {
            "known": _coerce_list((data.get("entities") or {}).get("known")),
            "new": _coerce_list((data.get("entities") or {}).get("new")),
        },
        "crossborder_signals": {
            "mentions_shipping": _coerce_bool(
                (data.get("crossborder_signals") or {}).get("mentions_shipping")
            ),
            "mentions_tax": _coerce_bool(
                (data.get("crossborder_signals") or {}).get("mentions_tax")
            ),
        },
        "purchase_intent_score": float(data.get("purchase_intent_score") or 0.0),
    }


def _normalize_comment_analysis(data: Mapping[str, Any]) -> dict[str, Any]:
    base = _normalize_post_analysis(data)
    base["actor_type"] = str(data.get("actor_type") or "other").strip().lower()
    return base


@dataclass(frozen=True)
class LLMScoreResult:
    value_score: float
    opportunity_score: float
    business_pool: str


def _score_post(analysis: Mapping[str, Any]) -> LLMScoreResult:
    base_score = 3.0

    ctype = analysis.get("content_type", "other")
    if ctype == "user_review":
        base_score += 3.0
    elif ctype == "ask_question":
        base_score += 1.0
    elif ctype == "news_sharing":
        base_score += 1.0
    elif ctype == "rant":
        base_score += 2.0

    intent = analysis.get("main_intent", "offtopic")
    if intent == "share_solution":
        base_score += 2.0
    elif intent == "complain":
        base_score += 2.0
    elif intent == "recommend_product":
        base_score += 1.0

    pains = analysis.get("pain_tags") or []
    base_score += min(len(pains) * 1.5, 4.5)

    cb = analysis.get("crossborder_signals") or {}
    if cb.get("mentions_shipping"):
        base_score += 1.0
    if cb.get("mentions_tax"):
        base_score += 1.0

    pi_score = float(analysis.get("purchase_intent_score") or 0.0)
    if pi_score > 0.7:
        base_score *= 1.2

    final_value = max(0.0, min(10.0, base_score))
    opp_score = (len(pains) * 0.25) + (pi_score * 0.5)
    if intent == "complain":
        opp_score += 0.2
    final_opp = max(0.0, min(1.0, opp_score))

    pool = "lab"
    if final_value >= 8.0:
        pool = "core"
    elif final_value <= 3.9:
        pool = "noise"

    return LLMScoreResult(value_score=round(final_value, 2), opportunity_score=round(final_opp, 2), business_pool=pool)


def _score_comment(analysis: Mapping[str, Any]) -> LLMScoreResult:
    base_score = 3.0

    actor = analysis.get("actor_type", "other")
    if actor == "buyer_review":
        base_score += 2.0
    elif actor == "buyer_ask":
        base_score += 1.0
    elif actor == "seller_operator":
        base_score -= 1.0
    elif actor == "expert_sharing":
        base_score += 2.0

    intent = analysis.get("main_intent", "offtopic")
    if intent == "share_solution":
        base_score += 3.0
    elif intent == "complain":
        base_score += 2.0
    elif intent == "recommend_product":
        base_score += 1.0
    elif intent == "offtopic":
        base_score -= 2.0

    pains = analysis.get("pain_tags") or []
    base_score += min(len(pains) * 1.0, 3.0)

    cb = analysis.get("crossborder_signals") or {}
    if cb.get("mentions_shipping"):
        base_score += 1.0
    if cb.get("mentions_tax"):
        base_score += 1.0

    pi_score = float(analysis.get("purchase_intent_score") or 0.0)
    if pi_score > 0.7:
        base_score *= 1.2

    final_value = max(0.0, min(10.0, base_score))
    opp_score = (len(pains) * 0.2) + (pi_score * 0.5)
    if intent == "complain":
        opp_score += 0.2
    final_opp = max(0.0, min(1.0, opp_score))

    pool = "lab"
    if final_value >= 8.0:
        pool = "core"
    elif final_value <= 3.9:
        pool = "noise"

    return LLMScoreResult(value_score=round(final_value, 2), opportunity_score=round(final_opp, 2), business_pool=pool)


class LLMLabeler:
    def __init__(
        self,
        *,
        model: str,
        prompt_version: str,
        max_body_chars: int,
        max_comment_chars: int,
        timeout: float = 25.0,
        api_key: str | None = None,
    ) -> None:
        self._model = model
        self._prompt_version = prompt_version
        self._max_body_chars = max_body_chars
        self._max_comment_chars = max_comment_chars
        self._client = GeminiChatClient(model, timeout=timeout, api_key=api_key)

    @property
    def prompt_version(self) -> str:
        return self._prompt_version

    @property
    def model_name(self) -> str:
        return self._model

    def _build_post_prompt(
        self,
        *,
        title: str,
        body: str,
        subreddit: str,
        comments: Sequence[str],
    ) -> list[dict[str, str]]:
        system = (
            "You are a strict market-intel classifier. "
            "Output JSON only. Use concise English tags. Do not invent facts."
        )
        body_text = _truncate(body, self._max_body_chars)
        comment_text = "\n".join(_truncate(c, self._max_comment_chars) for c in comments[:2])
        user = (
            f"Post from r/{subreddit}.\n"
            f"Title: {title}\n"
            f"Body: {body_text}\n"
            f"TopComments: {comment_text}\n\n"
            "Return JSON with this schema:\n"
            f"{json.dumps(_POST_SCHEMA, ensure_ascii=True)}"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _build_post_batch_prompt(
        self,
        *,
        items: Sequence[dict[str, Any]],
    ) -> list[dict[str, str]]:
        system = (
            "You are a strict market-intel classifier. "
            "Output JSON only. Use concise English tags. Do not invent facts."
        )
        payload: list[dict[str, Any]] = []
        for item in items:
            payload.append(
                {
                    "id": item.get("id"),
                    "subreddit": item.get("subreddit"),
                    "title": _truncate(str(item.get("title") or ""), self._max_body_chars),
                    "body": _truncate(str(item.get("body") or ""), self._max_body_chars),
                    "comments": [
                        _truncate(str(c or ""), self._max_comment_chars)
                        for c in (item.get("comments") or [])
                    ],
                }
            )
        user = (
            "Return JSON array with objects in this schema:\n"
            f"{json.dumps(_POST_BATCH_SCHEMA, ensure_ascii=True)}\n\n"
            f"Items:\n{json.dumps(payload, ensure_ascii=True)}"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _build_comment_prompt(
        self,
        *,
        body: str,
        post_title: str,
        subreddit: str,
    ) -> list[dict[str, str]]:
        system = (
            "You are a strict market-intel classifier. "
            "Output JSON only. Use concise English tags. Do not invent facts."
        )
        body_text = _truncate(body, self._max_body_chars)
        user = (
            f"Comment from r/{subreddit}.\n"
            f"PostTitle: {post_title}\n"
            f"Comment: {body_text}\n\n"
            "Return JSON with this schema:\n"
            f"{json.dumps(_COMMENT_SCHEMA, ensure_ascii=True)}"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def _build_comment_batch_prompt(
        self,
        *,
        items: Sequence[dict[str, Any]],
    ) -> list[dict[str, str]]:
        system = (
            "You are a strict market-intel classifier. "
            "Output JSON only. Use concise English tags. Do not invent facts."
        )
        payload: list[dict[str, Any]] = []
        for item in items:
            payload.append(
                {
                    "id": item.get("id"),
                    "subreddit": item.get("subreddit"),
                    "post_title": _truncate(
                        str(item.get("post_title") or ""), self._max_body_chars
                    ),
                    "comment": _truncate(
                        str(item.get("body") or ""), self._max_body_chars
                    ),
                }
            )
        user = (
            "Return JSON array with objects in this schema:\n"
            f"{json.dumps(_COMMENT_BATCH_SCHEMA, ensure_ascii=True)}\n\n"
            f"Items:\n{json.dumps(payload, ensure_ascii=True)}"
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    async def label_post(
        self,
        *,
        title: str,
        body: str,
        subreddit: str,
        comments: Sequence[str],
    ) -> tuple[dict[str, Any], LLMScoreResult, int, int]:
        prompt = self._build_post_prompt(
            title=title,
            body=body,
            subreddit=subreddit,
            comments=comments,
        )
        raw = await self._client.generate(
            prompt,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=512,
        )
        parsed = _safe_json_loads(raw)
        analysis = _normalize_post_analysis(parsed)
        score = _score_post(analysis)
        input_chars = sum(len(m.get("content") or "") for m in prompt)
        output_chars = len(raw or "")
        return analysis, score, input_chars, output_chars

    async def label_posts_batch(
        self,
        *,
        items: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not items:
            return []
        prompt = self._build_post_batch_prompt(items=items)
        raw = await self._client.generate(
            prompt,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1024,
        )
        parsed = _safe_json_loads_any(raw)
        batch_items = _extract_batch_items(parsed)
        if not batch_items:
            return []

        input_chars = sum(len(m.get("content") or "") for m in prompt)
        output_chars = len(raw or "")
        divisor = max(1, len(batch_items))
        per_input = max(1, input_chars // divisor)
        per_output = max(1, output_chars // divisor)

        results: list[dict[str, Any]] = []
        for item in batch_items:
            item_id = item.get("id")
            if item_id is None:
                continue
            analysis = _normalize_post_analysis(item)
            score = _score_post(analysis)
            results.append(
                {
                    "id": int(item_id),
                    "analysis": analysis,
                    "score": score,
                    "input_chars": per_input,
                    "output_chars": per_output,
                }
            )
        return results

    async def label_comment(
        self,
        *,
        body: str,
        post_title: str,
        subreddit: str,
    ) -> tuple[dict[str, Any], LLMScoreResult, int, int]:
        prompt = self._build_comment_prompt(
            body=body,
            post_title=post_title,
            subreddit=subreddit,
        )
        raw = await self._client.generate(
            prompt,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=512,
        )
        parsed = _safe_json_loads(raw)
        analysis = _normalize_comment_analysis(parsed)
        score = _score_comment(analysis)
        input_chars = sum(len(m.get("content") or "") for m in prompt)
        output_chars = len(raw or "")
        return analysis, score, input_chars, output_chars

    async def label_comments_batch(
        self,
        *,
        items: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not items:
            return []
        prompt = self._build_comment_batch_prompt(items=items)
        raw = await self._client.generate(
            prompt,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1024,
        )
        parsed = _safe_json_loads_any(raw)
        batch_items = _extract_batch_items(parsed)
        if not batch_items:
            return []

        input_chars = sum(len(m.get("content") or "") for m in prompt)
        output_chars = len(raw or "")
        divisor = max(1, len(batch_items))
        per_input = max(1, input_chars // divisor)
        per_output = max(1, output_chars // divisor)

        results: list[dict[str, Any]] = []
        for item in batch_items:
            item_id = item.get("id")
            if item_id is None:
                continue
            analysis = _normalize_comment_analysis(item)
            score = _score_comment(analysis)
            results.append(
                {
                    "id": int(item_id),
                    "analysis": analysis,
                    "score": score,
                    "input_chars": per_input,
                    "output_chars": per_output,
                }
            )
        return results


__all__ = ["LLMLabeler", "LLMScoreResult"]
