from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.hotpost.breakdown_eval_set_builder import BREAKDOWN_FAILURE_TAGS

_TAG_GUIDANCE = {
    "weak_thesis": {
        "definition": "thesis 看起来像判断，但只是把几条现象重新拼成一句更抽象的话，没有真正往更深一层推进。",
        "when": "读完 thesis 仍然只是在换种方式复述 signal，没有形成更稳定的解释框架。",
        "not": "正常保守。保守可以成立，但空话式抽象不算成立的 thesis。",
    },
    "quote_pack_not_supporting_claim": {
        "definition": "quote_pack 看起来很多，但并没有真正共同支撑 thesis，或者只是热闹堆砌。",
        "when": "引用之间只是同主题共现，没有形成共同指向；或者 thesis 明显比 quote 说得更重。",
        "not": "引用少。少而准可以 pass，问题在于证据关系没撑住结论。",
    },
    "no_judgment_gain": {
        "definition": "整张拆解卡没有真正给出新判断，只是把多条 signal 汇总得更长。",
        "when": "读完只有“这些帖子都在说类似的事”，没有“原来真正卡在这里”。",
        "not": "简洁。短不等于没判断，空才算。",
    },
    "reddit_restatement": {
        "definition": "正文主要还是在复述 Reddit 讨论，没有把 grouped evidence 压成用户可直接拿走的判断。",
        "when": "summary_line/why_now 的主体像论坛摘要，读完仍然停留在 Reddit 上发生了什么。",
        "not": "短引用锚点。引用可以有，但不能变成正文主体。",
    },
    "why_now_not_actionable": {
        "definition": "why_now 只是在说最近大家都在聊，没有完成拆解层应有的信号读数。",
        "when": "why_now 停在时间句或讨论增多，没有说明为什么这组 grouped discussion 现在不能忽视。",
        "not": "正常的时效说明。问题在于只有时间，没有判断。",
    },
    "audience_not_who_is_talking": {
        "definition": "audience 写成目标 persona，而不是真实在聊这件事的人。",
        "when": "读起来像营销受众画像，而不是 Reddit 里提出问题、抱怨、比较的人群。",
        "not": "适度抽象的人群描述。只要仍然贴着真实发言者，就不算。",
    },
    "stitched_not_coherent": {
        "definition": "这组 signal 被硬拼到一起，看起来相关，但其实不是同一个决策问题。",
        "when": "候选看似同类，真正张力却不同；或 thesis 靠拼接而不是靠共指成立。",
        "not": "多角度但同问题。多个角度共同指向一个判断时可以成立。",
    },
    "reporty_title": {
        "definition": "标题像分析报告、研究摘要或论坛目录，而不是一条有判断张力的拆解句。",
        "when": "标题堆概念、像条目索引，或者把 thesis 写得像学术摘要。",
        "not": "信息密度高。高密度不等于报告腔。",
    },
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_breakdown_review_packet(cases: list[dict[str, Any]], labels: list[dict[str, Any]]) -> str:
    label_map = {item["eval_case_id"]: item for item in labels}
    rows = [
        "# Breakdown Eval Review Packet V1",
        "",
        f"- 样本数：`{len(cases)}`",
        "",
        "## 评审规则",
        "",
        "- 先看 grouped 输入，再看拆解输出。",
        "- 只用 pass/fail，不打 1-5 分。",
        "- 整卡只判断：这张拆解卡有没有成立的更深一层判断。",
        "",
    ]
    for index, case in enumerate(_sorted_cases(cases), start=1):
        input_bundle = case["input_bundle"]
        output = case["baseline_output"]
        detail = output.get("detail") or {}
        label = label_map.get(case["eval_case_id"], {})
        rows.extend(
            [
                f"## Case {index} · `{case['eval_case_id']}`",
                "",
                f"- 来源：`{case['sample_origin']}`",
                f"- scope：`{input_bundle['source_scope_id']}`",
                f"- pack：`{input_bundle.get('topic_pack_id') or 'unknown'}`",
                f"- evidence：`{input_bundle['thread_count']} 帖 / {input_bundle['community_count']} 社区`",
                f"- hypothesis：{input_bundle.get('hypothesis') or '无'}",
                "",
                "### 输入证据",
                "",
                f"- communities：{', '.join(input_bundle.get('source_communities') or ['无'])}",
                f"- candidate_ids：{', '.join(input_bundle.get('candidate_ids') or ['无'])}",
                _quote_block(input_bundle.get('evidence_quotes') or []),
                "",
                "### 当前输出",
                "",
                f"- title：{output.get('title') or ''}",
                f"- summary_line：{output.get('summary_line') or ''}",
                f"- audience：{output.get('audience') or ''}",
                f"- why_now：{output.get('why_now') or ''}",
                f"- thesis：{detail.get('thesis') or ''}",
                f"- tension：{detail.get('tension_point_or_why_it_matters') or ''}",
                _quote_pack_block(detail.get('quote_pack') or []),
                "",
                "### 标注位",
                "",
                f"- overall_pass：`{label.get('overall_pass')}`",
                f"- field_passes：`{label.get('field_passes')}`",
                f"- failure_tags：`{label.get('failure_tags')}`",
                f"- review_notes：{label.get('review_notes') or ''}",
                "",
            ]
        )
    return "\n".join(rows).strip() + "\n"


def build_breakdown_failure_taxonomy(cases: list[dict[str, Any]]) -> str:
    counts = {}
    for case in cases:
        bundle = case["input_bundle"]
        key = (bundle["source_scope_id"], bundle.get("topic_pack_id") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    rows = [
        "# Breakdown Failure Taxonomy V1",
        "",
        "## 使用方式",
        "",
        "- 先读 review packet，再往下归类坏样本。",
        "- 一张拆解卡可以挂多个 failure tag。",
        "- 如果遇到新失败类型，先记到“待新增标签”，不要直接改旧标签定义。",
        "",
        "## 样本覆盖",
        "",
    ]
    for (scope_id, pack_id), count in sorted(counts.items()):
        rows.append(f"- `{scope_id} / {pack_id}`: `{count}`")
    rows.extend(["", "## V1 Failure Tags", ""])
    for tag in BREAKDOWN_FAILURE_TAGS:
        guidance = _TAG_GUIDANCE[tag]
        rows.extend([f"### `{tag}`", "", "- 定义：", "- 何时命中：", "- 不该误判成：", "- 代表样本：", ""])
        rows[-5] = f"- 定义：{guidance['definition']}"
        rows[-4] = f"- 何时命中：{guidance['when']}"
        rows[-3] = f"- 不该误判成：{guidance['not']}"
    rows.extend(["## 待新增标签", "", "- （人工阅读后补）", ""])
    return "\n".join(rows)


def _sorted_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        cases,
        key=lambda item: (
            item["input_bundle"]["source_scope_id"],
            item["input_bundle"].get("topic_pack_id") or "unknown",
            item["sample_origin"],
            item["eval_case_id"],
        ),
    )


def _quote_block(quotes: list[Any]) -> str:
    clipped = []
    for quote in quotes[:4]:
        text = quote["text"] if isinstance(quote, dict) else str(quote)
        community = quote.get("community") if isinstance(quote, dict) else None
        clipped.append(f"  - {community or 'unknown'}: {text}")
    return "\n".join(["- evidence_quotes:"] + clipped if clipped else ["- evidence_quotes: 无"])


def _quote_pack_block(quotes: list[Any]) -> str:
    clipped = [f"  - {str(quote)}" for quote in quotes[:3]]
    return "\n".join(["- quote_pack:"] + clipped if clipped else ["- quote_pack: 无"])


__all__ = ["build_breakdown_failure_taxonomy", "build_breakdown_review_packet", "load_jsonl"]
