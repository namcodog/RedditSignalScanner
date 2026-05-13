from __future__ import annotations

from typing import Optional, Any

from app.schemas.hotpost_card_drafts import ValidationCardDraft
from app.schemas.hotpost_clues import QuotePreview, ValidationDetail
from app.services.hotpost.card_content_generator import (
    _apply_validation_content,
    _default_client_factory,
    _generate_json,
)
from app.services.hotpost.legacy_signal_copy_builder import (
    _format_communities,
    _intent_clause,
    _join_sentences,
    _why_now_reason_phrase,
)
from app.services.hotpost.card_content_prompts import build_signal_prompt
from app.services.hotpost.card_content_generation_contract import build_generation_field_contract_prompt
from app.services.hotpost.semantic_readout import finalize_signal_readout, semantic_prompt_extra
from app.services.hotpost.signal_skill_variant_policy import (
    SIGNAL_SKILL_VARIANTS,
    all_banned_patterns,
    clean_experiment_quotes,
    clean_summary_noise,
    time_window_from_reason,
)


def build_eval_signal_draft(case: dict[str, Any], *, variant_id: str) -> ValidationCardDraft:
    bundle = case["input_bundle"]
    quotes = [QuotePreview.model_validate(item) for item in bundle["evidence_quotes"]]
    quotes = clean_experiment_quotes(quotes, variant_id=variant_id)
    top_community = str((bundle.get("source_communities") or ["r/unknown"])[0]).replace("r/", "", 1)
    source_link = quotes[0].permalink if quotes else ""
    return ValidationCardDraft(
        draft_id=f"{case['eval_case_id']}-{variant_id}",
        candidate_id=case["eval_case_id"],
        candidate_ids=[case["eval_case_id"]],
        card_id=f"{case['eval_case_id']}-{variant_id}",
        signal_id=f"{case['eval_case_id']}-{variant_id}",
        card_type="validate",
        category_id="validate",
        topic_pack_id=bundle.get("topic_pack_id"),
        title=case["baseline_output"]["title"],
        source_scope_id=bundle["source_scope_id"],
        source_scope_name=bundle["source_scope_name"],
        matched_subreddit=top_community,
        post_id=case["eval_case_id"],
        source_event_at=None,
        score=0,
        num_comments=0,
        time_window=time_window_from_reason(str(bundle.get("why_now_reason") or "")),
        signal_level=bundle["signal_level"],
        why_now_reason=bundle["why_now_reason"],
        thread_count=int(bundle["thread_count"]),
        community_count=int(bundle["community_count"]),
        quote_count=int(bundle["quote_count"]),
        intent_tags=[str(item) for item in bundle.get("intent_tags") or []],
        evidence_quotes=quotes,
        summary_line="",
        audience="",
        why_now="",
        source_link=source_link,
        source_links=[source_link] if source_link else [],
        source_communities=[str(item) for item in bundle.get("source_communities") or []],
        draft_status="draft",
        draft_note=f"signal skill experiment {variant_id}",
        detail=ValidationDetail(
            pain_point="待生成",
            target_user_and_scene="待生成",
            why_test_now="待生成",
            continue_signal="待生成",
            stop_signal="待生成",
        ),
    )


def build_experiment_messages(
    draft: ValidationCardDraft,
    *,
    variant_id: str,
    banned_patterns: list[str],
    rules:Optional[ dict[str, Any]] = None,
) -> list[dict[str, str]]:
    messages = build_signal_prompt(
        draft,
        banned_patterns=banned_patterns,
        field_contract_prompt=build_generation_field_contract_prompt(rules) if rules is not None else "",
    )
    extra = (
        semantic_prompt_extra(rules=rules, lane="signal", topic_pack_id=draft.topic_pack_id)
        if rules is not None
        else ""
    )
    if not extra:
        return messages
    messages[0] = {**messages[0], "content": messages[0]["content"] + extra}
    return messages


async def run_signal_skill_variant(
    case: dict[str, Any],
    *,
    variant_id: str,
    model: str,
    timeout: float,
    rules: dict[str, Any],
    client_factory:Optional[ Any] = None,
) -> dict[str, Any]:
    draft = build_eval_signal_draft(case, variant_id=variant_id)
    messages = build_experiment_messages(
        draft,
        variant_id=variant_id,
        banned_patterns=all_banned_patterns(rules),
        rules=rules,
    )
    payload = await _generate_json(
        model=model,
        timeout=timeout,
        messages=messages,
        client_factory=client_factory or _default_client_factory,
    )
    generated = _apply_validation_content(draft, payload, rules)
    why_now_mode = SIGNAL_SKILL_VARIANTS[variant_id]["why_now_mode"]
    if why_now_mode == "tight":
        why_now = _build_tight_why_now(generated.source_communities, generated.thread_count, generated.intent_tags, generated.why_now_reason)
        generated = generated.model_copy(
            update={
                "why_now": why_now,
            }
        )
    if why_now_mode == "pack_paid_econ":
        why_now = _build_paid_econ_why_now(generated.thread_count, generated.intent_tags)
        generated = generated.model_copy(
            update={
                "why_now": why_now,
            }
        )
    if why_now_mode == "pack_paid_econ_signal":
        why_now = _build_paid_econ_signal_why_now(generated.intent_tags)
        generated = generated.model_copy(
            update={
                "why_now": why_now,
            }
        )
    if why_now_mode == "pack_tools_efficiency":
        why_now = _build_tools_efficiency_why_now(generated.thread_count, generated.intent_tags)
        generated = generated.model_copy(
            update={
                "why_now": why_now,
            }
        )
    generated = finalize_signal_readout(generated, source_draft=draft, rules=rules)
    return {
        "eval_case_id": case["eval_case_id"],
        "variant_id": variant_id,
        "input_bundle": case["input_bundle"],
        "baseline_output": {
            "title": clean_summary_noise(generated.title),
            "summary_line": clean_summary_noise(generated.summary_line),
            "audience": generated.audience,
            "why_now": generated.why_now,
            "detail": generated.detail.model_dump(mode="json"),
        },
    }


def _build_tight_why_now(
    communities: list[str],
    thread_count: int,
    intent_tags: list[str],
    why_now_reason: str,
) -> str:
    community_text = _format_communities(communities, len(communities))
    timing = _why_now_reason_phrase(why_now_reason, thread_count=thread_count)
    intent = _intent_clause(intent_tags)
    head = f"{community_text}里这事已经不只是随口一提"
    if intent:
        return _join_sentences([head, timing, intent])
    return _join_sentences([head, timing, f"现在能看到{thread_count}个相关帖子"])


def _build_paid_econ_why_now(thread_count: int, intent_tags: list[str]) -> str:
    intent = _intent_clause(intent_tags)
    tail = "这已经碰到预算、自动化和归因判断，不只是泛营销吐槽。"
    if intent:
        return _join_sentences([f"这波讨论里已经直接出现{thread_count}个相关帖子。", intent, tail])
    return _join_sentences([f"这波讨论里已经直接出现{thread_count}个相关帖子。", tail])


def _build_paid_econ_signal_why_now(intent_tags: list[str]) -> str:
    if "替换" in intent_tags or "求推荐" in intent_tags:
        return "讨论已经从排查异常转向追问该改哪种目标、回传或操作方案，说明这会直接改投放动作。"
    if "避坑" in intent_tags:
        return "讨论重点已经从‘哪里报错了’转向‘这类设置以后怎么避坑’，说明问题会持续影响投放判断。"
    return "这已经不只是后台异常说明，开始影响投手怎么设目标、回传信号和判断预算。"


def _build_tools_efficiency_why_now(thread_count: int, intent_tags: list[str]) -> str:
    intent = _intent_clause(intent_tags)
    tail = "这已经不是单个工具技巧讨论，开始逼人重新整理工具栈和上下文流转。"
    if intent:
        return _join_sentences([f"这波讨论里已经冒出{thread_count}个相关帖子。", intent, tail])
    return _join_sentences([f"这波讨论里已经冒出{thread_count}个相关帖子。", tail])

__all__ = [
    "SIGNAL_SKILL_VARIANTS",
    "build_eval_signal_draft",
    "build_experiment_messages",
    "run_signal_skill_variant",
]
