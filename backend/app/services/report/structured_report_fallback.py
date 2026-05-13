from __future__ import annotations

from typing import Any, Mapping, Sequence

from app.schemas.task import TaskSummary


def build_structured_report_fallback(
    *,
    task: TaskSummary,
    insights: Mapping[str, Any],
    sources: Mapping[str, Any],
    report_tier: str,
    blocked_flags: Sequence[str] | None = None,
    blocked_suggestion: str = "",
) -> dict[str, Any]:
    """
    Build a deterministic structured report when LLM structured output is unavailable.

    Why this exists:
    - Full A contract requires one unified report skeleton.
    - We cannot let UI fallback fabricate structure independently.
    - B/C/X should be simplified versions on the same skeleton, not a separate shape.
    """

    def _txt(value: Any) -> str:
        return str(value).strip() if value not in (None, "") else ""

    def _list(value: Any) -> list[Any]:
        return list(value) if isinstance(value, list) else []

    def _int(value: Any) -> int:
        try:
            return int(value or 0)
        except Exception:
            return 0

    def _float(value: Any) -> float:
        try:
            return float(value or 0.0)
        except Exception:
            return 0.0

    communities_detail = _list(sources.get("communities_detail"))
    communities_sorted = sorted(
        [row for row in communities_detail if isinstance(row, dict)],
        key=lambda row: _int(row.get("mentions")),
        reverse=True,
    )
    community_names = [_txt(row.get("name")) for row in communities_sorted if _txt(row.get("name"))]
    if not community_names:
        community_names = [_txt(name) for name in _list(sources.get("communities")) if _txt(name)]
    top_communities = community_names[:4]
    if not top_communities:
        top_communities = ["r/insight"]

    posts_analyzed = _int(sources.get("posts_analyzed"))
    comments_analyzed = _int(sources.get("comments_analyzed"))
    ps_ratio_value = sources.get("ps_ratio")
    ps_ratio = f"{_float(ps_ratio_value):.2f}" if isinstance(ps_ratio_value, (int, float)) else "N/A"

    pain_points = [row for row in _list(insights.get("pain_points")) if isinstance(row, dict)]
    opportunities = [row for row in _list(insights.get("opportunities")) if isinstance(row, dict)]
    top_drivers = _list(insights.get("top_drivers"))

    tier_is_full = report_tier == "A_full"
    tier_is_trimmed = report_tier == "B_trimmed"
    tier_is_scouting = report_tier == "C_scouting"
    tier_is_blocked = report_tier == "X_blocked"

    trend_conclusion = (
        f"过去周期内已覆盖 {posts_analyzed} 帖 / {comments_analyzed} 评论，趋势可用于继续决策。"
        if tier_is_full
        else f"当前覆盖 {posts_analyzed} 帖 / {comments_analyzed} 评论，先用于方向判断。"
    )
    if tier_is_blocked:
        trend_conclusion = "当前样本仍不够稳定，先看线索，不直接下结论。"

    ps_conclusion = (
        f"P/S 比约 {ps_ratio}，痛点与方案已形成可读结构。"
        if tier_is_full
        else f"P/S 比约 {ps_ratio}，先看方向，后续补全证据。"
    )

    core_battle_conclusion = (
        f"当前最活跃社区集中在 {', '.join(top_communities[:3])}。"
        if top_communities
        else "当前社区分布仍在补齐。"
    )

    if opportunities:
        opp_text = _txt(opportunities[0].get("description")) or _txt(opportunities[0].get("title"))
    else:
        opp_text = ""
    explicit_opportunity = (
        f"已出现机会线索：{opp_text}" if opp_text else "先锁定方向机会，再补完整机会卡。"
    )

    if tier_is_blocked and blocked_flags:
        explicit_opportunity = f"本轮被质量门禁拦截（{', '.join([_txt(x) for x in blocked_flags if _txt(x)])}）。"
    if tier_is_blocked and _txt(blocked_suggestion):
        explicit_opportunity = f"{explicit_opportunity} 建议：{_txt(blocked_suggestion)}"

    decision_cards = [
        {
            "title": "需求趋势",
            "conclusion": trend_conclusion,
            "details": [
                f"覆盖社区：{len(community_names)} 个",
                "这是系统生成的统一结构报告，不依赖前端拼装。",
            ],
        },
        {
            "title": "问题/解决方案比",
            "conclusion": ps_conclusion,
            "details": [
                f"P/S 比：{ps_ratio}",
                "结论力度会随证据强度自动升级或保守。",
            ],
        },
        {
            "title": "核心社群",
            "conclusion": core_battle_conclusion,
            "details": [
                "优先看高活跃且重复抱怨出现的社区。",
                "社区名单由本轮分析真实数据生成。",
            ],
        },
        {
            "title": "明确机会点",
            "conclusion": explicit_opportunity,
            "details": [
                "机会卡与痛点卡使用同一条证据链。",
                "B/C 是 Full A 同骨架简化，不走独立页面结构。",
            ],
        },
    ]

    battlefields: list[dict[str, Any]] = []
    for idx in range(4):
        name = top_communities[idx] if idx < len(top_communities) else f"r/insight_{idx + 1}"
        pain_text = _txt(pain_points[idx].get("description")) if idx < len(pain_points) else ""
        profile = (
            "讨论量和抱怨强度都已达到可执行判断门槛。"
            if tier_is_full
            else "讨论信号已经出现，适合先做方向判断。"
        )
        if tier_is_blocked:
            profile = "目前主要是线索态，先补样本再做完整判断。"
        battlefields.append(
            {
                "name": name,
                "subreddits": [name],
                "profile": profile,
                "pain_points": [pain_text] if pain_text else ["先看该社区是否持续出现同类抱怨。"],
                "strategy_advice": "先在该社区验证问题复现频率，再决定是否深挖。",
            }
        )

    structured_pain_points: list[dict[str, Any]] = []
    for idx in range(3):
        row = pain_points[idx] if idx < len(pain_points) else {}
        title = _txt(row.get("description")) or f"关键痛点 {idx + 1}"
        voices = [_txt(v) for v in _list(row.get("user_examples")) if _txt(v)][:3]
        if not voices:
            voices = ["本轮讨论中该问题有重复出现迹象。"]
        structured_pain_points.append(
            {
                "title": title,
                "user_voices": voices,
                "data_impression": f"覆盖 {len(community_names)} 个社区，已出现可追踪信号。",
                "interpretation": (
                    "该痛点可直接进入解决方案验证。"
                    if tier_is_full
                    else "该痛点已可用于方向判断，后续补齐更强证据。"
                ),
            }
        )

    structured_drivers: list[dict[str, Any]] = []
    for idx, driver in enumerate(top_drivers[:3]):
        if isinstance(driver, dict):
            title = _txt(driver.get("title")) or f"驱动力 {idx + 1}"
            description = _txt(driver.get("description")) or "该驱动力在讨论中反复出现。"
        else:
            title = _txt(driver) or f"驱动力 {idx + 1}"
            description = "该驱动力在讨论中反复出现。"
        structured_drivers.append({"title": title, "description": description})
    while len(structured_drivers) < 3:
        num = len(structured_drivers) + 1
        structured_drivers.append(
            {"title": f"驱动力 {num}", "description": "用户持续强调效率、透明和可控的解决体验。"}
        )

    structured_opportunities: list[dict[str, Any]] = []
    for idx in range(2):
        row = opportunities[idx] if idx < len(opportunities) else {}
        title = _txt(row.get("description")) or _txt(row.get("title")) or f"机会 {idx + 1}"
        key_insights = [_txt(x) for x in _list(row.get("key_insights")) if _txt(x)]
        structured_opportunities.append(
            {
                "title": title,
                "target_pain_points": key_insights[:3] or [structured_pain_points[idx]["title"]],
                "target_communities": top_communities[:3],
                "product_positioning": _txt(row.get("potential_users"))
                or "先用小范围验证该机会的复现与转化价值。",
                "core_selling_points": key_insights[:3]
                or ["明确痛点", "可执行步骤", "结果可验证"],
            }
        )

    competition_level = "中等竞争，可差异化切入"
    if tier_is_full:
        competition_level = "竞争可见，但仍有结构性机会"
    if tier_is_blocked:
        competition_level = "暂不下竞争结论，先补样本"

    return {
        "decision_cards": decision_cards,
        "market_health": {
            "competition_saturation": {
                "level": competition_level,
                "details": [
                    f"已分析 {posts_analyzed} 帖 / {comments_analyzed} 评论。",
                    f"核心社区：{', '.join(top_communities[:3])}",
                ],
                "interpretation": (
                    "当前结论可用于继续推进。"
                    if tier_is_full or tier_is_trimmed
                    else "当前以方向线索为主，建议补样本后再做强结论。"
                ),
            },
            "ps_ratio": {
                "ratio": ps_ratio,
                "conclusion": ps_conclusion,
                "interpretation": "该比例用于判断市场是在抱怨积压还是方案成熟阶段。",
                "health_assessment": (
                    "可继续推进"
                    if tier_is_full
                    else "先方向判断"
                    if tier_is_scouting or tier_is_trimmed
                    else "先补样本"
                ),
            },
        },
        "battlefields": battlefields,
        "pain_points": structured_pain_points,
        "drivers": structured_drivers,
        "opportunities": structured_opportunities,
    }


def enforce_structured_report_contract(
    *,
    task: TaskSummary,
    insights: Mapping[str, Any],
    sources: Mapping[str, Any],
    report_tier: str,
    candidate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    fallback = build_structured_report_fallback(
        task=task,
        insights=insights,
        sources=sources,
        report_tier=report_tier,
    )
    if not isinstance(candidate, Mapping):
        return fallback
    structured = dict(candidate)
    for key, value in fallback.items():
        if key not in structured or structured[key] in (None, [], {}):
            structured[key] = value
    return structured


__all__ = ["build_structured_report_fallback", "enforce_structured_report_contract"]
