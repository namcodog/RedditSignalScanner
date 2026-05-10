from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Optional, Any

from app.services.analysis.signal_extraction import OpportunitySignal, PainPointSignal
from app.services.report.content_guardrails import (
    clean_business_terms,
    contains_cjk_text,
    sanitize_business_text,
)

ExamplePostsBuilder = Callable[[Sequence[str], str, bool], list[dict[str, Any]]]
UserExamplesBuilder = Callable[[Sequence[str], str], list[str]]
PainTranslator = Callable[[str, Sequence[Mapping[str, Any]]], Mapping[str, Any]]
OpportunityTranslator = Callable[[str, Sequence[Mapping[str, Any]]], Mapping[str, Any]]


@dataclass(slots=True)
class InsightSynthesisSummary:
    insights: dict[str, Any]
    action_reports: list[dict[str, Any]]
    entity_summary: dict[str, Any]
    channel_breakdown: list[dict[str, Any]]
    top_communities: list[str]
    battlefield_profiles: list[dict[str, Any]]
    top_drivers: list[dict[str, Any]]


_SEMANTIC_SCAFFOLD_RULES: tuple[dict[str, Any], ...] = (
    {
        "patterns": ("payout", "refund", "supplier", "cash flow", "checkout", "payment", "bank account", "pay"),
        "pain": "回款慢、手续费高，现金周转经常被卡住",
        "opportunity": "多平台收款与回款诊断助手",
    },
    {
        "patterns": ("edc", "carry", "pocket", "bulk", "organizer", "key", "knife", "flashlight", "multitool"),
        "pain": "随身小物一多，口袋发鼓、分类混乱，拿取很不顺手",
        "opportunity": "随身收纳分区与快速取用助手",
    },
    {
        "patterns": ("workflow", "automation", "prompt", "knowledge", "progress", "handoff", "internal tool", "notion", "claude", "chatgpt"),
        "pain": "任务和知识散落在多处，协作推进情况很不透明",
        "opportunity": "团队协作进度与知识归档助手",
    },
    {
        "patterns": ("vacuum", "dust", "pet hair", "cleaning", "storage", "organization", "declutter", "small space"),
        "pain": "灰尘和宠物毛反复积累，小空间清洁收纳很费力",
        "opportunity": "小空间清洁收纳与 routine 提醒助手",
    },
    {
        "patterns": ("newborn", "baby", "feeding", "sleep", "night", "routine", "tracker", "parent"),
        "pain": "夜奶、睡眠和喂养记录容易断档，家人协作经常接不上",
        "opportunity": "夜奶睡眠与喂养协作记录助手",
    },
    {
        "patterns": ("espresso", "grinder", "extraction", "dial", "shot", "brew", "beans"),
        "pain": "磨豆和萃取参数总要反复重调，稳定出杯很费时间",
        "opportunity": "咖啡参数记录与复现助手",
    },
    {
        "patterns": ("onebag", "travel", "backpack", "camping", "hiking", "outdoor", "gear"),
        "pain": "出行和户外装备越带越乱，收纳和取用都不顺手",
        "opportunity": "轻量出行装备分装与清单助手",
    },
    {
        "patterns": ("frugal", "budget", "subscription", "bill", "save money", "coupon", "cheap", "spending"),
        "pain": "订阅和账单分散，想省钱却很难持续盯住支出",
        "opportunity": "订阅账单盘点与省钱提醒助手",
    },
)


def _infer_semantic_cjk_phrase(
    text: Any,
    *,
    kind: str,
    fallback: str,
) -> str:
    lower = str(text or "").lower()
    if not lower:
        return fallback
    for rule in _SEMANTIC_SCAFFOLD_RULES:
        if any(pattern in lower for pattern in rule["patterns"]):
            candidate = str(rule[kind]).strip()
            if candidate:
                return candidate
    return fallback


def _build_cjk_scaffold(
    text: Any,
    *,
    prefix: str,
    kind: str,
) -> str:
    cleaned = sanitize_business_text(
        text,
        fallback="",
        reject_low_signal=True,
    )
    if not cleaned:
        return ""
    if contains_cjk_text(cleaned):
        return cleaned
    compact = " ".join(part for part in cleaned.split() if part).strip(" ,.;:-_/")
    if not compact:
        return ""
    semantic = _infer_semantic_cjk_phrase(
        compact,
        kind=kind,
        fallback="",
    )
    if semantic and contains_cjk_text(semantic):
        return semantic
    if len(compact) > 48:
        compact = compact[:48].rstrip(" ,.;:-_/") + "..."
    return f"{prefix}：{compact}"


def build_pain_points_payload(
    pain_signals: Sequence[PainPointSignal],
    *,
    build_example_posts: ExamplePostsBuilder,
    build_user_examples: UserExamplesBuilder,
    translate_pain_signal: PainTranslator,
    classify_pain_severity: Callable[[int, float], str],
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for pain_signal in pain_signals:
        source_examples = list(
            build_example_posts(
                pain_signal.source_posts,
                pain_signal.description,
                False,
            )
        )
        translated_pain = translate_pain_signal(
            pain_signal.description,
            source_examples,
        )
        cleaned_description = sanitize_business_text(
            pain_signal.description,
            fallback="",
            reject_low_signal=True,
        )
        if not contains_cjk_text(cleaned_description):
            cleaned_description = sanitize_business_text(
                translated_pain.get("description"),
                fallback="",
                reject_low_signal=True,
            )
        if not contains_cjk_text(cleaned_description):
            fallback_seed = ""
            if source_examples:
                fallback_seed = str(
                    source_examples[0].get("title")
                    or source_examples[0].get("content")
                    or ""
                )
            cleaned_description = _build_cjk_scaffold(
                translated_pain.get("description")
                or pain_signal.description
                or fallback_seed,
                prefix="高频抱怨",
                kind="pain",
            )
        if not contains_cjk_text(cleaned_description):
            continue
        severity = classify_pain_severity(
            pain_signal.frequency,
            pain_signal.sentiment,
        )
        user_examples = list(translated_pain.get("user_examples") or [])
        if not user_examples:
            user_examples = list(
                build_user_examples(
                    pain_signal.source_posts,
                    pain_signal.description,
                )
            )
        user_examples = [
            example.strip()
            for example in user_examples
            if isinstance(example, str) and contains_cjk_text(example.strip())
        ]
        if not user_examples:
            user_examples = [f"围绕「{cleaned_description}」的抱怨在本轮样本里反复出现。"]
        payload.append(
            {
                "description": cleaned_description,
                "frequency": pain_signal.frequency,
                "sentiment_score": round(pain_signal.sentiment, 2),
                "severity": severity,
                "example_posts": source_examples,
                "user_examples": user_examples,
            }
        )
    return payload


def pick_linked_pain_cluster(
    description: str,
    clusters: Sequence[Mapping[str, Any]],
) ->Optional[ str]:
    lower = (description or "").lower()
    best:Optional[ str] = None
    for entry in clusters:
        topic = sanitize_business_text(
            entry.get("topic"),
            fallback="",
            reject_low_signal=True,
        )
        if topic and topic.lower() in lower:
            best = topic
            break
    if best is None and clusters:
        best = sanitize_business_text(
            clusters[0].get("topic"),
            fallback="",
            reject_low_signal=True,
        )
    return best


def clean_opportunity_copy(
    *,
    raw_keywords: Sequence[Any],
    linked_cluster:Optional[ str],
    description: str,
) -> list[str]:
    cleaned = clean_business_terms(raw_keywords)
    if linked_cluster and linked_cluster not in cleaned:
        cleaned.insert(0, linked_cluster)
    if not cleaned and description:
        cleaned = [description]
    return cleaned[:4]


def build_opportunities_payload(
    opportunity_signals: Sequence[OpportunitySignal],
    *,
    build_example_posts: ExamplePostsBuilder,
    translate_opportunity_signal: OpportunityTranslator,
    clusters: Sequence[Mapping[str, Any]],
    fallback_channels: Sequence[str],
    select_opportunity_channels: Callable[[Sequence[Mapping[str, Any]], Sequence[str]], list[str]],
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for opportunity_signal in opportunity_signals:
        source_examples = list(
            build_example_posts(
                opportunity_signal.source_posts,
                opportunity_signal.description,
                True,
            )
        )
        translated_opportunity = translate_opportunity_signal(
            opportunity_signal.description,
            source_examples,
        )
        description = sanitize_business_text(
            opportunity_signal.description,
            fallback="",
            reject_low_signal=True,
        )
        translated_description = sanitize_business_text(
            translated_opportunity.get("description"),
            fallback="",
            reject_low_signal=True,
        )
        if (not description) or (
            translated_description and not contains_cjk_text(description)
        ):
            description = translated_description
        linked_cluster = sanitize_business_text(
            pick_linked_pain_cluster(opportunity_signal.description, clusters),
            fallback="",
            reject_low_signal=True,
        )
        if not linked_cluster:
            linked_cluster = sanitize_business_text(
                translated_opportunity.get("linked_pain_cluster"),
                fallback="",
                reject_low_signal=True,
            )
        if description and not contains_cjk_text(description):
            fallback_seed = ""
            if source_examples:
                fallback_seed = str(
                    source_examples[0].get("title")
                    or source_examples[0].get("content")
                    or ""
                )
            description = _build_cjk_scaffold(
                translated_description
                or opportunity_signal.description
                or fallback_seed,
                prefix="产品机会",
                kind="opportunity",
            )
        key_insights = clean_opportunity_copy(
            raw_keywords=[
                *(translated_opportunity.get("key_insights") or []),
                *list(opportunity_signal.keywords or []),
            ],
            linked_cluster=linked_cluster,
            description=description,
        )
        if not description and not linked_cluster and not key_insights:
            continue
        top_channels = select_opportunity_channels(
            source_examples,
            fallback_channels,
        )
        payload.append(
            {
                "description": description or linked_cluster or "围绕高频支付摩擦的产品机会",
                "relevance_score": round(opportunity_signal.relevance, 2),
                "potential_users": f"约{opportunity_signal.potential_users}个潜在团队",
                "potential_users_est": int(opportunity_signal.potential_users),
                "linked_pain_cluster": linked_cluster or None,
                "top_channels": top_channels,
                "key_insights": key_insights,
                "source_examples": source_examples,
            }
        )
    return payload


def finalize_insights_summary(
    *,
    insights: Mapping[str, Any],
    communities_detail: Sequence[Mapping[str, Any]],
    pain_counts_by_community: Mapping[str, int],
    build_action_reports: Callable[[Mapping[str, Any]], Sequence[Mapping[str, Any]]],
    summarize_entities: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    summarize_entities_fallback: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    build_battlefield_profiles: Callable[[Sequence[Mapping[str, Any]], Sequence[Mapping[str, Any]], Mapping[str, int], int], list[dict[str, Any]]],
    build_top_drivers: Callable[[Sequence[Mapping[str, Any]], Sequence[Mapping[str, Any]], int], list[dict[str, Any]]],
    battlefield_limit: int = 4,
    driver_limit: int = 3,
) -> InsightSynthesisSummary:
    synthesized = dict(insights)
    action_reports = [dict(report) for report in build_action_reports(synthesized)]
    synthesized["action_items"] = action_reports
    try:
        entity_summary = dict(summarize_entities(synthesized))
        channels = entity_summary.get("channels", [])
        channel_breakdown = [
            {
                "name": str(row.get("name")),
                "mentions": int(row.get("mentions") or 0),
            }
            for row in channels[:5]
            if isinstance(row, Mapping) and row.get("name")
        ]
    except Exception:
        entity_summary = dict(summarize_entities_fallback(synthesized))
        channel_breakdown = []
    synthesized["entity_summary"] = entity_summary
    synthesized["channel_breakdown"] = channel_breakdown
    top_communities: list[str] = []
    seen_communities: set[str] = set()
    sorted_communities = sorted(
        (
            detail
            for detail in communities_detail
            if isinstance(detail, Mapping) and detail.get("name")
        ),
        key=lambda detail: (
            -int(detail.get("mentions") or 0),
            str(detail.get("name") or ""),
        ),
    )
    for detail in sorted_communities:
        name = str(detail.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen_communities:
            continue
        seen_communities.add(key)
        top_communities.append(name)
        if len(top_communities) >= 5:
            break
    if not top_communities:
        for row in channel_breakdown:
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()
            if key in seen_communities:
                continue
            seen_communities.add(key)
            top_communities.append(name)
            if len(top_communities) >= 5:
                break
    synthesized["top_communities"] = top_communities
    battlefield_profiles = build_battlefield_profiles(
        communities_detail,
        list(synthesized.get("pain_points") or []),
        pain_counts_by_community,
        battlefield_limit,
    )
    top_drivers = build_top_drivers(
        list(synthesized.get("pain_points") or []),
        action_reports,
        driver_limit,
    )
    synthesized["battlefield_profiles"] = battlefield_profiles
    synthesized["top_drivers"] = top_drivers
    synthesized["drivers"] = top_drivers
    return InsightSynthesisSummary(
        insights=synthesized,
        action_reports=action_reports,
        entity_summary=entity_summary,
        channel_breakdown=channel_breakdown,
        top_communities=top_communities,
        battlefield_profiles=battlefield_profiles,
        top_drivers=top_drivers,
    )


__all__ = [
    "build_opportunities_payload",
    "build_pain_points_payload",
    "clean_opportunity_copy",
    "finalize_insights_summary",
    "InsightSynthesisSummary",
    "pick_linked_pain_cluster",
]
