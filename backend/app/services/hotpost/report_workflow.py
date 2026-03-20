from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable

from app.schemas.hotpost import Hotpost, HotpostComment
from app.services.hotpost.report_llm import generate_hotpost_llm_report
from app.services.hotpost.result_meta import HotpostLLMReportResult
from app.services.llm.clients.openai_client import OpenAIChatClient, resolve_llm_api_key


@dataclass(slots=True)
class HotpostReportWorkflowInput:
    mode: str
    query: str
    time_filter: str
    top_posts: list[Hotpost]
    all_comments: list[HotpostComment]
    llm_model_name: str


@dataclass(slots=True)
class HotpostReportWorkflowDeps:
    resolve_api_key: Callable[[], str | None] = resolve_llm_api_key
    client_factory: Callable[[str], Any] = lambda model_name: OpenAIChatClient(model=model_name)
    generate_report: Callable[..., Any] = generate_hotpost_llm_report
    getenv: Callable[[str, str], str] = os.getenv


def _env_flag(getenv: Callable[[str, str], str], key: str, default: str = "true") -> bool:
    return getenv(key, default).strip().lower() in {"1", "true", "yes"}


async def build_hotpost_report_result(
    *,
    workflow_input: HotpostReportWorkflowInput,
    deps: HotpostReportWorkflowDeps,
) -> HotpostLLMReportResult:
    evidence_count = len(workflow_input.top_posts)
    enable_llm_report = _env_flag(deps.getenv, "ENABLE_HOTPOST_LLM_REPORT", "true")
    api_key = deps.resolve_api_key()

    if not enable_llm_report:
        return HotpostLLMReportResult(
            report=None,
            source="disabled",
            degraded_reason="report_llm_disabled",
        )
    if not api_key:
        return HotpostLLMReportResult(
            report=None,
            source="disabled",
            degraded_reason="missing_api_key",
        )
    if evidence_count <= 0:
        return HotpostLLMReportResult(
            report=None,
            source="disabled",
            degraded_reason="no_evidence",
        )

    max_tokens = int(
        deps.getenv(
            "HOTPOST_LLM_MAX_TOKENS",
            deps.getenv("OPENROUTER_MAX_TOKENS", "4096"),
        )
    )
    temperature = float(
        deps.getenv(
            "HOTPOST_LLM_TEMPERATURE",
            deps.getenv("OPENROUTER_TEMPERATURE", "0.3"),
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
        for post in workflow_input.top_posts
    ]
    comments_payload = [
        {
            "body": comment.body,
            "score": comment.score,
            "author": comment.author,
            "permalink": comment.permalink,
        }
        for comment in workflow_input.all_comments
    ]
    return await deps.generate_report(
        mode=workflow_input.mode,
        query=workflow_input.query,
        time_filter=workflow_input.time_filter,
        posts_data=posts_payload,
        comments_data=comments_payload,
        llm_client=deps.client_factory(workflow_input.llm_model_name),
        max_tokens=max_tokens,
        temperature=temperature,
    )


__all__ = [
    "HotpostReportWorkflowDeps",
    "HotpostReportWorkflowInput",
    "build_hotpost_report_result",
]
