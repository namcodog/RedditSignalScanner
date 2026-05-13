from __future__ import annotations

import logging
from typing import Any, Sequence

from app.services.llm.clients.gemini_client import GeminiChatClient
from app.services.llm.label_contract import LLMScoreResult
from app.services.llm.labeling_runtime import (
    run_label_comment,
    run_label_comments_batch,
    run_label_post,
    run_label_posts_batch,
)
from app.services.llm.labeling_support import (
    COMMENT_BATCH_SCHEMA,
    COMMENT_SCHEMA,
    POST_BATCH_SCHEMA,
    POST_SCHEMA,
    build_comment_batch_prompt,
    build_comment_prompt,
    build_post_batch_prompt,
    build_post_prompt,
    extract_batch_items,
    safe_json_loads,
    safe_json_loads_any,
    truncate,
)

logger = logging.getLogger(__name__)


# Keep the old module-level names alive so current imports and patches don't drift.
_POST_SCHEMA = POST_SCHEMA
_COMMENT_SCHEMA = COMMENT_SCHEMA
_POST_BATCH_SCHEMA = POST_BATCH_SCHEMA
_COMMENT_BATCH_SCHEMA = COMMENT_BATCH_SCHEMA


def _truncate(text: str, limit: int) -> str:
    return truncate(text, limit)


def _safe_json_loads(raw: str) -> dict[str, Any]:
    return safe_json_loads(raw)


def _safe_json_loads_any(raw: str) -> Any:
    return safe_json_loads_any(raw)


def _extract_batch_items(parsed: Any) -> list[dict[str, Any]]:
    return extract_batch_items(parsed)


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
        return build_post_prompt(
            title=title,
            body=body,
            subreddit=subreddit,
            comments=comments,
            max_body_chars=self._max_body_chars,
            max_comment_chars=self._max_comment_chars,
        )

    def _build_post_batch_prompt(
        self,
        *,
        items: Sequence[dict[str, Any]],
    ) -> list[dict[str, str]]:
        return build_post_batch_prompt(
            items=items,
            max_body_chars=self._max_body_chars,
            max_comment_chars=self._max_comment_chars,
        )

    def _build_comment_prompt(
        self,
        *,
        body: str,
        post_title: str,
        subreddit: str,
    ) -> list[dict[str, str]]:
        return build_comment_prompt(
            body=body,
            post_title=post_title,
            subreddit=subreddit,
            max_body_chars=self._max_body_chars,
        )

    def _build_comment_batch_prompt(
        self,
        *,
        items: Sequence[dict[str, Any]],
    ) -> list[dict[str, str]]:
        return build_comment_batch_prompt(
            items=items,
            max_body_chars=self._max_body_chars,
        )

    async def label_post(
        self,
        *,
        title: str,
        body: str,
        subreddit: str,
        comments: Sequence[str],
    ) -> tuple[dict[str, Any], LLMScoreResult, int, int]:
        return await run_label_post(
            client=self._client,
            title=title,
            body=body,
            subreddit=subreddit,
            comments=comments,
            max_body_chars=self._max_body_chars,
            max_comment_chars=self._max_comment_chars,
        )

    async def label_posts_batch(
        self,
        *,
        items: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return await run_label_posts_batch(
            client=self._client,
            items=items,
            max_body_chars=self._max_body_chars,
            max_comment_chars=self._max_comment_chars,
            model_name=self._model,
            prompt_version=self._prompt_version,
            logger=logger,
        )

    async def label_comment(
        self,
        *,
        body: str,
        post_title: str,
        subreddit: str,
    ) -> tuple[dict[str, Any], LLMScoreResult, int, int]:
        return await run_label_comment(
            client=self._client,
            body=body,
            post_title=post_title,
            subreddit=subreddit,
            max_body_chars=self._max_body_chars,
        )

    async def label_comments_batch(
        self,
        *,
        items: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return await run_label_comments_batch(
            client=self._client,
            items=items,
            max_body_chars=self._max_body_chars,
            model_name=self._model,
            prompt_version=self._prompt_version,
            logger=logger,
        )


__all__ = ["LLMLabeler", "LLMScoreResult"]
