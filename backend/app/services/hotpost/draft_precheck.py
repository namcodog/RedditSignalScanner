from __future__ import annotations

import json
import re
from typing import Any


PRECHECK_DECISIONS = {"PASS", "REWRITE", "BLOCK"}


def draft_precheck_json_schema() -> dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "decision": {"type": "STRING", "enum": ["PASS", "REWRITE", "BLOCK"]},
            "reasons": {"type": "ARRAY", "items": {"type": "STRING"}},
            "required_fixes": {"type": "ARRAY", "items": {"type": "STRING"}},
            "risk_flags": {"type": "ARRAY", "items": {"type": "STRING"}},
            "publish_note": {"type": "STRING"},
        },
        "required": [
            "decision",
            "reasons",
            "required_fixes",
            "risk_flags",
            "publish_note",
        ],
    }


def parse_draft_precheck_result(
    payload: dict[str, Any],
    *,
    draft_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = str(payload.get("decision") or "").strip().upper()
    if decision not in PRECHECK_DECISIONS:
        raise ValueError(f"invalid precheck decision: {decision or '-'}")
    reasons = _string_list(payload.get("reasons"))
    required_fixes = _string_list(payload.get("required_fixes"))
    risk_flags = _string_list(payload.get("risk_flags"))
    if decision == "PASS" and draft_payload is not None:
        forced = _forced_rewrite_findings(draft_payload)
        if forced:
            decision = "REWRITE"
            reasons.extend(item["reason"] for item in forced)
            required_fixes.extend(item["fix"] for item in forced)
            risk_flags.extend(item["flag"] for item in forced)
    return {
        "decision": decision,
        "reasons": _unique_strings(reasons),
        "required_fixes": _unique_strings(required_fixes),
        "risk_flags": _unique_strings(risk_flags),
        "publish_note": str(payload.get("publish_note") or "").strip(),
        "should_rewrite": decision == "REWRITE",
        "should_block": decision == "BLOCK",
    }


def build_draft_precheck_messages(
    *, draft_payload: dict[str, Any], semantic_brief: dict[str, Any] | None
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是 Hotpost 人工 review 前的 AI 预检节点。只判断草稿是否被证据支撑，"
                "不要重写正文，不要发布。输出 JSON。"
                "decision 只能是 PASS / REWRITE / BLOCK。"
                "PASS 表示可以进入人工 review；REWRITE 表示字段有问题但可修；"
                "BLOCK 表示证据不支撑或明显不该发。"
                "以下情况不能 PASS，至少 REWRITE："
                "min_test_action 只是“去看原始讨论”或类似跳转提示；"
                "why_test_now / summary / detail 里有半截英文原话、截断引用或没闭合的引用；"
                "continue_signal 把 Please educate、years、old 这类标题废词当观察词。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "draft": draft_payload,
                    "semantic_brief": semantic_brief or {},
                },
                ensure_ascii=False,
                indent=2,
            ),
        },
    ]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _forced_rewrite_findings(draft_payload: dict[str, Any]) -> list[dict[str, str]]:
    detail = draft_payload.get("detail") if isinstance(draft_payload.get("detail"), dict) else {}
    findings: list[dict[str, str]] = []
    min_test_action = str(detail.get("min_test_action") or "").strip()
    if min_test_action in {"去看原始讨论", "查看原始讨论", "看原始讨论"}:
        findings.append(
            {
                "flag": "weak_min_test_action",
                "reason": "min_test_action 只是跳转提示，不是可执行验证动作。",
                "fix": "把 min_test_action 改成用户或卖家能实际检查的一步动作。",
            }
        )
    text = json.dumps(draft_payload, ensure_ascii=False)
    if _has_truncated_quote(text):
        findings.append(
            {
                "flag": "truncated_quote",
                "reason": "草稿里出现半截原话或截断引用。",
                "fix": "删掉半截英文原话，改成完整短摘录或中文转述。",
            }
        )
    continue_signal = str(detail.get("continue_signal") or "").strip()
    if _has_junk_tracking_terms(continue_signal):
        findings.append(
            {
                "flag": "junk_tracking_terms",
                "reason": "continue_signal 把标题废词当成后续观察词。",
                "fix": "改成能代表真实业务变化的观察词或行为信号。",
            }
        )
    return findings


def _has_truncated_quote(value: str) -> bool:
    normalized = " ".join(value.split())
    if "原话里有个关键句" not in normalized:
        return False
    return bool(re.search(r"[A-Za-z][A-Za-z’' ,.:-]{20,}(going to|Ye)", normalized))


def _has_junk_tracking_terms(value: str) -> bool:
    normalized = value.lower()
    junk_terms = ["please educate", "years", "old"]
    return sum(1 for term in junk_terms if term in normalized) >= 2


def _unique_strings(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


__all__ = [
    "build_draft_precheck_messages",
    "draft_precheck_json_schema",
    "parse_draft_precheck_result",
]
