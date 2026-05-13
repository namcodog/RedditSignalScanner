from __future__ import annotations


def build_signal_why_now(
    *,
    source_communities: list[str],
    thread_count: int,
    community_count: int,
    intent_tags: list[str],
    why_now_reason: str,
) -> str:
    """Legacy helper for re-polishing old published cards only."""
    community_text = _format_communities(source_communities, community_count)
    intent_clause = _intent_clause(intent_tags)
    if thread_count <= 1:
        if intent_clause:
            return f"{community_text} 这条讨论值得看，因为它把一个真实取舍摆出来了：{intent_clause}。"
        return f"{community_text} 这条讨论已经把一个具体变化摆出来了，值得先看原话。"

    timing_text = _why_now_reason_phrase(why_now_reason, thread_count=thread_count)
    parts = [f"{community_text} 里已经有 {thread_count} 条讨论在指向同一个问题"]
    if timing_text:
        parts.append(timing_text)
    if intent_clause:
        parts.append(intent_clause)
    return _join_sentences(parts)


def build_signal_why_test_now(
    *,
    source_communities: list[str],
    thread_count: int,
    community_count: int,
    intent_tags: list[str],
    why_now_reason: str,
) -> str:
    """Legacy helper for re-polishing old published cards only."""
    community_text = _format_communities(source_communities, community_count)
    intent_clause = _intent_clause(intent_tags)
    if thread_count <= 1:
        if intent_clause:
            return f"{community_text} 这条原话已经把取舍说清楚了：{intent_clause}。"
        return f"{community_text} 这条原话已经把场景、取舍或阻力说清楚了，可以先拿来做判断。"

    timing_text = _why_now_reason_phrase(why_now_reason, thread_count=thread_count)
    parts = [f"{community_text} 里已经有 {thread_count} 条讨论反复提到这件事"]
    if timing_text:
        parts.append(timing_text)
    if intent_clause:
        parts.append(intent_clause)
    return _join_sentences(parts)


def build_continue_signal(intent_tags: list[str]) -> str:
    """Legacy helper for re-polishing old published cards only."""
    clauses: list[str] = ["如果接下来在更多社区里还出现同样抱怨"]
    if _has_intent(intent_tags, "求替代", "迁移 / 切换意向"):
        clauses.append("而且继续有用户点名找替代")
    elif _has_intent(intent_tags, "求推荐", "求推荐 / 求解法"):
        clauses.append("而且继续有用户直接问推荐")
    elif _has_intent(intent_tags, "避坑"):
        clauses.append("而且避坑情绪越来越重")
    return "，".join(clauses) + "，就继续关注。"


def build_stop_signal() -> str:
    """Legacy helper for re-polishing old published cards only."""
    return "如果后面只剩零散吐槽，没有新的具体场景或后续追问，暂时不用太在意。"


def _format_communities(communities: list[str], community_count: int) -> str:
    cleaned = [str(item).strip() for item in communities if str(item).strip()]
    if not cleaned:
        return f"{community_count}个社区"
    if len(cleaned) <= 3:
        return "、".join(cleaned)
    shown = "、".join(cleaned[:3])
    return f"{shown}等{max(community_count, len(cleaned))}个社区"


def _why_now_reason_phrase(why_now_reason: str, *, thread_count: int) -> str:
    if thread_count <= 1:
        return ""
    if why_now_reason == "new_threads_24h":
        return "这 24 小时里又冒出来"
    if why_now_reason == "switch_signal_7d":
        return "近 7 天里还在继续冒头"
    if why_now_reason == "recurring_7d":
        return "近 7 天里反复出现"
    return ""


def _intent_clause(intent_tags: list[str]) -> str:
    clauses: list[str] = []
    if _has_intent(intent_tags, "求替代", "迁移 / 切换意向", "替换"):
        clauses.append("已经有用户开始找替代")
    if _has_intent(intent_tags, "求推荐", "求推荐 / 求解法", "求解法 / 求推荐"):
        clauses.append("已经有用户直接问推荐和方案")
    if _has_intent(intent_tags, "明确阻塞 / 吐槽到影响行动", "明确阻塞"):
        clauses.append("而且这事已经卡到手头工作")
    if _has_intent(intent_tags, "避坑"):
        clauses.append("避坑情绪也很重")
    if _has_intent(intent_tags, "反常识争议 / 共识变化"):
        clauses.append("大家对这件事的分歧也在变大")
    if _has_intent(intent_tags, "值得警惕"):
        clauses.append("已经有用户把它当成风险信号")
    if _has_intent(intent_tags, "先看权限和追责"):
        clauses.append("讨论已经往权限和追责上追")
    if _has_intent(intent_tags, "先看经营基本面"):
        clauses.append("讨论已经开始追问这门生意算不算得过来")
    if _has_intent(intent_tags, "值得写"):
        clauses.append("这已经不只是顺手一吐槽")
    if not clauses and _has_intent(intent_tags, "趋势变化"):
        clauses.append("用户开始重新算这件事还值不值")
    if not clauses:
        return ""
    return "，".join(clauses)


def _has_intent(intent_tags: list[str], *needles: str) -> bool:
    haystack = " ".join(intent_tags)
    return any(needle in haystack for needle in needles)


def _join_sentences(parts: list[str]) -> str:
    cleaned = [part.strip("，。 ") for part in parts if part and part.strip("，。 ")]
    if not cleaned:
        return ""
    head, *tail = cleaned
    if not tail:
        return head + "。"
    return head + "，" + "，".join(tail) + "。"


__all__ = [
    "build_continue_signal",
    "build_signal_why_now",
    "build_signal_why_test_now",
    "build_stop_signal",
]
