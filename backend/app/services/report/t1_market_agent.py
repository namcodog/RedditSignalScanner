from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Mapping

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ReportInputs:
    stats: Any
    clusters: list[Any]
    product_description: str = "跨境电商支付解决方案"


def _to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        result = value.to_dict()
        if isinstance(result, Mapping):
            return dict(result)
    if is_dataclass(value):
        return asdict(value)
    raw = getattr(value, "__dict__", None)
    if isinstance(raw, Mapping):
        return dict(raw)
    return {}


class T1MarketReportAgent:
    """
    市场洞察报告渲染器。

    职责只保留一件事：
    - 吃已经准备好的 stats / pain clusters
    - 输出一份稳定的 markdown

    不再负责取数，不再负责注入 service。
    """

    def __init__(self, inputs: ReportInputs, *, quality_level: str | None = None) -> None:
        self.inputs = inputs
        self.quality_level = (
            str(quality_level or getattr(settings, "report_quality_level", "standard"))
            .strip()
            .lower()
        )
        self.llm_used = False

    def render(
        self,
        product_description: str | None = None,
        quality_level: str | None = None,
    ) -> str:
        stats = _to_dict(self.inputs.stats)
        clusters = [_to_dict(cluster) for cluster in self.inputs.clusters]
        product_name = product_description or self.inputs.product_description
        level = str(quality_level or self.quality_level or "standard").strip().lower()

        community_stats = list(stats.get("community_stats") or [])
        aspect_breakdown = list(stats.get("aspect_breakdown") or [])
        brand_links = list(stats.get("brand_pain_cooccurrence") or [])

        lines: list[str] = [f"# {product_name} 社区市场洞察报告", ""]

        lines.extend(["## 已分析赛道", ""])
        if community_stats:
            for community in community_stats[:5]:
                subreddit = str(community.get("subreddit") or "").strip()
                label = subreddit if subreddit.startswith("r/") else f"r/{subreddit}"
                lines.append(
                    f"- {label}: {community.get('posts', 0)} 帖子 / {community.get('comments', 0)} 评论 / P/S {community.get('ps_ratio', 'N/A')}"
                )
        else:
            lines.append("- 暂无社区概览")

        lines.extend(
            [
                "",
                "## 决策卡片",
                "",
                f"- 覆盖社区数: {len(stats.get('subreddits') or [])}",
                f"- 全局 P/S: {stats.get('global_ps_ratio', 'N/A')}",
                f"- 痛点总量: {stats.get('total_pain', 0)}",
                f"- 方案总量: {stats.get('total_solution', 0)}",
            ]
        )

        lines.extend(["", "## 用户痛点", ""])
        if clusters:
            for index, cluster in enumerate(clusters[:5], start=1):
                lines.append(f"### 痛点 {index}: {cluster.get('topic', '未命名痛点')}")
                keywords = ", ".join(cluster.get("keywords") or [])
                if keywords:
                    lines.append(f"- 关键词: {keywords}")
                samples = cluster.get("samples") or []
                if samples:
                    lines.append(f"- 代表样本: {samples[0]}")
                aspects = ", ".join(cluster.get("aspects") or [])
                if aspects:
                    lines.append(f"- 相关维度: {aspects}")
                lines.append("")
        else:
            lines.extend(["- 暂无痛点聚类", ""])

        if aspect_breakdown:
            lines.extend(["## 主要战场", ""])
            for aspect in aspect_breakdown[:5]:
                lines.append(
                    f"- {aspect.get('aspect', 'other')}: pain={aspect.get('pain', 0)} / total={aspect.get('total', 0)}"
                )
            lines.append("")

        if brand_links:
            lines.extend(["## 品牌共现", ""])
            for item in brand_links[:5]:
                lines.append(f"- {item.get('brand', 'unknown')}: {item.get('mentions', 0)} 次提及")
            lines.append("")

        lines.extend(["## 商业机会", "", "### 商业机会（草案）"])
        if clusters:
            top_topics = " / ".join(
                str(cluster.get("topic") or "")
                for cluster in clusters[:3]
                if cluster.get("topic")
            )
            lines.append(
                f"- 优先围绕 {top_topics} 设计解决方案" if top_topics else "- 优先围绕高频痛点设计解决方案"
            )
        else:
            lines.append("- 先补齐样本，再判断商业机会")

        lines.extend(["", "## LLM 增强", ""])
        llm_block = self._render_llm_enhancement(product_name, clusters, level)
        if llm_block:
            self.llm_used = True
            lines.append(llm_block)
        else:
            self.llm_used = False
            lines.append("未调用 LLM")

        return "\n".join(lines).strip() + "\n"

    async def render_async(
        self,
        product_description: str | None = None,
        quality_level: str | None = None,
    ) -> str:
        return self.render(product_description=product_description, quality_level=quality_level)

    def _render_llm_enhancement(
        self,
        product_name: str,
        clusters: list[dict[str, Any]],
        quality_level: str,
    ) -> str:
        if quality_level != "premium":
            return ""

        try:
            from app.services.llm.clients.openai_client import OpenAIChatClient

            top_topics = ", ".join(
                str(cluster.get("topic") or "")
                for cluster in clusters[:3]
                if cluster.get("topic")
            ) or "暂无痛点"

            client = OpenAIChatClient(
                model=str(getattr(settings, "llm_model_name", "openai/gpt-4o-mini")),
            )
            return client._chat_completion(
                [{"role": "user", "content": f"请用一句话总结 {product_name} 的核心市场机会：{top_topics}"}],
                max_tokens=120,
                temperature=0.2,
            ).strip()
        except Exception as exc:  # pragma: no cover - 兼容老测试 monkeypatch
            logger.warning("market insight LLM enhancement failed: %s", exc)
            return ""
