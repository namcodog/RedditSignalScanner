from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.hotpost.signal_eval_set_builder import SIGNAL_FAILURE_TAGS


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_signal_review_packet(cases: list[dict[str, Any]], labels: list[dict[str, Any]]) -> str:
    label_map = {item["eval_case_id"]: item for item in labels}
    rows = ["# Signal Eval Review Packet V1", "", f"- 样本数：`{len(cases)}`", "", "## 评审规则", "", "- 先看输入证据，再看输出卡片。", "- 只用 pass/fail，不打 1-5 分。", "- 整卡只判断：有没有完成判断前移。", ""]
    for index, case in enumerate(_sorted_cases(cases), start=1):
        input_bundle = case["input_bundle"]
        output = case["baseline_output"]
        label = label_map.get(case["eval_case_id"], {})
        rows.extend(
            [
                f"## Case {index} · `{case['eval_case_id']}`",
                "",
                f"- 来源：`{case['sample_origin']}`",
                f"- scope：`{input_bundle['source_scope_id']}`",
                f"- pack：`{input_bundle.get('topic_pack_id') or 'unknown'}`",
                f"- signal：`{input_bundle.get('signal_level') or 'unknown'}`",
                f"- intent：`{', '.join(input_bundle.get('intent_tags') or ['无'])}`",
                f"- evidence：`{input_bundle['thread_count']} 帖 / {input_bundle['community_count']} 社区 / {input_bundle['quote_count']} quote`",
                "",
                "### 输入证据",
                "",
                f"- communities：{', '.join(input_bundle.get('source_communities') or ['无'])}",
                _quote_block(input_bundle.get("evidence_quotes") or []),
                "",
                "### 当前输出",
                "",
                f"- title：{output.get('title') or ''}",
                f"- summary_line：{output.get('summary_line') or ''}",
                f"- audience：{output.get('audience') or ''}",
                f"- why_now：{output.get('why_now') or ''}",
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


def build_signal_failure_taxonomy(cases: list[dict[str, Any]]) -> str:
    counts = {}
    for case in cases:
        bundle = case["input_bundle"]
        key = (bundle["source_scope_id"], bundle.get("topic_pack_id") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    rows = [
        "# Signal Failure Taxonomy V1",
        "",
        "## 使用方式",
        "",
        "- 先读 review packet，再往下归类坏样本。",
        "- 一张卡可以挂多个 failure tag。",
        "- 如果遇到新失败类型，先记到“待新增标签”，不要直接改旧标签定义。",
        "",
        "## 样本覆盖",
        "",
    ]
    for (scope_id, pack_id), count in sorted(counts.items()):
        rows.append(f"- `{scope_id} / {pack_id}`: `{count}`")
    rows.extend(["", "## V1 Failure Tags", ""])
    for tag in SIGNAL_FAILURE_TAGS:
        rows.extend(
            [
                f"### `{tag}`",
                "",
                "- 定义：",
                "- 何时命中：",
                "- 不该误判成：",
                "- 代表样本：",
                "",
            ]
        )
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
    for quote in quotes[:3]:
        text = quote["text"] if isinstance(quote, dict) else str(quote)
        community = quote.get("community") if isinstance(quote, dict) else None
        clipped.append(f"  - {community or 'unknown'}: {text}")
    return "\n".join(["- evidence_quotes:"] + clipped if clipped else ["- evidence_quotes: 无"])


__all__ = ["build_signal_failure_taxonomy", "build_signal_review_packet", "load_jsonl"]
