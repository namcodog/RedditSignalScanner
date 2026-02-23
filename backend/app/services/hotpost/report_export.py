from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return {}


def _format_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
        except Exception:
            return ""
    return _as_str(value)


def _format_pct(value: Any) -> str:
    if value is None:
        return "0%"
    if isinstance(value, str):
        return value if value.endswith("%") else value
    try:
        return f"{float(value) * 100:.0f}%"
    except Exception:
        return _as_str(value)


def _append_reliability(lines: list[str], data: dict[str, Any]) -> None:
    reliability = _as_str(data.get("reliability_note"))
    if reliability:
        lines.append("## 可靠性说明")
        lines.append(reliability)
        lines.append("")


def _append_next_steps(lines: list[str], data: dict[str, Any]) -> None:
    next_steps = _as_dict(data.get("next_steps") or {})
    if not next_steps:
        return
    lines.append("## 🚀 下一步")
    if next_steps.get("deepdive_available"):
        token = next_steps.get("deepdive_token") or ""
        lines.append(f"- ✅ 可生成深度报告 → ?token={token}")
    suggested = next_steps.get("suggested_keywords") or []
    if suggested:
        lines.append(f"- 💡 建议关键词：{'、'.join([_as_str(s) for s in suggested])}")
    lines.append("")


def _append_debug_info(lines: list[str], data: dict[str, Any]) -> None:
    debug = _as_dict(data.get("debug_info") or {})
    if not debug:
        return
    lines.append("## 🧪 调试信息")
    if debug.get("search_query"):
        lines.append(f"- 实际关键词：{debug.get('search_query')}")
    query_parts = debug.get("query_parts") or []
    if query_parts and len(query_parts) > 1:
        lines.append(f"- 拆分查询：{'; '.join([_as_str(p) for p in query_parts])}")
    subreddits = debug.get("subreddits") or []
    if subreddits:
        lines.append(f"- 命中社区：{', '.join([_as_str(s) for s in subreddits])}")
    if debug.get("time_filter"):
        lines.append(f"- 时间范围：{debug.get('time_filter')}")
    if debug.get("sort"):
        lines.append(f"- 排序方式：{debug.get('sort')}")
    if debug.get("raw_posts") is not None:
        lines.append(f"- 原始帖子数：{debug.get('raw_posts')}")
    if debug.get("filtered_posts") is not None:
        lines.append(f"- 过滤后帖子数：{debug.get('filtered_posts')}")
    if debug.get("relevance_filtered") is not None:
        lines.append(f"- 低相关过滤数：{debug.get('relevance_filtered')}")
    lines.append("")


def _export_trending_report(data: dict[str, Any]) -> str:
    query = _as_str(data.get("query") or "爆帖速递")
    mode = _as_str(data.get("mode") or "trending")
    generated_at = _format_datetime(data.get("search_time") or datetime.now(timezone.utc))
    summary = _as_str(data.get("summary"))
    confidence = _as_str(data.get("confidence"))
    evidence_count = _as_str(data.get("evidence_count"))
    community_distribution = data.get("community_distribution") or {}
    sentiment = data.get("sentiment_overview") or {}

    lines: list[str] = []
    lines.append(f"# {query} — Reddit 快报")
    lines.append("")
    lines.append(f"> 生成时间：{generated_at}  ")
    lines.append(f"> 模式：{mode}  ")
    lines.append("")

    lines.append("## 一句话结论")
    lines.append(summary or "（暂无结论）")
    lines.append("")

    lines.append("## 数据概况")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 可信度 | {confidence or '-'} |")
    lines.append(f"| 证据数 | {evidence_count or '0'} |")
    lines.append(f"| 社区数 | {len(community_distribution)} |")
    lines.append("")

    if sentiment:
        lines.append("**情绪概览**：")
        lines.append(
            f"正向 {sentiment.get('positive', 0):.2f} / "
            f"中性 {sentiment.get('neutral', 0):.2f} / "
            f"负向 {sentiment.get('negative', 0):.2f}"
        )
        lines.append("")

    if community_distribution:
        lines.append("**社区分布**：")
        for name, pct in community_distribution.items():
            lines.append(f"- {name}: {pct}")
        lines.append("")

    topics = data.get("topics") or []
    if topics:
        lines.append("## 🔥 热点话题")
        for topic in topics:
            topic = _as_dict(topic)
            if not topic:
                continue
            rank = topic.get("rank")
            title = topic.get("topic") or "未命名话题"
            trend = topic.get("time_trend") or "-"
            heat = topic.get("heat_score") or "-"
            takeaway = topic.get("key_takeaway") or ""

            lines.append(f"### {rank}. {title}")
            lines.append(f"- 趋势：{trend}")
            lines.append(f"- 热度：{heat}")
            if takeaway:
                lines.append(f"- 结论：{takeaway}")
            evidence = topic.get("evidence") or []
            if evidence:
                lines.append("")
                lines.append("**证据帖**：")
                for ev in evidence:
                    ev = _as_dict(ev)
                    if not ev:
                        continue
                    ev_title = ev.get("title") or ""
                    ev_url = ev.get("url") or ""
                    ev_score = ev.get("score") or 0
                    ev_comments = ev.get("comments") or 0
                    ev_sub = ev.get("subreddit") or ""
                    lines.append(f"- {ev_title} ({ev_sub}) | 👍 {ev_score} 💬 {ev_comments}")
                    if ev_url:
                        lines.append(f"  - 链接：{ev_url}")
                    key_quote = ev.get("key_quote")
                    if key_quote:
                        lines.append(f"  > {_truncate(_as_str(key_quote), 250)}")
            lines.append("")

    top_posts = data.get("top_posts") or []
    if top_posts:
        lines.append("## 🧵 代表性帖子")
        for post in top_posts:
            post = _as_dict(post)
            if not post:
                continue
            title = post.get("title") or ""
            subreddit = post.get("subreddit") or ""
            score = post.get("score") or 0
            comments = post.get("num_comments") or 0
            heat_score = post.get("heat_score") or "-"
            body_preview = _truncate(_as_str(post.get("body_preview") or ""), 300)
            url = post.get("reddit_url") or ""
            why = post.get("why_relevant") or ""

            lines.append(f"### {title}")
            lines.append("| 社区 | 点赞 | 评论 | 热度 |")
            lines.append("|------|-----|-----|-----|")
            lines.append(f"| {subreddit} | {score} | {comments} | {heat_score} |")
            if body_preview:
                lines.append("")
                lines.append(f"> {body_preview}")
            if why:
                lines.append("")
                lines.append(f"**为何重要**：{why}")

            top_comments = post.get("top_comments") or []
            if top_comments:
                lines.append("")
                lines.append("**🗣️ 神评论**:")
                for idx, comment in enumerate(top_comments[:3], start=1):
                    comment = _as_dict(comment)
                    if not comment:
                        continue
                    c_body = _truncate(_as_str(comment.get("body") or ""), 250)
                    c_score = comment.get("score") or 0
                    c_author = comment.get("author") or "-"
                    lines.append(f"{idx}. 👍 {c_score} | u/{c_author}")
                    lines.append(f"> {c_body}")
            if url:
                lines.append("")
                lines.append(f"📎 **原帖**: {url}")
            lines.append("")

    _append_reliability(lines, data)
    _append_debug_info(lines, data)
    _append_next_steps(lines, data)
    return "\n".join(lines).strip() + "\n"


def _export_rant_report(data: dict[str, Any]) -> str:
    query = _as_str(data.get("query") or "爆帖速递")
    generated_at = _format_datetime(data.get("search_time") or datetime.now(timezone.utc))
    summary = _as_str(data.get("summary"))
    confidence = _as_str(data.get("confidence"))
    evidence_count = _as_str(data.get("evidence_count"))
    community_distribution = data.get("community_distribution") or {}
    sentiment = data.get("sentiment_overview") or {}
    rant_intensity = data.get("rant_intensity") or {}

    lines: list[str] = []
    lines.append(f"# {query} — 痛点挖掘报告")
    lines.append("")
    lines.append(f"> 生成时间：{generated_at}  ")
    lines.append("> 模式：痛点挖掘 (Rant)  ")
    lines.append("")

    lines.append("## 📌 一句话结论")
    lines.append(summary or "（暂无结论）")
    lines.append("")

    lines.append("## 📊 数据概况")
    lines.append("| 指标 | 值 |")
    lines.append("|------|-----|")
    lines.append(f"| 可信度 | {confidence or '-'} |")
    lines.append(f"| 吐槽帖数 | {evidence_count or '0'} |")
    lines.append(f"| 社区数 | {len(community_distribution)} |")
    lines.append("")

    if sentiment:
        lines.append("**情绪分布**：")
        lines.append(
            f"正向 {_format_pct(sentiment.get('positive'))} / "
            f"中性 {_format_pct(sentiment.get('neutral'))} / "
            f"负向 {_format_pct(sentiment.get('negative'))}"
        )
        lines.append("")

    if rant_intensity:
        lines.append("**吐槽强度分布**：")
        lines.append(
            f"强烈 {_format_pct(rant_intensity.get('strong'))} / "
            f"中等 {_format_pct(rant_intensity.get('medium'))} / "
            f"轻微 {_format_pct(rant_intensity.get('weak'))}"
        )
        lines.append("")

    pain_points = data.get("pain_points") or []
    if pain_points:
        lines.append(f"## 🔥 核心痛点 Top {len(pain_points)}")
        for pain in pain_points:
            pain = _as_dict(pain)
            if not pain:
                continue
            rank = pain.get("rank") or ""
            category = pain.get("category") or "未命名痛点"
            severity = pain.get("severity") or "-"
            mentions = pain.get("mentions") or 0
            percentage = _format_pct(pain.get("percentage"))
            takeaway = pain.get("key_takeaway") or ""
            user_voice = pain.get("user_voice") or ""
            implication = pain.get("business_implication") or ""

            lines.append(f"### #{rank} {category}")
            lines.append("| 严重程度 | 提及次数 | 占比 |")
            lines.append("|---------|---------|------|")
            lines.append(f"| {severity} | {mentions} | {percentage} |")
            if takeaway:
                lines.append(f"**核心观点**：{takeaway}")
            if user_voice:
                lines.append("")
                lines.append(f"> \"{_truncate(_as_str(user_voice), 200)}\"")
            if implication:
                lines.append("")
                lines.append(f"**商业影响**：{implication}")

            evidence_posts = pain.get("evidence_posts") or []
            if evidence_posts:
                lines.append("")
                lines.append("**代表性帖子**：")
                for post in evidence_posts[:2]:
                    post = _as_dict(post)
                    if not post:
                        continue
                    title = post.get("title") or ""
                    subreddit = post.get("subreddit") or ""
                    score = post.get("score") or 0
                    comments = post.get("num_comments") or 0
                    heat_score = post.get("heat_score") or "-"
                    rant_score = post.get("rant_score") or "-"
                    signals = ", ".join(post.get("signals") or [])
                    url = post.get("reddit_url") or ""
                    lines.append(f"- {title} ({subreddit}) | 👍 {score} 💬 {comments} | 热度 {heat_score} | 吐槽分 {rant_score}")
                    if signals:
                        lines.append(f"  - 信号词：{signals}")
                    if url:
                        lines.append(f"  - 链接：{url}")
                    top_comments = post.get("top_comments") or []
                    if top_comments:
                        first = _as_dict(top_comments[0])
                        if first:
                            body = _truncate(_as_str(first.get("body") or ""), 200)
                            lines.append(f"  > {body}")
            lines.append("")

    migration = _as_dict(data.get("migration_intent") or {})
    if migration:
        lines.append("## 🚶 迁移意向分析")
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        lines.append(f"| 涉及迁移的帖子 | {migration.get('total_mentions', 0)} 条 |")
        lines.append(f"| 迁移意向占比 | {_format_pct(migration.get('percentage'))} |")
        status = migration.get("status_distribution") or {}
        if status:
            lines.append("")
            lines.append("**状态分布**：")
            lines.append(
                f"已离开 {_format_pct(status.get('already_left'))} / "
                f"考虑中 {_format_pct(status.get('considering'))} / "
                f"留守 {_format_pct(status.get('staying'))}"
            )
        destinations = migration.get("destinations") or []
        if destinations:
            lines.append("")
            lines.append("**用户流向**：")
            for dest in destinations:
                dest = _as_dict(dest)
                if not dest:
                    continue
                lines.append(f"- {dest.get('name')}: {dest.get('mentions')} ({dest.get('sentiment')})")
        key_quote = migration.get("key_quote")
        if key_quote:
            lines.append("")
            lines.append(f"> \"{_truncate(_as_str(key_quote), 200)}\"")
        lines.append("")

    competitors = data.get("competitor_mentions") or []
    if competitors:
        lines.append("## 🏢 竞品分析")
        for comp in competitors:
            comp = _as_dict(comp)
            if not comp:
                continue
            name = comp.get("name") or ""
            mentions = comp.get("mentions") or 0
            sentiment = comp.get("sentiment") or "-"
            score = comp.get("sentiment_score") or "-"
            lines.append(f"### {name}")
            lines.append(f"- 提及次数：{mentions}")
            lines.append(f"- 情绪倾向：{sentiment}（{score}）")
            praise = comp.get("common_praise") or []
            complaint = comp.get("common_complaint") or []
            if praise:
                lines.append(f"- 优势：{'、'.join([_as_str(p) for p in praise])}")
            if complaint:
                lines.append(f"- 短板：{'、'.join([_as_str(c) for c in complaint])}")
            vs_adobe = comp.get("vs_adobe") or ""
            if vs_adobe:
                lines.append(f"- 对比结论：{vs_adobe}")
            quote = comp.get("evidence_quote") or comp.get("sample_quote")
            if quote:
                lines.append(f"> \"{_truncate(_as_str(quote), 200)}\"")
            lines.append("")

    top_rants = data.get("top_rants") or []
    if top_rants:
        lines.append("## 📰 Top 吐槽帖 Top 5")
        for post in top_rants:
            post = _as_dict(post)
            if not post:
                continue
            title = post.get("title") or ""
            subreddit = post.get("subreddit") or ""
            score = post.get("score") or 0
            comments = post.get("num_comments") or 0
            heat_score = post.get("heat_score") or "-"
            rant_score = post.get("rant_score") or "-"
            signals = ", ".join(post.get("rant_signals") or [])
            why = post.get("why_important") or ""
            url = post.get("reddit_url") or ""
            body_preview = _truncate(_as_str(post.get("body_preview") or ""), 300)

            lines.append(f"### {title}")
            lines.append(f"- 社区：{subreddit} | 👍 {score} | 💬 {comments} | 热度 {heat_score} | 吐槽分 {rant_score}")
            if signals:
                lines.append(f"- 吐槽信号：{signals}")
            if body_preview:
                lines.append(f"> {body_preview}")
            if why:
                lines.append(f"**为什么重要**：{why}")
            if url:
                lines.append(f"📎 原帖：{url}")
            lines.append("")

    _append_reliability(lines, data)
    _append_debug_info(lines, data)
    _append_next_steps(lines, data)
    return "\n".join(lines).strip() + "\n"


def _export_opportunity_report(data: dict[str, Any]) -> str:
    query = _as_str(data.get("query") or "爆帖速递")
    generated_at = _format_datetime(data.get("search_time") or datetime.now(timezone.utc))
    summary = _as_str(data.get("summary"))
    confidence = _as_str(data.get("confidence"))
    evidence_count = _as_str(data.get("evidence_count"))
    community_distribution = data.get("community_distribution") or {}
    opportunity_strength = _as_str(data.get("opportunity_strength"))
    need_urgency = data.get("need_urgency") or {}

    lines: list[str] = []
    lines.append(f"# {query} — 机会发现报告")
    lines.append("")
    lines.append(f"> 生成时间：{generated_at}  ")
    lines.append("> 模式：机会发现 (Opportunity)  ")
    lines.append("")

    lines.append("## 📌 一句话结论")
    lines.append(summary or "（暂无结论）")
    lines.append("")

    lines.append("## 📊 数据概况")
    lines.append("| 指标 | 值 |")
    lines.append("|------|-----|")
    lines.append(f"| 可信度 | {confidence or '-'} |")
    lines.append(f"| 需求帖数 | {evidence_count or '0'} |")
    lines.append(f"| 社区数 | {len(community_distribution)} |")
    if opportunity_strength:
        lines.append(f"| 机会强度 | {opportunity_strength} |")
    lines.append("")

    if need_urgency:
        lines.append("**需求紧迫度分布**：")
        lines.append(
            f"紧迫 {_format_pct(need_urgency.get('urgent'))} / "
            f"一般 {_format_pct(need_urgency.get('moderate'))} / "
            f"随意 {_format_pct(need_urgency.get('casual'))}"
        )
        lines.append("")

    unmet_needs = data.get("unmet_needs") or []
    if unmet_needs:
        lines.append(f"## 🔎 核心需求 Top {len(unmet_needs)}")
        for need in unmet_needs:
            need = _as_dict(need)
            if not need:
                continue
            rank = need.get("rank") or ""
            name = need.get("need") or "未命名需求"
            urgency = need.get("urgency") or "-"
            mentions = need.get("mentions") or 0
            me_too = need.get("me_too_count") or 0
            price_range = need.get("price_range") or "-"
            takeaway = need.get("key_takeaway") or ""
            user_voice = need.get("user_voice") or ""

            lines.append(f"### #{rank} {name}")
            lines.append("| 紧迫度 | 提及次数 | 共鸣数 | 价格区间 |")
            lines.append("|-------|---------|-------|---------|")
            lines.append(f"| {urgency} | {mentions} | {me_too} | {price_range} |")
            if takeaway:
                lines.append(f"**核心观点**：{takeaway}")
            if user_voice:
                lines.append("")
                lines.append(f"> \"{_truncate(_as_str(user_voice), 200)}\"")

            workarounds = need.get("current_workarounds") or []
            if workarounds:
                lines.append("")
                lines.append("**现有替代方案**：")
                for item in workarounds:
                    item = _as_dict(item)
                    if not item:
                        continue
                    lines.append(f"- {item.get('name')}: {item.get('satisfaction')}")

            evidence_posts = need.get("evidence_posts") or []
            if evidence_posts:
                lines.append("")
                lines.append("**代表性帖子**：")
                for post in evidence_posts[:2]:
                    post = _as_dict(post)
                    if not post:
                        continue
                    title = post.get("title") or ""
                    subreddit = post.get("subreddit") or ""
                    score = post.get("score") or 0
                    comments = post.get("num_comments") or 0
                    heat_score = post.get("heat_score") or "-"
                    url = post.get("reddit_url") or ""
                    lines.append(f"- {title} ({subreddit}) | 👍 {score} 💬 {comments} | 热度 {heat_score}")
                    if url:
                        lines.append(f"  - 链接：{url}")
            lines.append("")

    existing_tools = data.get("existing_tools") or []
    if existing_tools:
        lines.append("## 🧰 现有工具")
        for tool in existing_tools:
            tool = _as_dict(tool)
            if not tool:
                continue
            name = tool.get("name") or ""
            mentions = tool.get("mentions") or 0
            sentiment = tool.get("sentiment") or "-"
            score = tool.get("sentiment_score") or "-"
            lines.append(f"### {name}")
            lines.append(f"- 提及次数：{mentions}")
            lines.append(f"- 情绪倾向：{sentiment}（{score}）")
            praise = tool.get("common_praise") or tool.get("praised_for") or []
            complaint = tool.get("common_complaint") or tool.get("criticized_for") or []
            if praise:
                lines.append(f"- 优势：{'、'.join([_as_str(p) for p in praise])}")
            if complaint:
                lines.append(f"- 短板：{'、'.join([_as_str(c) for c in complaint])}")
            gap = tool.get("gap_analysis") or ""
            if gap:
                lines.append(f"- 不足分析：{gap}")
            lines.append("")

    segments = data.get("user_segments") or []
    if segments:
        lines.append("## 👥 用户画像")
        for seg in segments:
            seg = _as_dict(seg)
            if not seg:
                continue
            lines.append(f"- {seg.get('segment')} ({seg.get('percentage')})")
            key_need = seg.get("key_need") or seg.get("core_need")
            if key_need:
                lines.append(f"  - 关键需求：{key_need}")
            sensitivity = seg.get("price_sensitivity")
            if sensitivity:
                lines.append(f"  - 价格敏感度：{sensitivity}")
            quote = seg.get("typical_quote")
            if quote:
                lines.append(f"  > \"{_truncate(_as_str(quote), 200)}\"")
        lines.append("")

    market = _as_dict(data.get("market_opportunity") or {})
    if market:
        lines.append("## 📈 市场机会")
        strength = market.get("strength") or "-"
        unmet_gap = market.get("unmet_gap") or market.get("gap") or ""
        demand_signal = market.get("demand_signal") or "-"
        competition = market.get("competition_level") or "-"
        recommendation = market.get("recommendation") or ""
        lines.append(f"- 机会强度：{strength}")
        if unmet_gap:
            lines.append(f"- 市场空白：{unmet_gap}")
        lines.append(f"- 需求信号：{demand_signal}")
        lines.append(f"- 竞争强度：{competition}")
        if recommendation:
            lines.append(f"- 建议：{recommendation}")
        lines.append("")

    top_discovery = data.get("top_discovery_posts") or []
    if top_discovery:
        lines.append("## 📰 Top 发现帖 Top 5")
        for post in top_discovery:
            post = _as_dict(post)
            if not post:
                continue
            title = post.get("title") or ""
            subreddit = post.get("subreddit") or ""
            score = post.get("score") or 0
            comments = post.get("num_comments") or 0
            heat_score = post.get("heat_score") or "-"
            resonance = post.get("resonance_count") or 0
            why = post.get("why_important") or ""
            url = post.get("reddit_url") or ""
            body_preview = _truncate(_as_str(post.get("body_preview") or ""), 300)

            lines.append(f"### {title}")
            lines.append(f"- 社区：{subreddit} | 👍 {score} | 💬 {comments} | 热度 {heat_score} | 共鸣 {resonance}")
            if body_preview:
                lines.append(f"> {body_preview}")
            if why:
                lines.append(f"**为什么重要**：{why}")
            if url:
                lines.append(f"📎 原帖：{url}")
            lines.append("")

    _append_reliability(lines, data)
    _append_debug_info(lines, data)
    _append_next_steps(lines, data)
    return "\n".join(lines).strip() + "\n"


def export_markdown_report(data: dict[str, Any]) -> str:
    mode = _as_str(data.get("mode") or "trending")
    if mode == "rant":
        return _export_rant_report(data)
    if mode == "opportunity":
        return _export_opportunity_report(data)
    return _export_trending_report(data)


__all__ = ["export_markdown_report"]
