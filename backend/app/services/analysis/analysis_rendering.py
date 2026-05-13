from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Mapping, Protocol, Sequence

from app.core.config import Settings
from app.schemas.task import TaskSummary
from app.services.analysis.insights_enrichment import derive_driver_label
from app.services.llm.clients.openai_client import OpenAIChatClient
from app.services.llm.report_prompts import (
    build_complete_report_v9,
    build_report_structured_prompt_v9,
    format_facts_for_prompt,
)
from app.services.report.structured_report_fallback import (
    build_structured_report_fallback,
)

logger = logging.getLogger(__name__)

DEFAULT_LOOKBACK_DAYS = 365


class _CommunityProfileLike(Protocol):
    name: str
    categories: Sequence[str]


class _CollectedCommunityLike(Protocol):
    profile: _CommunityProfileLike
    posts: Sequence[Mapping[str, Any]]


@dataclass(frozen=True)
class StructuredReportRenderResult:
    report: dict[str, Any] | None
    status: str
    reason: str | None
    model: str | None
    rounds: int


@dataclass(frozen=True)
class AnalysisReportRenderBundle:
    report_html: str
    structured_render: StructuredReportRenderResult


def _structured_llm_skipped(reason: str) -> StructuredReportRenderResult:
    return StructuredReportRenderResult(
        report=None,
        status="skipped",
        reason=reason,
        model=None,
        rounds=0,
    )


def format_collection_warning_lines(sources: Mapping[str, Any]) -> list[str]:
    warnings = sources.get("collection_warnings") or []
    if not isinstance(warnings, list):
        return []
    lines: list[str] = []
    stale_cache = sources.get("stale_cache_subreddits") or []
    stale_fallback = sources.get("stale_cache_fallback_subreddits") or []
    if "stale_cache_detected" in warnings:
        lines.append(f"- 发现 {len(stale_cache)} 个社区缓存过期，时效性下降。")
    if "stale_cache_fallback" in warnings:
        lines.append(f"- 有 {len(stale_fallback)} 个社区使用旧缓存兜底（API/限流失败）。")
    if "reddit_rate_limited" in warnings:
        lines.append("- Reddit API 触发限流，部分社区未能实时拉取。")
    if "reddit_api_error" in warnings:
        lines.append("- Reddit API 请求失败，部分社区未能实时拉取。")
    return lines


def render_report(
    task_summary: TaskSummary,
    communities: Sequence[_CollectedCommunityLike],
    insights: Mapping[str, Any],
    sources: Mapping[str, Any],
) -> str:
    community_names = [entry.profile.name for entry in communities]
    pain_counts = {}
    try:
        pain_counts = sources.get("pain_counts_by_community", {}) or {}
    except Exception:
        pain_counts = {}
    top_communities = sorted(
        communities,
        key=lambda c: (
            pain_counts.get(c.profile.name, 0),
            len(c.posts),
        ),
        reverse=True,
    )[:4]
    pain_points: list[dict[str, Any]] = list(insights.get("pain_points", []) or [])
    opportunities: list[dict[str, Any]] = list(insights.get("opportunities", []) or [])
    competitors: list[dict[str, Any]] = list(insights.get("competitors", []) or [])
    action_items: list[dict[str, Any]] = list(insights.get("action_items", []) or [])
    posts_analyzed = int(sources.get("posts_analyzed", 0) or 0)
    cache_hit_rate = float(sources.get("cache_hit_rate", 0.0) or 0.0)
    lookback_days = int(sources.get("lookback_days") or DEFAULT_LOOKBACK_DAYS)
    warning_lines = format_collection_warning_lines(sources)
    warning_block = ""
    if warning_lines:
        warning_block = "\n## 数据提醒\n" + "\n".join(warning_lines)

    ps_ratio_value = sources.get("ps_ratio")
    ps_ratio = (
        f"{ps_ratio_value:.2f}"
        if isinstance(ps_ratio_value, (int, float))
        else f"{len(pain_points)}:{max(len(action_items), len(opportunities), 1)}"
    )

    def _fmt_pain(p: Mapping[str, Any]) -> str:
        desc = str(p.get("description", "")).strip() or "未提取"
        freq = p.get("frequency") or p.get("mentions") or 1
        return f"- {desc}（频次 {freq}）"

    def _fmt_opp(o: Mapping[str, Any]) -> str:
        desc = str(o.get("description", "")).strip() or "未提取"
        rel = o.get("relevance_score", 0)
        rel_str = f"{rel:.0%}" if isinstance(rel, (float, int)) else str(rel)
        audience = o.get("potential_users_est") or o.get("potential_users") or ""
        return f"- {desc}（相关度 {rel_str}，潜在用户 {audience}）"

    def _fmt_comp(c: Mapping[str, Any]) -> str:
        name = c.get("name") or "未知"
        mentions = c.get("mentions", 0)
        sentiment = c.get("sentiment", "mixed")
        return f"- {name}：提及 {mentions} 次，情感 {sentiment}"

    top_pains = "\n".join(_fmt_pain(p) for p in pain_points[:3]) or "- 未识别到核心痛点"
    top_opps = "\n".join(_fmt_opp(o) for o in opportunities[:3]) or "- 未识别到机会"
    top_comps = "\n".join(_fmt_comp(c) for c in competitors[:5]) or "- 未识别到竞品/品牌"

    top_drivers_list: list[str] = []
    for pain in pain_points[:5]:
        driver = derive_driver_label(str(pain.get("description", "")))
        item = f"- {driver} ← 来源痛点：{pain.get('description', '')}"
        if item not in top_drivers_list:
            top_drivers_list.append(item)
    top_drivers = "\n".join(top_drivers_list) or "- 暂无驱动力结论"

    quotes: list[str] = []
    for pain in pain_points:
        for quote in pain.get("user_examples", []) or []:
            if quote not in quotes:
                quotes.append(quote)
            if len(quotes) >= 5:
                break
        if len(quotes) >= 5:
            break
    quotes_block = "\n".join(f"- {quote}" for quote in quotes[:5]) or "- 暂无用户原声"

    def _format_opportunity_card(opportunity: Mapping[str, Any]) -> str:
        desc = str(opportunity.get("description", "")).strip() or "未提取"
        users = (
            opportunity.get("potential_users")
            or opportunity.get("potential_users_est")
            or "N/A"
        )
        rel = opportunity.get("relevance_score", 0)
        rel_str = f"{rel:.0%}" if isinstance(rel, (float, int)) else str(rel)
        linked = opportunity.get("linked_pain_cluster") or "通用痛点"
        channels = opportunity.get("top_channels") or []
        channel_str = ", ".join(channels) if channels else "多渠道"
        return (
            f"- {desc}\n"
            f"  - 目标社群：{', '.join(community_names[:3]) or '核心社区'}\n"
            f"  - 产品定位：解决 {linked}，强调 {rel_str} 相关度\n"
            f"  - 核心卖点：{', '.join(opportunity.get('key_insights', [])[:3]) or '效率/稳定/合规'}\n"
            f"  - 潜在用户：{users}；渠道：{channel_str}"
        )

    opportunity_cards = "\n".join(
        _format_opportunity_card(opportunity) for opportunity in opportunities[:3]
    ) or "- 暂无机会卡"

    battlefield_blocks: list[str] = []
    for community in top_communities:
        name = community.profile.name
        description = ", ".join(community.profile.categories) if community.profile.categories else "相关社区"
        pains = ", ".join(
            [
                str(pain.get("description", ""))
                for pain in pain_points[:2]
                if pain.get("description")
            ]
        ) or "关注用户运营/转化等常见问题"
        strategy = "提供可视化、自动化和本地化能力，验证 ROI"
        battlefield_blocks.append(
            dedent(
                f"""
                - **{name}**
                  - 画像：{description}
                  - 常见痛点：{pains}
                  - 痛点热度：{pain_counts.get(name, 0)}
                  - 策略建议：{strategy}
                """
            ).strip()
        )

    battlefields = "\n".join(battlefield_blocks) or "- 暂无战场数据"

    return dedent(
        f"""
        [Reddit Signal Scanner] 市场洞察报告

        ## 已分析赛道
        - 赛道：{task_summary.product_description.strip()}
        - 关键词：{", ".join(sources.get("keywords", []) or [])}
        - 数据范围：
          - 社区：{len(communities)} 个
          - 帖子：{posts_analyzed} 条（缓存命中率 {cache_hit_rate:.0%}）
          - 时间窗口：近 {lookback_days} 天，围绕上述关键词采样
        - 覆盖社区：{", ".join(community_names[:12])}

        ## 决策卡片
        1) 需求趋势：基于 {posts_analyzed} 条帖子，热度仍在（社区覆盖 {len(community_names)} 个）。
        2) 问题/解决方案比（P/S）：约 {ps_ratio}，痛点略高，需继续挖掘方案位。
        3) 核心战场：{", ".join(community_names[:4]) or "待补充"}。
        4) 明确机会点：{"; ".join([str(opportunity.get("description", "")) for opportunity in opportunities[:3]]) or "待补充"}。

        ## 概览
        - 竞争与品牌：\n{top_comps}
        - 痛点/解决方案比：{ps_ratio}（痛点 {len(pain_points)}，机会 {max(len(action_items), len(opportunities))}）

        ## 核心战场推荐
        {battlefields}

        ## 用户痛点（Top 3）
        {top_pains}

        ## Top 购买驱动力
        {top_drivers}

        ## 潜在机会（Top 3）
        {top_opps}

        ## 机会卡（结构化）
        {opportunity_cards}

        ## 用户之声（Quotes）
        {quotes_block}

        ## 数据与技术摘要
        - 帖子总数：{posts_analyzed}
        - 覆盖社区：{len(community_names)}
        - 新发现社区：{max(0, len(community_names) - len(set(community_names)))}（按名称去重估算）
        - 缓存命中率：{cache_hit_rate:.0%}
        {warning_block}
        """
    ).strip()


def render_scouting_report(
    task_summary: TaskSummary,
    communities: Sequence[_CollectedCommunityLike],
    sources: Mapping[str, Any],
) -> str:
    community_names = [entry.profile.name for entry in communities]
    posts_analyzed = int(sources.get("posts_analyzed", 0) or 0)
    comments_analyzed = int(sources.get("comments_analyzed", 0) or 0)
    comments_status = str(sources.get("comments_pipeline_status") or "").strip() or "unknown"
    cache_hit_rate = float(sources.get("cache_hit_rate", 0.0) or 0.0)
    warning_lines = format_collection_warning_lines(sources)
    warning_block = ""
    if warning_lines:
        warning_block = "\n## 数据提醒\n" + "\n".join(warning_lines)
    keywords = sources.get("keywords", []) or []

    ps_ratio_value = sources.get("ps_ratio")
    ps_ratio = (
        f"{ps_ratio_value:.2f}"
        if isinstance(ps_ratio_value, (int, float))
        else "N/A"
    )

    communities_detail = sources.get("communities_detail") or []
    top_communities: list[dict[str, Any]] = []
    if isinstance(communities_detail, list):
        try:
            candidates = [
                row
                for row in communities_detail
                if isinstance(row, dict) and row.get("name")
            ]
            candidates.sort(key=lambda row: int(row.get("mentions") or 0), reverse=True)
            top_communities = candidates[:4]
        except Exception:
            top_communities = []

    if not top_communities:
        top_communities = [{"name": name} for name in community_names[:4] if name]

    battlefield_lines: list[str] = []
    for row in top_communities:
        name = str(row.get("name") or "").strip() or "unknown"
        categories = row.get("categories") or []
        label = ", ".join([str(item) for item in categories if item]) if isinstance(categories, list) else ""
        mentions = int(row.get("mentions") or 0) if isinstance(row.get("mentions"), (int, float)) else 0
        extra: list[str] = []
        if label:
            extra.append(f"画像：{label}")
        if mentions:
            extra.append(f"提及：{mentions}")
        extra_text = f"（{'；'.join(extra)}）" if extra else ""
        battlefield_lines.append(f"- **{name}**{extra_text}")
    battlefields = "\n".join(battlefield_lines) or "- 暂无战场数据"

    remediation_actions = sources.get("remediation_actions") or []
    remediation_note = ""
    try:
        if isinstance(remediation_actions, list) and remediation_actions:
            backfill_posts = sum(
                int(action.get("targets") or 0)
                for action in remediation_actions
                if isinstance(action, dict) and action.get("type") == "backfill_posts"
            )
            backfill_comments = sum(
                int(action.get("targets") or 0)
                for action in remediation_actions
                if isinstance(action, dict) and action.get("type") == "backfill_comments"
            )
            parts: list[str] = []
            if backfill_posts:
                parts.append(f"帖子补抓下单 {backfill_posts} 个 target")
            if backfill_comments:
                parts.append(f"评论补抓下单 {backfill_comments} 个 target")
            if parts:
                remediation_note = "系统已自动补量：" + "，".join(parts) + "（稍后重试会更准）。"
    except Exception:
        remediation_note = ""

    return dedent(
        f"""
        [Reddit Signal Scanner] 勘探简报（C_scouting）

        ## 已分析赛道
        - 赛道：{task_summary.product_description.strip()}
        - 关键词：{", ".join([str(item) for item in keywords if item])}
        - 数据范围：
          - 社区：{len(community_names)} 个
          - 帖子：{posts_analyzed} 条（缓存命中率 {cache_hit_rate:.0%}）
          - 评论：{comments_analyzed} 条（状态：{comments_status}）

        ## 决策卡片
        1) 需求趋势：目前样本主要集中在 {len(community_names)} 个社区，热度需要继续观察。
        2) 问题/解决方案比（P/S）：约 {ps_ratio}（先当“方向感”，别当结论）。
        3) 核心战场：{", ".join(community_names[:4]) or "待补充"}。
        4) 下一步建议：扩充样本（更多社区/更长时间窗/更明确关键词），再升级到 B/A 报告。{remediation_note}
        {warning_block}

        ## 核心战场推荐
        {battlefields}

        ## 备注
        目前样本只够做“前期观察”，还不足以输出完整的痛点/机会结论；等样本更充分后，会自动升级为 B/A 报告。
        """
    ).strip()


async def render_report_with_llm(
    *,
    task: TaskSummary,
    facts_slice: Mapping[str, Any] | None,
    report_tier: str,
    settings: Settings,
) -> str | None:
    if report_tier in {"C_scouting", "X_blocked"}:
        return None
    if not settings.enable_llm_summary:
        return None
    api_key = str(getattr(settings, "openai_api_key", "")).strip()
    if not api_key:
        return None
    if not facts_slice:
        return None

    facts_text = format_facts_for_prompt(facts_slice)
    prompt = build_complete_report_v9(task.product_description, facts_text)
    client = OpenAIChatClient(model=settings.llm_model_name, timeout=60.0, api_key=api_key)
    content = await client.generate(prompt, max_tokens=4000, temperature=0.25)
    return content.strip() or None


def extract_json_payload(raw: str) -> dict[str, Any] | None:
    text = (raw or "").strip()
    if not text:
        return None
    if "```" in text:
        lines: list[str] = []
        in_block = False
        for line in text.splitlines():
            if line.strip().startswith("```"):
                in_block = not in_block
                continue
            if in_block:
                lines.append(line)
        text = "\n".join(lines).strip() if lines else text
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


async def render_structured_report_with_llm(
    *,
    task: TaskSummary,
    facts_slice: Mapping[str, Any] | None,
    report_tier: str,
    settings: Settings,
) -> StructuredReportRenderResult:
    if report_tier in {"C_scouting", "X_blocked"}:
        return _structured_llm_skipped("tier_skipped")
    if not settings.enable_llm_summary:
        return _structured_llm_skipped("llm_summary_disabled")
    if str(settings.llm_model_name).strip() == "local-extractive":
        return _structured_llm_skipped("local_extractive_mode")
    api_key = str(getattr(settings, "openai_api_key", "")).strip()
    if not api_key:
        return _structured_llm_skipped("missing_api_key")
    if not facts_slice:
        return _structured_llm_skipped("missing_facts_slice")

    facts_text = format_facts_for_prompt(facts_slice)
    prompt = build_report_structured_prompt_v9(task.product_description, facts_text)
    client = OpenAIChatClient(model=settings.llm_model_name, timeout=60.0, api_key=api_key)
    try:
        raw = await client.generate(prompt, max_tokens=4000, temperature=0.25)
    except Exception:
        logger.warning("Structured report LLM render failed", exc_info=True)
        return StructuredReportRenderResult(
            report=None,
            status="failed",
            reason="llm_generate_failed",
            model=str(settings.llm_model_name),
            rounds=1,
        )
    payload = extract_json_payload(raw)
    if payload is None:
        return StructuredReportRenderResult(
            report=None,
            status="failed",
            reason="invalid_json_payload",
            model=str(settings.llm_model_name),
            rounds=1,
        )
    return StructuredReportRenderResult(
        report=payload,
        status="completed",
        reason=None,
        model=str(settings.llm_model_name),
        rounds=1,
    )


async def render_analysis_reports(
    *,
    task: TaskSummary,
    communities: Sequence[_CollectedCommunityLike],
    insights: Mapping[str, Any],
    sources: Mapping[str, Any],
    facts_slice: Mapping[str, Any] | None,
    report_tier: str,
    settings: Settings,
    blocked_flags: Sequence[str] | None = None,
    blocked_suggestion: str = "",
) -> AnalysisReportRenderBundle:
    if report_tier == "X_blocked":
        scouting_report = render_scouting_report(task, communities, sources)
        report_html = dedent(
            f"""
            [Reddit Signal Scanner] 报告拦截（X_blocked）

            这次数据不够“下结论”，所以系统把报告拦住了，避免输出误导性结论。

            - 原因：{", ".join([str(item) for item in blocked_flags or []]) or "unknown"}
            - 建议：{blocked_suggestion}

            ---

            {scouting_report}
            """
        ).strip()
    elif report_tier == "C_scouting":
        report_html = render_scouting_report(task, communities, sources)
    else:
        report_html = render_report(task, communities, insights, sources)

    structured_render = await render_structured_report_with_llm(
        task=task,
        facts_slice=facts_slice,
        report_tier=report_tier,
        settings=settings,
    )
    # Contract guard:
    # Always return a unified structured report skeleton so B/C/X stay as
    # simplified forms of the same product contract (instead of detached pages).
    if not structured_render.report:
        fallback_structured = build_structured_report_fallback(
            task=task,
            insights=insights,
            sources=sources,
            report_tier=report_tier,
            blocked_flags=blocked_flags,
            blocked_suggestion=blocked_suggestion,
        )
        structured_render = StructuredReportRenderResult(
            report=fallback_structured,
            status="completed",
            reason="deterministic_fallback",
            model=None,
            rounds=0,
        )
    return AnalysisReportRenderBundle(
        report_html=report_html,
        structured_render=structured_render,
    )


__all__ = [
    "AnalysisReportRenderBundle",
    "StructuredReportRenderResult",
    "extract_json_payload",
    "format_collection_warning_lines",
    "render_analysis_reports",
    "render_report",
    "render_report_with_llm",
    "render_scouting_report",
    "render_structured_report_with_llm",
]
