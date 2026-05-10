from __future__ import annotations

import json

from app.schemas.hotpost_card_drafts import ValidationCardDraft, WritingCardDraft
from app.services.hotpost.reddit_guide_prompt_assets import build_reddit_guide_prompt_prefix


def build_signal_prompt(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    banned_patterns: list[str],
    field_contract_prompt: str = "",
) -> list[dict[str, str]]:
    system = (
        build_reddit_guide_prompt_prefix(mode_name="潜力快帖")
        + "\n"
        "只用输入证据，不补背景。"
        "后台词和英文黑话先翻成用户能感知的后果，再必要时补原词。"
        "preview_quote_permalink 从 evidence_quotes 里选。"
        "输出必须是合法 JSON。硬禁词："
        + " / ".join(banned_patterns)
        + field_contract_prompt
    )
    evidence = [
        {
            "text": quote.text,
            "community": quote.community,
            "permalink": quote.permalink,
        }
        for quote in draft.evidence_quotes
    ]
    user = {
        "topic_pack_id": draft.topic_pack_id,
        "current_title": draft.title,
        "stats": {
            "thread_count": draft.thread_count,
            "community_count": draft.community_count,
            "signal_level": draft.signal_level,
            "why_now_reason": draft.why_now_reason,
            "intent_tags": draft.intent_tags,
        },
        "evidence_quotes": evidence,
        "output_schema": {
            "title": "string",
            "summary_line": "string",
            "audience": "string",
            "why_now": "string",
            "preview_quote_permalink": "string",
            "detail": {
                "pain_point": "string",
                "target_user_and_scene": "string",
                "why_test_now": "string",
                "continue_signal": "string",
                "stop_signal": "string",
            },
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False, separators=(",", ":"))},
    ]


def build_hot_prompt(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    banned_patterns: list[str],
    field_contract_prompt: str = "",
) -> list[dict[str, str]]:
    system = (
        build_reddit_guide_prompt_prefix(mode_name="近期爆帖")
        + "\n"
        "只用输入里的 evidence_quotes，不补背景。"
        "preview_quote_permalink 只能从 evidence_quotes 里选。"
        "输出必须是合法 JSON。硬禁词："
        + " / ".join(banned_patterns)
        + field_contract_prompt
    )
    evidence = [
        {"text": quote.text, "community": quote.community, "permalink": quote.permalink}
        for quote in draft.evidence_quotes
    ]
    user = {
        "scope": draft.source_scope_name,
        "stats": {
            "thread_count": draft.thread_count,
            "community_count": draft.community_count,
            "intent_tags": draft.intent_tags,
        },
        "evidence_quotes": evidence,
        "output_schema": {
            "title": "string",
            "summary_line": "string",
            "audience": "string",
            "why_now": "string",
            "preview_quote_permalink": "string",
            "detail": {
                "flashpoint": "string",
                "fight_line": "string",
                "why_test_now": "string",
                "continue_signal": "string",
                "stop_signal": "string",
            },
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False, separators=(",", ":"))},
    ]


def build_breakdown_prompt(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    banned_patterns: list[str],
    field_contract_prompt: str = "",
) -> list[dict[str, str]]:
    system = (
        build_reddit_guide_prompt_prefix(mode_name="跨区热议")
        + "\n"
        "现在要判断这张卡能不能升级成『拆解卡』。"
        "thesis 不能拍脑袋，必须由至少两条原话共同支撑；如果很难再深一层，就写一条更保守、更具体的判断；只有完全没有共同指向时，才让 thesis 为空字符串。"
        "只用输入里的 evidence_quotes，不补背景。"
        "quote_pack 只放真正支撑 thesis 的原话，每条格式：英文原话｜中文翻译｜来源社区。"
        "supporting_quote_permalinks 必须只引用给定 evidence_quotes 中的 permalink。"
        "输出必须是合法 JSON。"
        "禁止使用这些套话："
        + " / ".join(banned_patterns)
        + field_contract_prompt
    )
    evidence = [
        {
            "text": quote.text,
            "community": quote.community,
            "permalink": quote.permalink,
        }
        for quote in draft.evidence_quotes
    ]
    user = {
        "scope": draft.source_scope_name,
        "stats": {
            "thread_count": draft.thread_count,
            "community_count": draft.community_count,
            "intent_tags": draft.intent_tags,
        },
        "current_card": {
            "card_type": draft.card_type,
            "title": draft.title,
            "summary_line": draft.summary_line,
            "audience": draft.audience,
            "why_now": draft.why_now,
        },
        "evidence_quotes": evidence,
        "output_schema": {
            "title": "string",
            "summary_line": "string",
            "audience": "string",
            "why_now": "string",
            "thesis": "string",
            "writing_angle_or_perspective": "string",
            "tension_point_or_why_it_matters": "string",
            "title_hooks": ["string"],
            "quote_pack": ["string"],
            "supporting_quote_permalinks": ["string"],
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False, separators=(",", ":"))},
    ]


__all__ = ["build_breakdown_prompt", "build_hot_prompt", "build_signal_prompt"]
