from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


SIGNAL_POLISH_VARIANTS: dict[str, dict[str, str]] = {
    "baseline_polish_v1": {"label": "baseline_polish"},
    "clean_summary_polish_v1": {"label": "clean_summary"},
    "clean_summary_tight_why_now_polish_v1": {"label": "clean_summary_tight_why_now"},
    "clean_summary_growth_pack_polish_v3": {"label": "clean_summary_growth_pack"},
}


_SUMMARY_PREFIX_PATTERNS: tuple[str, ...] = (
    r"^几条[^：。]{0,40}(讨论|帖子|声音|发言)都在(说|讲|抱怨|提到|讨论)(同一件事|同一个坑)?[:：，]?",
    r"^几条[^：。]{0,20}都在(说|讲|抱怨|提到)[:：，]?",
    r"^有人(直说|说得很直|直接说|直接质疑|复盘)[:：，]?",
    r"^另一拨人也在(抱怨|担心|提醒|提到|补了一刀)[:：，]?",
)


def apply_signal_polish_variant(
    output: dict[str, Any],
    *,
    input_bundle: dict[str, Any],
    variant_id: str,
) -> dict[str, Any]:
    polished = deepcopy(output)
    if variant_id == "baseline_polish_v1":
        return polished
    polished["summary_line"] = _clean_summary_restatement(str(polished.get("summary_line") or ""))
    polished["title"] = _soften_title(str(polished.get("title") or ""))
    if variant_id == "clean_summary_growth_pack_polish_v3":
        if str(input_bundle.get("source_scope_id") or "") == "business-growth-ops":
            polished["title"] = _polish_growth_title(polished["title"])
            polished["summary_line"] = _polish_growth_summary(polished["summary_line"])
        return polished
    if variant_id == "clean_summary_tight_why_now_polish_v1":
        polished["why_now"] = _build_compact_why_now(input_bundle)
    return polished


def _clean_summary_restatement(text: str) -> str:
    cleaned = text.strip()
    for pattern in _SUMMARY_PREFIX_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned)
    cleaned = re.sub(r"^(评论区里|帖子里|楼里|讨论里)[，,:：]?", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip("，。 ")
    if cleaned and cleaned[-1] not in "。！？":
        cleaned += "。"
    return cleaned


def _soften_title(text: str) -> str:
    cleaned = text.strip().replace("“", "").replace("”", "").replace("'", "")
    cleaned = cleaned.replace("：", "，")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip("，。 ")


def _polish_growth_title(text: str) -> str:
    polished = text
    replacements = (
        ("被直指", "开始被质疑"),
        ("最糟", "最难让人继续投"),
        ("难以为继", "开始站不住"),
        ("不值得追", "先别急着信"),
        ("值得继续追？", "开始逼人重算这笔账"),
        ("完蛋了", "先扛不住了"),
    )
    for source, target in replacements:
        polished = polished.replace(source, target)
    polished = polished.replace("，值得继续追?", "").replace("，值得继续追？", "")
    return polished.strip("，。 ")


def _polish_growth_summary(text: str) -> str:
    polished = text
    polished = re.sub(r"^这意味着", "", polished)
    polished = polished.replace("大家真正开始重新判断", "大家开始重新判断")
    polished = polished.replace("从业者已开始重新评估其价值", "投放者开始重新算这笔账")
    polished = polished.replace("成为绝对最差预算选择", "预算价值开始被重新怀疑")
    polished = polished.replace("这让从业者重新评估长期价值", "这让从业者开始重新算长期回报")
    polished = re.sub(r"\s+", " ", polished).strip("，。 ")
    if polished and polished[-1] not in "。！？":
        polished += "。"
    return polished


def _build_compact_why_now(bundle: dict[str, Any]) -> str:
    intent_tags = [str(item) for item in (bundle.get("intent_tags") or [])]
    why_now_reason = str(bundle.get("why_now_reason") or "")
    if "替换" in intent_tags or "求推荐" in intent_tags or "求解法 / 求推荐" in " ".join(intent_tags):
        return "这已经不是零散吐槽，开始逼人重新选工具、方案或替代品。"
    if "避坑" in intent_tags:
        return "这波讨论已经从吐槽变成避坑提醒，说明它会直接影响后续判断。"
    if why_now_reason == "recurring_7d":
        return "这事近一周里反复出现，已经不是单个帖子里的偶发抱怨。"
    if why_now_reason == "switch_signal_7d":
        return "这事近一周里还在继续冒头，说明大家开始把它当成需要重新判断的问题。"
    if why_now_reason == "new_threads_24h":
        return "这事这两天又冒出来了，说明它不是已经过去的小插曲。"
    return "这已经不只是顺手一提，开始影响人接下来怎么判断。"


__all__ = ["SIGNAL_POLISH_VARIANTS", "apply_signal_polish_variant"]
