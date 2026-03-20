from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from app.schemas.hotpost import Hotpost
from app.services.hotpost.result_meta import HotpostSummaryResult


class HotpostSummaryClient(Protocol):
    async def generate(
        self,
        prompt: str,
        *,
        temperature: float,
        max_tokens: int,
    ) -> str:
        ...


@dataclass(slots=True)
class HotpostSummaryWorkflowInput:
    query: str
    posts: list[Hotpost]
    confidence: str
    sentiment_overview: dict[str, float] | None = None
    community_distribution: dict[str, str] | None = None


@dataclass(slots=True)
class HotpostSummaryWorkflowDeps:
    resolve_api_key: Callable[[], str]
    client_factory: Callable[[], HotpostSummaryClient]


def build_hotpost_fallback_summary(
    posts: list[Hotpost],
    *,
    sentiment_overview: dict[str, float] | None = None,
    community_distribution: dict[str, str] | None = None,
) -> str:
    if not posts:
        return "暂无相关讨论，样本不足。"
    communities = {p.subreddit for p in posts if p.subreddit}
    signal_counts: dict[str, int] = {}
    for post in posts:
        for signal in post.signals:
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
    parts = [f"找到 {len(posts)} 条相关讨论，来自 {len(communities)} 个社区。"]
    if community_distribution:
        top_communities = list(community_distribution.items())[:3]
        community_text = "、".join(f"{name}({pct})" for name, pct in top_communities)
        if community_text:
            parts.append(f"主要社区：{community_text}。")
    if signal_counts:
        top_signals = [name for name, _ in sorted(signal_counts.items(), key=lambda item: item[1], reverse=True)[:3]]
        parts.append(f"高频信号词：{'、'.join(top_signals)}。")
    if sentiment_overview:
        parts.append(
            "情绪分布："
            f"负向{sentiment_overview.get('negative', 0):.0%} / "
            f"中性{sentiment_overview.get('neutral', 0):.0%} / "
            f"正向{sentiment_overview.get('positive', 0):.0%}。"
        )
    return "".join(parts)


async def generate_hotpost_summary(
    *,
    workflow_input: HotpostSummaryWorkflowInput,
    deps: HotpostSummaryWorkflowDeps,
) -> HotpostSummaryResult:
    if workflow_input.confidence in {"none", "low"}:
        return HotpostSummaryResult(
            text=build_hotpost_fallback_summary(
                workflow_input.posts,
                sentiment_overview=workflow_input.sentiment_overview,
                community_distribution=workflow_input.community_distribution,
            ),
            source="fallback",
            degraded_reason="low_confidence",
        )

    api_key = deps.resolve_api_key()
    if not api_key:
        return HotpostSummaryResult(
            text=build_hotpost_fallback_summary(
                workflow_input.posts,
                sentiment_overview=workflow_input.sentiment_overview,
                community_distribution=workflow_input.community_distribution,
            ),
            source="fallback",
            degraded_reason="missing_api_key",
        )

    client = deps.client_factory()
    titles = "\n".join(f"- {post.title}" for post in workflow_input.posts[:10])
    prompt = (
        "请根据以下 Reddit 帖子标题，给出一句话洞察（不超过40字），"
        "只基于标题内容，不要编造：\n" + titles
    )
    try:
        content = await client.generate(prompt, temperature=0.3, max_tokens=120)
    except Exception:
        return HotpostSummaryResult(
            text=build_hotpost_fallback_summary(
                workflow_input.posts,
                sentiment_overview=workflow_input.sentiment_overview,
                community_distribution=workflow_input.community_distribution,
            ),
            source="fallback",
            degraded_reason="llm_generate_failed",
        )
    summary = (content or "").strip()
    if summary:
        return HotpostSummaryResult(text=summary, source="llm")
    return HotpostSummaryResult(
        text=build_hotpost_fallback_summary(
            workflow_input.posts,
            sentiment_overview=workflow_input.sentiment_overview,
            community_distribution=workflow_input.community_distribution,
        ),
        source="fallback",
        degraded_reason="llm_empty_output",
    )


__all__ = [
    "HotpostSummaryWorkflowDeps",
    "HotpostSummaryWorkflowInput",
    "build_hotpost_fallback_summary",
    "generate_hotpost_summary",
]
