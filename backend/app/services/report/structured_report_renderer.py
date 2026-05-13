from __future__ import annotations

from typing import Any, Mapping, Sequence


def render_structured_report_markdown(
    report_structured: Mapping[str, Any] | None,
    *,
    product_description: str,
    facts_slice: Mapping[str, Any] | None,
    pain_points: Sequence[Any] | None,
) -> str | None:
    if not report_structured:
        return None

    def _safe_text(value: Any) -> str:
        return str(value).strip() if value not in (None, "") else ""

    def _safe_list(value: Any) -> list[Any]:
        return list(value) if isinstance(value, list) else []

    def _fmt_lines(items: Sequence[str], indent: int = 0) -> list[str]:
        pad = " " * indent
        return [f"{pad}- {item}" for item in items if item]

    def _extract_volume() -> tuple[int, int]:
        aggregates = (facts_slice or {}).get("aggregates") or {}
        communities = aggregates.get("communities") or []
        posts_total = 0
        comments_total = 0
        if isinstance(communities, list):
            for entry in communities:
                if not isinstance(entry, dict):
                    continue
                posts_total += int(entry.get("posts", 0) or 0)
                comments_total += int(entry.get("comments", 0) or 0)
        return posts_total, comments_total

    def _collect_core_communities() -> list[str]:
        battlefields = _safe_list(report_structured.get("battlefields"))
        names: list[str] = []
        for battlefield in battlefields:
            if not isinstance(battlefield, dict):
                continue
            subreddits = battlefield.get("subreddits") or []
            for subreddit in subreddits:
                subreddit_text = _safe_text(subreddit)
                if subreddit_text and subreddit_text not in names:
                    names.append(subreddit_text)
        if names:
            return names[:5]
        aggregates = (facts_slice or {}).get("aggregates") or {}
        communities = aggregates.get("communities") or []
        for entry in communities:
            if not isinstance(entry, dict):
                continue
            name = _safe_text(entry.get("name"))
            if name and name not in names:
                names.append(name)
        return names[:5]

    def _extract_evidence_links(idx: int) -> list[str]:
        if not pain_points or idx >= len(pain_points):
            return []
        entry = pain_points[idx]
        examples = getattr(entry, "example_posts", None) or []
        links: list[str] = []
        for post in examples:
            url = None
            text = None
            if isinstance(post, dict):
                url = post.get("url") or post.get("permalink")
                text = post.get("content") or post.get("title")
            else:
                url = getattr(post, "url", None) or getattr(post, "permalink", None)
                text = getattr(post, "content", None) or getattr(post, "title", None)
            url_text = _safe_text(url)
            if not url_text:
                continue
            text_value = _safe_text(text)
            if text_value:
                if len(text_value) > 60:
                    text_value = f"{text_value[:60]}..."
                links.append(f"[{text_value}]({url_text})")
            else:
                links.append(url_text)
        return links[:2]

    decision_cards = _safe_list(report_structured.get("decision_cards"))
    structured_market_health = report_structured.get("market_health") or {}
    battlefields = _safe_list(report_structured.get("battlefields"))
    pain_list = _safe_list(report_structured.get("pain_points"))
    drivers = _safe_list(report_structured.get("drivers"))
    opportunities = _safe_list(report_structured.get("opportunities"))

    core_communities = _collect_core_communities()
    posts_total, comments_total = _extract_volume()
    summary_parts: list[str] = []
    for card in decision_cards:
        if not isinstance(card, dict):
            continue
        if card.get("title") == "需求趋势":
            summary_parts.append(_safe_text(card.get("conclusion")))
        if card.get("title") == "核心社群":
            summary_parts.append(_safe_text(card.get("conclusion")))
    summary_line = "；".join([part for part in summary_parts if part])

    lines: list[str] = [
        "# 市场洞察报告",
        "",
        "## 顶部信息",
        f"- 标题：{_safe_text(product_description)} · 市场洞察报告",
    ]
    if summary_line:
        lines.append(f"- 简述：{summary_line}")
    if core_communities:
        lines.append(f"- 核心社区：{', '.join(core_communities)}")
    lines.append("- 时间窗口：过去 12 个月")
    if posts_total or comments_total:
        lines.append(f"- 数据量级：约 {posts_total} 帖 / {comments_total} 评论")
    else:
        lines.append("- 数据量级：数据不足")
    lines.extend(["", "## 决策卡片"])
    for card in decision_cards:
        if not isinstance(card, dict):
            continue
        title = _safe_text(card.get("title")) or "要点"
        conclusion = _safe_text(card.get("conclusion"))
        details = [_safe_text(x) for x in _safe_list(card.get("details"))]
        lines.append(f"### {title}")
        if conclusion:
            lines.append(f"- 结论：{conclusion}")
        if details:
            lines.append("- 依据：")
            lines.extend(_fmt_lines(details, indent=2))
        lines.append("")

    lines.append("## 概览（市场健康度诊断）")
    competition = structured_market_health.get("competition_saturation") or {}
    ps_ratio = structured_market_health.get("ps_ratio") or {}
    comp_level = _safe_text(competition.get("level"))
    comp_interp = _safe_text(competition.get("interpretation"))
    comp_details = [_safe_text(x) for x in _safe_list(competition.get("details"))]
    if comp_level or comp_interp or comp_details:
        lines.append("### 竞争饱和度")
        if comp_level:
            lines.append(f"- 结论：{comp_level}")
        if comp_details:
            lines.append("- 依据：")
            lines.extend(_fmt_lines(comp_details, indent=2))
        if comp_interp:
            lines.append(f"- 解读：{comp_interp}")
    ps_ratio_value = _safe_text(ps_ratio.get("ratio"))
    ps_conclusion = _safe_text(ps_ratio.get("conclusion"))
    ps_interp = _safe_text(ps_ratio.get("interpretation"))
    if ps_ratio_value or ps_conclusion or ps_interp:
        lines.append("### 难题与攻略比解读")
        if ps_ratio_value:
            lines.append(f"- 比例：{ps_ratio_value}")
        if ps_conclusion:
            lines.append(f"- 结论：{ps_conclusion}")
        if ps_interp:
            lines.append(f"- 解读：{ps_interp}")
    lines.append("")

    lines.append("## 核心战场推荐（分社区画像）")
    for idx in range(4):
        entry = battlefields[idx] if idx < len(battlefields) else None
        label = f"战场 {idx + 1}"
        if not isinstance(entry, dict):
            lines.append(f"### {label}（数据不足，暂无覆盖）")
            lines.append("")
            continue
        name = _safe_text(entry.get("name")) or label
        subreddits = [
            _safe_text(x)
            for x in _safe_list(entry.get("subreddits"))
            if _safe_text(x)
        ]
        profile = _safe_text(entry.get("profile"))
        pains = [
            _safe_text(x)
            for x in _safe_list(entry.get("pain_points"))
            if _safe_text(x)
        ]
        strategy = _safe_text(entry.get("strategy_advice"))
        lines.append(f"### {label}：{name}")
        if subreddits:
            lines.append(f"- 相关社区：{', '.join(subreddits)}")
        if profile:
            lines.append(f"- 人群画像：{profile}")
        if pains:
            lines.append("- 核心吐槽点：")
            lines.extend(_fmt_lines(pains, indent=2))
        if strategy:
            lines.append(f"- 进入策略：{strategy}")
        lines.append("")

    lines.append("## 用户痛点（3 个）")
    for idx, item in enumerate(pain_list[:3], start=1):
        if not isinstance(item, dict):
            continue
        title = _safe_text(item.get("title")) or f"痛点 {idx}"
        voices = [
            _safe_text(x)
            for x in _safe_list(item.get("user_voices"))
            if _safe_text(x)
        ]
        impression = _safe_text(item.get("data_impression"))
        interpretation = _safe_text(item.get("interpretation"))
        lines.append(f"### {idx}. {title}")
        if voices:
            lines.append("- 用户原声：")
            lines.extend(_fmt_lines(voices, indent=2))
        if impression:
            lines.append(f"- 数据印象：{impression}")
        if interpretation:
            lines.append(f"- 解读：{interpretation}")
        evidence = _extract_evidence_links(idx - 1)
        if evidence:
            lines.append("- 证据链接：")
            lines.extend(_fmt_lines(evidence, indent=2))
        lines.append("")

    lines.append("## Top 购买驱动力")
    for item in drivers[:3]:
        if not isinstance(item, dict):
            continue
        title = _safe_text(item.get("title"))
        description = _safe_text(item.get("description"))
        if title:
            lines.append(f"- {title}：{description}" if description else f"- {title}")
    lines.append("")

    lines.append("## 商业机会（机会卡）")
    for idx, item in enumerate(opportunities[:2], start=1):
        if not isinstance(item, dict):
            continue
        title = _safe_text(item.get("title")) or f"机会 {idx}"
        target_pains = [
            _safe_text(x)
            for x in _safe_list(item.get("target_pain_points"))
            if _safe_text(x)
        ]
        target_communities = [
            _safe_text(x)
            for x in _safe_list(item.get("target_communities"))
            if _safe_text(x)
        ]
        positioning = _safe_text(item.get("product_positioning"))
        selling_points = [
            _safe_text(x)
            for x in _safe_list(item.get("core_selling_points"))
            if _safe_text(x)
        ]
        lines.append(f"### 机会卡 {idx}：{title}")
        if target_pains:
            lines.append(f"- 痛点：{', '.join(target_pains)}")
        if target_communities:
            lines.append(f"- 目标社群：{', '.join(target_communities)}")
        if positioning:
            lines.append(f"- 产品定位：{positioning}")
        if selling_points:
            lines.append("- 卖点：")
            lines.extend(_fmt_lines(selling_points, indent=2))
        lines.append("")

    return "\n".join(lines).strip()


__all__ = ["render_structured_report_markdown"]
