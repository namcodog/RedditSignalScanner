from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from difflib import SequenceMatcher
import json
import logging
import os
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Optional, Any, Callable, Iterator, cast

import yaml

from app.services.hotpost.card_content_llm_router import (
    build_card_content_client,
    normalize_card_content_llm_profiles,
    resolve_production_card_content_llm_profile,
    resolve_card_content_model_route,
)
from app.services.hotpost.card_content_title_v13 import (
    build_title_independence_repair_messages,
    find_v13_title_issues,
    merge_title_repair,
)
from app.services.llm.clients.openai_client import OpenAIChatClient
from app.schemas.hotpost_card_drafts import ValidationCardDraft, WritingCardDraft
from app.schemas.hotpost_clues import QuotePreview, WritingDetail
from app.schemas.hotpost_validate_details import build_validation_detail
from app.services.hotpost.card_content_rules_config import load_card_content_rules
from app.services.hotpost.card_content_polish import polish_generated_text
from app.services.hotpost.card_content_generation_contract import (
    build_generation_field_contract_prompt,
)
from app.services.hotpost.card_content_prompts import (
    build_breakdown_prompt,
    build_hot_prompt,
    build_signal_prompt,
)
from app.services.hotpost.card_draft_builder import build_published_card
from app.services.hotpost.card_payload_store import (
    load_candidates,
    merge_published_cards,
)
from app.services.hotpost.semantic_readout import (
    finalize_validation_readout,
    semantic_prompt_extra,
)
from app.services.hotpost.signal_input_quality import assess_signal_draft_input_quality
from app.services.hotpost.signal_skill_variant_policy import (
    clean_experiment_quotes,
    production_signal_variant,
)


_HOTPOST_CONFIG_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "hotpost_quality.yaml"
)
_SEMANTIC_BRIEF_MAX_QUOTES = 3
_SEMANTIC_BRIEF_MAX_QUOTE_CHARS = 240

logger = logging.getLogger(__name__)


LLMClientFactory = Callable[[str, float], Any]
_GENERATION_SUB_STAGES: ContextVar[list[dict[str, Any]] | None] = ContextVar(
    "hotpost_generation_sub_stages",
    default=None,
)


class HotpostLLMJsonError(ValueError):
    def __init__(self, error_type: str, message: str) -> None:
        self.error_type = error_type
        super().__init__(f"{error_type}: {message}")


class HotpostLLMStageTimeout(TimeoutError):
    def __init__(self, stage: str, model: str, timeout: float) -> None:
        self.error_type = "stage_timeout"
        super().__init__(f"{stage} timed out after {timeout:.2f}s for model {model}")


@contextmanager
def collect_generation_sub_stages() -> Iterator[list[dict[str, Any]]]:
    stages: list[dict[str, Any]] = []
    token = _GENERATION_SUB_STAGES.set(stages)
    try:
        yield stages
    finally:
        _GENERATION_SUB_STAGES.reset(token)


def generation_error_type(exc: BaseException) -> str:
    error_type = getattr(exc, "error_type", "")
    if isinstance(error_type, str) and error_type:
        return error_type
    status_code = getattr(exc, "status_code", None)
    if status_code == 503 or "503" in str(exc):
        return "provider_503"
    if isinstance(exc, TimeoutError):
        return "stage_timeout"
    return exc.__class__.__name__


def _default_client_factory(model: str, timeout: float) -> Any:
    return build_card_content_client(model, timeout=timeout)


@lru_cache(maxsize=1)
def load_card_content_models() -> dict[str, Any]:
    payload = yaml.safe_load(_HOTPOST_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    routing = payload.get("llm_routing") or {}
    fast_model = str(
        os.getenv("HOTPOST_FAST_MODEL") or routing.get("fast_model") or ""
    ).strip()
    reasoning_model = str(
        os.getenv("HOTPOST_REASONING_MODEL") or routing.get("reasoning_model") or ""
    ).strip()
    if not fast_model or not reasoning_model:
        raise ValueError("hotpost_quality.yaml missing llm routing models")
    reasoning_enabled_raw = os.getenv("HOTPOST_REASONING_ENABLED")
    reasoning_enabled = (
        reasoning_enabled_raw.strip().lower() not in {"0", "false", "no", "off"}
        if reasoning_enabled_raw is not None
        else bool(routing.get("reasoning_enabled", True))
    )
    fast_model_pack_overrides = routing.get("fast_model_pack_overrides") or {}
    if not isinstance(fast_model_pack_overrides, dict):
        raise ValueError("hotpost_quality.yaml fast_model_pack_overrides is invalid")
    fast_model_lane_overrides = routing.get("fast_model_lane_overrides") or {}
    if not isinstance(fast_model_lane_overrides, dict):
        raise ValueError("hotpost_quality.yaml fast_model_lane_overrides is invalid")
    route_profiles = normalize_card_content_llm_profiles(routing.get("profiles"))
    production_profile_override = os.getenv("HOTPOST_CARD_CONTENT_PROFILE_ID")
    if production_profile_override is not None:
        normalized_override = production_profile_override.strip()
        production_profile_id = (
            ""
            if normalized_override.lower() in {"0", "false", "no", "none", "off"}
            else normalized_override
        )
    else:
        production_profile_id = str(routing.get("production_profile_id") or "").strip()
    normalized_pack_overrides: dict[str, dict[str, Any]] = {}
    for pack_id, raw in fast_model_pack_overrides.items():
        if not isinstance(raw, dict):
            continue
        model = str(raw.get("model") or "").strip()
        if not model:
            continue
        timeout_seconds = raw.get("timeout_seconds")
        normalized_pack_overrides[str(pack_id).strip()] = {
            "model": model,
            "timeout_seconds": float(timeout_seconds)
            if timeout_seconds is not None
            else None,
        }
    normalized_lane_overrides: dict[str, dict[str, Any]] = {}
    for lane_name, raw in fast_model_lane_overrides.items():
        if not isinstance(raw, dict):
            continue
        model = str(raw.get("model") or "").strip()
        if not model:
            continue
        timeout_seconds = raw.get("timeout_seconds")
        normalized_lane_overrides[str(lane_name).strip()] = {
            "model": model,
            "timeout_seconds": float(timeout_seconds)
            if timeout_seconds is not None
            else None,
        }
    return {
        "fast_model": fast_model,
        "reasoning_model": reasoning_model,
        "reasoning_enabled": reasoning_enabled,
        "fast_model_pack_overrides": normalized_pack_overrides,
        "fast_model_lane_overrides": normalized_lane_overrides,
        "route_profiles": route_profiles,
        "production_profile_id": production_profile_id,
    }


async def generate_card_content(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    client_factory: LLMClientFactory = _default_client_factory,
    allow_breakdown: bool = True,
) -> ValidationCardDraft | WritingCardDraft:
    if isinstance(draft, ValidationCardDraft) and draft.lane != "hot":
        quality = assess_signal_draft_input_quality(draft)
        if quality["should_block"]:
            reasons = ", ".join(quality["reasons"])
            raise ValueError(f"Signal input quality gate blocked draft: {reasons}")
    rules = load_card_content_rules()
    precheck_timeout = _pipeline_timeout(
        rules, "precheck_seconds", float(rules["timeouts"]["signal_seconds"])
    )
    models = load_card_content_models()
    variant_id = production_signal_variant(_draft_topic_pack_id(draft), rules=rules)
    topic_pack_id = _draft_topic_pack_id(draft)
    signal_prompt_draft = draft
    if variant_id and isinstance(draft, ValidationCardDraft):
        signal_prompt_draft = draft.model_copy(
            update={
                "evidence_quotes": clean_experiment_quotes(
                    draft.evidence_quotes, variant_id=variant_id
                )
            }
        )
    prompt_builder = (
        build_hot_prompt
        if isinstance(draft, ValidationCardDraft) and draft.lane == "hot"
        else build_signal_prompt
    )
    signal_messages = prompt_builder(
        signal_prompt_draft,
        banned_patterns=_all_banned_patterns(rules),
        field_contract_prompt=build_generation_field_contract_prompt(rules),
    )
    extra_instruction = semantic_prompt_extra(
        rules=rules,
        lane="hot"
        if isinstance(draft, ValidationCardDraft) and draft.lane == "hot"
        else "signal",
        topic_pack_id=topic_pack_id,
    )
    if extra_instruction:
        signal_messages[0] = {
            **signal_messages[0],
            "content": signal_messages[0]["content"] + extra_instruction,
        }
    semantic_brief: dict[str, Any] | None = None
    production_profile = resolve_production_card_content_llm_profile(models=models)
    if production_profile is not None:
        semantic_brief = await _generate_profile_semantic_brief(
            draft,
            model=str(production_profile["semantic_model"]),
            timeout=_pipeline_timeout(rules, "semantic_brief_seconds", 90.0),
            client_factory=client_factory,
        )
        signal_messages = _with_profile_semantic_brief(
            signal_messages, semantic_brief=semantic_brief
        )
        signal_model = str(production_profile["writer_model"])
        signal_timeout = _pipeline_timeout(
            rules, "writer_seconds", float(rules["timeouts"]["signal_seconds"])
        )
    else:
        signal_model, signal_timeout = resolve_card_content_model_route(
            models=models,
            topic_pack_id=topic_pack_id,
            lane=getattr(draft, "lane", None),
            default_timeout=float(rules["timeouts"]["signal_seconds"]),
        )
    signal_payload = await _generate_json(
        model=signal_model,
        timeout=signal_timeout,
        messages=signal_messages,
        client_factory=client_factory,
        max_tokens=_max_tokens(rules, "signal", default=2200),
        response_schema=_card_content_json_schema_for_draft(draft),
    )
    if production_profile is not None and semantic_brief is not None:
        signal_payload = await _repair_v13_title_if_needed(
            signal_payload,
            semantic_brief=semantic_brief,
            semantic_model=str(production_profile["semantic_model"]),
            writer_model=signal_model,
            timeout=_pipeline_timeout(rules, "title_repair_seconds", signal_timeout),
            client_factory=client_factory,
        )
    try:
        signal_draft = _apply_validation_content(draft, signal_payload, rules)
    except ValueError as exc:
        signal_payload = await _regenerate_json_for_validation_error(
            model=signal_model,
            timeout=signal_timeout,
            messages=signal_messages,
            client_factory=client_factory,
            max_tokens=_max_tokens(rules, "signal", default=2200),
            error=exc,
            response_schema=_card_content_json_schema_for_draft(draft),
        )
        signal_draft = _apply_validation_content(draft, signal_payload, rules)
    signal_draft = finalize_validation_readout(
        signal_draft, source_draft=draft, rules=rules
    )
    if not allow_breakdown or not _can_attempt_breakdown(signal_draft, models):
        return await _attach_draft_precheck_result(
            signal_draft,
            semantic_brief=semantic_brief,
            production_profile=production_profile,
            model=signal_model,
            timeout=precheck_timeout,
            client_factory=client_factory,
        )
    breakdown_model = _breakdown_content_model(
        models=models, production_profile=production_profile
    )
    breakdown_messages = build_breakdown_prompt(
        signal_draft,
        banned_patterns=_all_banned_patterns(rules),
        field_contract_prompt=build_generation_field_contract_prompt(rules),
    )
    if production_profile is not None and semantic_brief is not None:
        breakdown_messages = _with_profile_semantic_brief(
            breakdown_messages, semantic_brief=semantic_brief
        )
    breakdown_schema = _breakdown_json_schema()
    breakdown_payload = await _generate_json(
        model=breakdown_model,
        timeout=float(rules["timeouts"]["breakdown_seconds"]),
        messages=breakdown_messages,
        client_factory=client_factory,
        max_tokens=_max_tokens(rules, "breakdown", default=1800),
        response_schema=breakdown_schema,
    )
    if not should_be_breakdown(signal_draft, breakdown_payload):
        return await _attach_draft_precheck_result(
            signal_draft,
            semantic_brief=semantic_brief,
            production_profile=production_profile,
            model=signal_model,
            timeout=precheck_timeout,
            client_factory=client_factory,
        )
    try:
        final_draft = _apply_breakdown_content(signal_draft, breakdown_payload, rules)
    except ValueError as exc:
        breakdown_payload = await _regenerate_json_for_validation_error(
            model=breakdown_model,
            timeout=float(rules["timeouts"]["breakdown_seconds"]),
            messages=breakdown_messages,
            client_factory=client_factory,
            max_tokens=_max_tokens(rules, "breakdown", default=1800),
            error=exc,
            response_schema=breakdown_schema,
        )
        if not should_be_breakdown(signal_draft, breakdown_payload):
            return await _attach_draft_precheck_result(
                signal_draft,
                semantic_brief=semantic_brief,
                production_profile=production_profile,
                model=signal_model,
                timeout=precheck_timeout,
                client_factory=client_factory,
            )
        final_draft = _apply_breakdown_content(signal_draft, breakdown_payload, rules)
    return await _attach_draft_precheck_result(
        final_draft,
        semantic_brief=semantic_brief,
        production_profile=production_profile,
        model=signal_model,
        timeout=precheck_timeout,
        client_factory=client_factory,
    )


async def refresh_breakdown_content(
    draft: WritingCardDraft,
    *,
    client_factory: LLMClientFactory = _default_client_factory,
) -> WritingCardDraft:
    rules = load_card_content_rules()
    models = load_card_content_models()
    production_profile = resolve_production_card_content_llm_profile(models=models)
    breakdown_model = _breakdown_content_model(
        models=models, production_profile=production_profile
    )
    breakdown_messages = build_breakdown_prompt(
        draft,
        banned_patterns=_all_banned_patterns(rules),
        field_contract_prompt=build_generation_field_contract_prompt(rules),
    )
    breakdown_schema = _breakdown_json_schema()
    breakdown_payload = await _generate_json(
        model=breakdown_model,
        timeout=float(rules["timeouts"]["breakdown_seconds"]),
        messages=breakdown_messages,
        client_factory=client_factory,
        max_tokens=_max_tokens(rules, "breakdown", default=1800),
        response_schema=breakdown_schema,
    )
    try:
        return _apply_breakdown_content(draft, breakdown_payload, rules)
    except ValueError as exc:
        breakdown_payload = await _regenerate_json_for_validation_error(
            model=breakdown_model,
            timeout=float(rules["timeouts"]["breakdown_seconds"]),
            messages=breakdown_messages,
            client_factory=client_factory,
            max_tokens=_max_tokens(rules, "breakdown", default=1800),
            error=exc,
            response_schema=breakdown_schema,
        )
        return _apply_breakdown_content(draft, breakdown_payload, rules)


async def _generate_profile_semantic_brief(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    model: str,
    client_factory: LLMClientFactory,
    timeout: float = 90.0,
) -> dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": (
                "你是 Hotpost 出卡前的语义理解层。你的输出不是正文，而是给后续中文 writer/reasoning model 使用的判断 brief。"
                "只根据输入证据判断，不新增事实，不补行业背景。"
                "输出 JSON，用短中文拆清主体、场景、证据、张力、时间窗口、lane-specific 判断和不能放大的边界。"
                "evidence_basis 每条必须是对象，写清 claim、community、quote_text、permalink；证据不足时在 claim 写“不足以证明”。"
                "lane_specific 里按 hot / signal / breakdown 分别给判断；不适用的字段写“不适用”。"
                "uncertainty 要写 confidence、missing_evidence、weak_points、single_thread_risk。"
                "avoid_claims 写出后续模型绝对不能扩写的结论。"
                "confidence_level 只能是 high / medium / low。"
                "publish_risk 只能是 pass / needs_human_review / block；证据弱、单帖风险高、泛建议时不要写 pass。"
                "claim_type 必须选择最贴近的一个；如果只是泛创业建议，写 generic_advice。"
                "evidence_strength 要判断 quote 是否真支撑主张、是否单帖、是否有具体动作、是否有可量化结果。"
                "writer_constraints 负责告诉后续 writer 必须降调和不能写什么。"
                "所有字符串用短句，每个字段不超过 80 个中文字；evidence_basis 最多 3 条，quote_text 只写短摘录。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                _semantic_brief_input(draft), ensure_ascii=False, indent=2
            ),
        },
    ]
    return await _generate_json(
        model=model,
        timeout=timeout,
        messages=messages,
        client_factory=client_factory,
        max_tokens=2800,
        response_schema=_semantic_brief_json_schema(),
        trace_id=draft.draft_id,
        stage="semantic_brief",
    )


def _pipeline_timeout(rules: dict[str, Any], key: str, default: float) -> float:
    pipeline = rules.get("pipeline") or {}
    if not isinstance(pipeline, dict):
        return default
    value = pipeline.get(key)
    return float(value) if value is not None else default


async def _generate_draft_precheck(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    semantic_brief: dict[str, Any],
    model: str,
    timeout: float,
    client_factory: LLMClientFactory,
) -> dict[str, Any]:
    from app.services.hotpost.draft_precheck import (
        build_draft_precheck_messages,
        draft_precheck_json_schema,
        parse_draft_precheck_result,
    )

    payload = await _generate_json(
        model=model,
        timeout=timeout,
        messages=build_draft_precheck_messages(
            draft_payload=draft.model_dump(mode="json"),
            semantic_brief=semantic_brief,
        ),
        client_factory=client_factory,
        max_tokens=1200,
        response_schema=draft_precheck_json_schema(),
        trace_id=draft.draft_id,
        stage="draft_precheck",
    )
    return parse_draft_precheck_result(
        payload,
        draft_payload=draft.model_dump(mode="json"),
    )


async def _attach_draft_precheck_result(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    semantic_brief: dict[str, Any] | None,
    production_profile: dict[str, Any] | None,
    model: str,
    timeout: float,
    client_factory: LLMClientFactory,
) -> ValidationCardDraft | WritingCardDraft:
    if production_profile is None or semantic_brief is None:
        return draft
    precheck_result = await _generate_draft_precheck_report(
        draft,
        semantic_brief=semantic_brief,
        model=model,
        timeout=timeout,
        client_factory=client_factory,
    )
    object.__setattr__(draft, "_hotpost_precheck_result", precheck_result)
    return draft


async def _generate_draft_precheck_report(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    semantic_brief: dict[str, Any],
    model: str,
    timeout: float,
    client_factory: LLMClientFactory,
) -> dict[str, Any]:
    try:
        return await _generate_draft_precheck(
            draft,
            semantic_brief=semantic_brief,
            model=model,
            timeout=timeout,
            client_factory=client_factory,
        )
    except Exception as exc:
        error_type = generation_error_type(exc)
        logger.warning(
            "Hotpost draft precheck failed draft_id=%s model=%s error=%s",
            draft.draft_id,
            model,
            str(exc)[:240],
        )
        return {
            "decision": "REWRITE",
            "reasons": ["AI 预检节点失败，不能视为通过。"],
            "required_fixes": ["人工核对标题、摘要和 detail 是否被原始证据支撑。"],
            "risk_flags": ["precheck_error", error_type],
            "publish_note": "AI 预检失败，进入人工 review 时必须重新核对证据。",
            "should_rewrite": True,
            "should_block": False,
        }


def _semantic_brief_input(
    draft: ValidationCardDraft | WritingCardDraft,
) -> dict[str, Any]:
    return {
        "card_id": draft.draft_id,
        "lane": getattr(draft, "lane", ""),
        "card_type": draft.card_type,
        "topic_pack_id": _draft_topic_pack_id(draft),
        "candidate_title": draft.title,
        "summary_line": draft.summary_line,
        "audience": draft.audience,
        "why_now": draft.why_now,
        "evidence_quotes": [
            _semantic_brief_quote_payload(quote)
            for quote in draft.evidence_quotes[:_SEMANTIC_BRIEF_MAX_QUOTES]
        ],
    }


def _semantic_brief_quote_payload(quote: QuotePreview) -> dict[str, str]:
    return {
        "text": _clip_semantic_brief_text(str(quote.text or "")),
        "community": quote.community,
        "permalink": quote.permalink,
    }


def _clip_semantic_brief_text(value: str) -> str:
    text = " ".join(value.split())
    if len(text) <= _SEMANTIC_BRIEF_MAX_QUOTE_CHARS:
        return text
    return text[: _SEMANTIC_BRIEF_MAX_QUOTE_CHARS - 1].rstrip() + "…"


def _with_profile_semantic_brief(
    messages: list[dict[str, str]],
    *,
    semantic_brief: dict[str, Any],
) -> list[dict[str, str]]:
    brief_text = json.dumps(semantic_brief, ensure_ascii=False, indent=2)
    instruction = f"""

## 语义理解层 brief

下面是语义理解层对 Reddit 证据的判断。你是中文字段编辑，只基于这个 brief 和原始输入生成中文字段。

{brief_text}

写作要求：
- 保持原 JSON 字段和结构不变。
- title 必须离开 summary_line 也能看懂，写清楚主体、场景和发生了什么。
- 优先使用 actor_and_scene、tension_or_decision、writing_focus 来确定中文表达角度。
- hot 卡优先看 lane_specific.hot；signal 卡优先看 lane_specific.signal；breakdown 卡优先看 lane_specific.breakdown。
- evidence_basis 只作为证据索引；引用原文和 permalink 仍以原始 evidence_quotes 为准，不要编造未列出的 quote。
- 不要照抄 brief，要把它转成自然中文卡片。
- writer_constraints 是硬写作合同；publish_risk 不是 pass 时，表达必须降调。
- 不新增事实；brief 说不能夸大的地方，一律收窄。
- uncertainty 里的 missing_evidence、weak_points、single_thread_risk 是降调依据，不要把弱证据写成强趋势。
- avoid_claims 是硬边界，不能换个说法写进标题、摘要或 detail。
""".rstrip()
    return [
        {**messages[0], "content": messages[0]["content"] + instruction},
        *messages[1:],
    ]


async def _repair_v13_title_if_needed(
    payload: dict[str, Any],
    *,
    semantic_brief: dict[str, Any],
    semantic_model: str,
    writer_model: str,
    timeout: float,
    client_factory: LLMClientFactory,
) -> dict[str, Any]:
    repaired_payload = dict(payload)
    for _ in range(2):
        issues = find_v13_title_issues(_v13_title_check_payload(repaired_payload))
        if not issues:
            break
        try:
            title_payload = await _generate_json(
                model=writer_model,
                timeout=timeout,
                messages=build_title_independence_repair_messages(
                    generated=_v13_title_check_payload(repaired_payload),
                    semantic_brief=semantic_brief,
                    issues=issues,
                    semantic_model=semantic_model,
                    writer_model=writer_model,
                ),
                client_factory=client_factory,
                max_tokens=1024,
                response_schema=None,
            )
        except (HotpostLLMJsonError, HotpostLLMStageTimeout) as exc:
            logger.warning(
                "Hotpost title repair skipped model=%s error_type=%s error=%s",
                writer_model,
                generation_error_type(exc),
                str(exc)[:160],
            )
            break
        repaired_payload = merge_title_repair(repaired_payload, title_payload)
    return repaired_payload


def _v13_title_check_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_detail = payload.get("detail")
    detail = cast(dict[str, Any], raw_detail) if isinstance(raw_detail, dict) else {}
    return {**payload, **detail}


def _semantic_brief_json_schema() -> dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "core_scene": {"type": "STRING"},
            "actor_and_scene": {"type": "STRING"},
            "supported_claim": {"type": "STRING"},
            "confidence_level": {
                "type": "STRING",
                "enum": ["high", "medium", "low"],
            },
            "publish_risk": {
                "type": "STRING",
                "enum": ["pass", "needs_human_review", "block"],
            },
            "claim_type": {
                "type": "STRING",
                "enum": [
                    "channel_test",
                    "market_validation",
                    "tool_adoption",
                    "platform_risk",
                    "generic_advice",
                    "unknown",
                ],
            },
            "evidence_strength": {
                "type": "OBJECT",
                "properties": {
                    "quote_support": {
                        "type": "STRING",
                        "enum": ["strong", "partial", "weak"],
                    },
                    "single_thread_risk": {"type": "BOOLEAN"},
                    "has_specific_user_action": {"type": "BOOLEAN"},
                    "has_measurable_result": {"type": "BOOLEAN"},
                },
                "required": [
                    "quote_support",
                    "single_thread_risk",
                    "has_specific_user_action",
                    "has_measurable_result",
                ],
            },
            "writer_constraints": {
                "type": "OBJECT",
                "properties": {
                    "must_not_claim": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                    },
                    "must_downscope": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                    },
                    "preferred_angle": {"type": "STRING"},
                },
                "required": ["must_not_claim", "must_downscope", "preferred_angle"],
            },
            "evidence_basis": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "claim": {"type": "STRING"},
                        "community": {"type": "STRING"},
                        "quote_text": {"type": "STRING"},
                        "permalink": {"type": "STRING"},
                    },
                    "required": ["claim", "community", "quote_text", "permalink"],
                },
            },
            "lane_specific": {
                "type": "OBJECT",
                "properties": {
                    "hot": {
                        "type": "OBJECT",
                        "properties": {
                            "flashpoint": {"type": "STRING"},
                            "debate_sides": {"type": "STRING"},
                            "controversy_axis": {"type": "STRING"},
                            "why_people_argue": {"type": "STRING"},
                        },
                        "required": [
                            "flashpoint",
                            "debate_sides",
                            "controversy_axis",
                            "why_people_argue",
                        ],
                    },
                    "signal": {
                        "type": "OBJECT",
                        "properties": {
                            "target_user": {"type": "STRING"},
                            "pain_trigger": {"type": "STRING"},
                            "buying_or_adoption_signal": {"type": "STRING"},
                            "testability": {"type": "STRING"},
                        },
                        "required": [
                            "target_user",
                            "pain_trigger",
                            "buying_or_adoption_signal",
                            "testability",
                        ],
                    },
                    "breakdown": {
                        "type": "OBJECT",
                        "properties": {
                            "repeated_pattern": {"type": "STRING"},
                            "cross_thread_commonality": {"type": "STRING"},
                            "thesis_candidate": {"type": "STRING"},
                            "synthesis_angle": {"type": "STRING"},
                        },
                        "required": [
                            "repeated_pattern",
                            "cross_thread_commonality",
                            "thesis_candidate",
                            "synthesis_angle",
                        ],
                    },
                },
                "required": ["hot", "signal", "breakdown"],
            },
            "tension_or_decision": {"type": "STRING"},
            "why_now_readout": {"type": "STRING"},
            "risk_bounds": {"type": "STRING"},
            "writing_focus": {"type": "STRING"},
            "avoid_claims": {"type": "ARRAY", "items": {"type": "STRING"}},
            "uncertainty": {
                "type": "OBJECT",
                "properties": {
                    "confidence": {"type": "STRING"},
                    "missing_evidence": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "weak_points": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "single_thread_risk": {"type": "STRING"},
                },
                "required": [
                    "confidence",
                    "missing_evidence",
                    "weak_points",
                    "single_thread_risk",
                ],
            },
        },
        "required": [
            "core_scene",
            "actor_and_scene",
            "supported_claim",
            "confidence_level",
            "publish_risk",
            "claim_type",
            "evidence_strength",
            "writer_constraints",
            "evidence_basis",
            "lane_specific",
            "tension_or_decision",
            "why_now_readout",
            "risk_bounds",
            "writing_focus",
            "avoid_claims",
            "uncertainty",
        ],
    }


def _breakdown_content_model(
    *, models: dict[str, Any], production_profile: dict[str, Any] | None
) -> str:
    if production_profile is not None:
        return str(production_profile["writer_model"])
    return str(models["reasoning_model"])


def should_be_breakdown(draft: ValidationCardDraft, llm_result: dict[str, Any]) -> bool:
    thesis = str(llm_result.get("thesis") or "").strip()
    supporting = llm_result.get("supporting_quote_permalinks") or []
    quote_pack = llm_result.get("quote_pack") or []
    if not _breakdown_support_is_valid(
        draft, thesis=thesis, supporting=supporting, quote_pack=quote_pack
    ):
        return False
    if _breakdown_fields_overlap(draft, llm_result):
        return False
    return (
        draft.thread_count >= 2
        and len(draft.evidence_quotes) >= 3
        and (draft.community_count >= 2 or draft.thread_count >= 3)
    )


def _breakdown_support_is_valid(
    draft: ValidationCardDraft,
    *,
    thesis: str,
    supporting: list[Any],
    quote_pack: list[Any],
) -> bool:
    if not thesis:
        return False
    valid_permalinks = {
        str(item.permalink).strip()
        for item in draft.evidence_quotes
        if str(item.permalink).strip()
    }
    normalized_supporting = [
        str(item).strip() for item in supporting if str(item).strip()
    ]
    unique_supporting = list(dict.fromkeys(normalized_supporting))
    if len(unique_supporting) < 2:
        return False
    if valid_permalinks and not set(unique_supporting).issubset(valid_permalinks):
        return False
    normalized_quote_pack = [
        str(item).strip() for item in quote_pack if str(item).strip()
    ]
    unique_quote_pack = list(dict.fromkeys(normalized_quote_pack))
    if len(unique_quote_pack) < 2:
        return False
    if any("｜" not in item for item in unique_quote_pack):
        return False
    return True


def _breakdown_fields_overlap(
    draft: ValidationCardDraft, llm_result: dict[str, Any]
) -> bool:
    llm_title = str(llm_result.get("title") or "").strip()
    llm_summary = str(llm_result.get("summary_line") or "").strip()
    llm_why_now = str(llm_result.get("why_now") or "").strip()
    thesis = str(llm_result.get("thesis") or "").strip()
    pairs = [
        (llm_title, llm_summary),
        (llm_summary, llm_why_now),
        (llm_summary, thesis),
        (llm_why_now, thesis),
        (llm_title, thesis),
        (thesis, str(draft.summary_line or "").strip()),
        (thesis, str(draft.why_now or "").strip()),
        (thesis, str(draft.title or "").strip()),
    ]
    return any(_texts_mean_same_thing(left, right) for left, right in pairs)


def _texts_mean_same_thing(left: str, right: str) -> bool:
    left_norm = _normalize_breakdown_gate_text(left)
    right_norm = _normalize_breakdown_gate_text(right)
    if not left_norm or not right_norm:
        return False
    shorter, longer = sorted((left_norm, right_norm), key=len)
    if len(shorter) >= 12 and shorter in longer:
        return True
    return SequenceMatcher(None, left_norm, right_norm).ratio() >= 0.9


def _normalize_breakdown_gate_text(value: str) -> str:
    lowered = value.strip().lower()
    if not lowered:
        return ""
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", lowered)


def backfill_published_cards(
    *,
    generated_cards: Optional[list[dict[str, Any]]] = None,
) -> int:
    if generated_cards is None:
        raise ValueError("generated_cards must be provided")
    return merge_published_cards(generated_cards)


def build_backfill_draft(
    item: dict[str, Any]
) -> ValidationCardDraft | WritingCardDraft:
    base = {
        "draft_id": f"backfill-{item['card_id']}",
        "candidate_id": item["card_id"],
        "candidate_ids": [item["card_id"]],
        "card_id": item["card_id"],
        "signal_id": item["signal_id"],
        "card_type": item["card_type"],
        "lane": item.get("lane") or "signal",
        "category_id": item["category_id"],
        "title": item["title"],
        "source_scope_id": item["source_scope_id"],
        "source_scope_name": item["source_scope_name"],
        "matched_subreddit": item["source_module"]["top_community"].replace(
            "r/", "", 1
        ),
        "post_id": item["preview_quote"]["permalink"]
        .split("/comments/")[-1]
        .split("/")[0],
        "source_event_at": item.get("source_event_at"),
        "score": 0,
        "num_comments": 0,
        "time_window": _guess_time_window(item["source_module"]["last_active_text"]),
        "signal_level": item.get("signal_level") or _derive_signal_level(item),
        "why_now_reason": item["why_now_reason"],
        "thread_count": item["source_module"]["thread_count"],
        "community_count": item["source_module"]["community_count"],
        "quote_count": len(item.get("quotes") or []),
        "intent_tags": item.get("intent_tags") or [],
        "evidence_quotes": item.get("quotes") or [item["preview_quote"]],
        "summary_line": item.get("summary_line") or "",
        "audience": item.get("audience") or "",
        "why_now": item.get("why_now") or "",
        "source_link": item["source_link"],
        "source_links": [item["source_link"]],
        "source_communities": item["source_module"]["primary_communities"],
        "draft_status": "draft",
        "draft_note": "full migration backfill",
    }
    if item["card_type"] == "write":
        return WritingCardDraft(**base, detail=item["detail"])
    return ValidationCardDraft(**base, detail=item["detail"])


def build_backfilled_published_card(
    draft: ValidationCardDraft | WritingCardDraft,
) -> dict[str, Any]:
    return build_published_card(draft).model_dump(mode="json")


async def _generate_json(
    *,
    model: str,
    timeout: float,
    messages: list[dict[str, str]],
    client_factory: LLMClientFactory,
    max_tokens: int = 2048,
    response_schema: Optional[dict[str, Any]] = None,
    trace_id: str = "",
    stage: str = "",
) -> dict[str, Any]:
    client = client_factory(model, timeout)
    response_format = _json_response_format_for_model(
        model, response_schema=response_schema
    )
    stage_name = stage or "llm_json"
    raw = await _call_llm_json_stage(
        client=client,
        model=model,
        timeout=timeout,
        name=stage_name,
        messages=messages,
        response_format=response_format,
        temperature=0.2,
        max_tokens=max_tokens,
    )
    try:
        return _coerce_llm_json_payload(raw)
    except ValueError as exc:
        _log_invalid_json_payload(
            model=model, stage=stage, trace_id=trace_id, raw=raw, error=exc
        )
        if generation_error_type(exc) == "empty_response":
            raise
        retry_messages = _invalid_json_retry_messages(messages, model=model, attempt=1)
        raw = await _call_llm_json_stage(
            client=client,
            model=model,
            timeout=timeout,
            name="json_retry",
            messages=retry_messages,
            response_format=response_format,
            temperature=0.0,
            max_tokens=max_tokens,
            attempt=1,
        )
        try:
            return _coerce_llm_json_payload(raw)
        except ValueError as exc:
            _log_invalid_json_payload(
                model=model, stage=stage, trace_id=trace_id, raw=raw, error=exc
            )
            if generation_error_type(exc) == "empty_response":
                raise
            if not model.startswith("google/"):
                return await _repair_invalid_json_payload(
                    client=client,
                    model=model,
                    timeout=timeout,
                    raw=raw,
                    response_schema=response_schema,
                )
            raw = await _call_llm_json_stage(
                client=client,
                model=model,
                timeout=timeout,
                name="json_retry",
                messages=_invalid_json_retry_messages(messages, model=model, attempt=2),
                response_format=response_format,
                temperature=0.0,
                max_tokens=max_tokens,
                attempt=2,
            )
            try:
                return _coerce_llm_json_payload(raw)
            except ValueError as exc:
                _log_invalid_json_payload(
                    model=model, stage=stage, trace_id=trace_id, raw=raw, error=exc
                )
                if generation_error_type(exc) == "empty_response":
                    raise
                return await _repair_invalid_json_payload(
                    client=client,
                    model=model,
                    timeout=timeout,
                    raw=raw,
                    response_schema=response_schema,
                )


async def _call_llm_json_stage(
    *,
    client: Any,
    model: str,
    timeout: float,
    name: str,
    messages: list[dict[str, str]],
    response_format: Optional[dict[str, Any]],
    temperature: float,
    max_tokens: int,
    attempt: int | None = None,
) -> str:
    started = time.monotonic()
    try:
        raw = await asyncio.wait_for(
            client.generate(
                messages,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
            ),
            timeout=max(0.001, float(timeout)),
        )
    except asyncio.TimeoutError as exc:
        error = HotpostLLMStageTimeout(name, model, timeout)
        _record_generation_sub_stage(
            name=name,
            model=model,
            timeout=timeout,
            started=started,
            status="failed",
            error_type=error.error_type,
            attempt=attempt,
        )
        raise error from exc
    except Exception as exc:
        _record_generation_sub_stage(
            name=name,
            model=model,
            timeout=timeout,
            started=started,
            status="failed",
            error_type=generation_error_type(exc),
            attempt=attempt,
        )
        raise
    _record_generation_sub_stage(
        name=name,
        model=model,
        timeout=timeout,
        started=started,
        status="completed",
        attempt=attempt,
        raw_chars=len(raw or ""),
    )
    return str(raw or "")


def _record_generation_sub_stage(
    *,
    name: str,
    model: str,
    timeout: float,
    started: float,
    status: str,
    error_type: str = "",
    attempt: int | None = None,
    raw_chars: int | None = None,
) -> None:
    stages = _GENERATION_SUB_STAGES.get()
    if stages is None:
        return
    entry: dict[str, Any] = {
        "name": name,
        "status": status,
        "model": model,
        "provider": _provider_for_model(model),
        "timeout_seconds": float(timeout),
        "duration_ms": round((time.monotonic() - started) * 1000, 1),
    }
    if attempt is not None:
        entry["attempt"] = attempt
    if error_type:
        entry["error_type"] = error_type
    if raw_chars is not None:
        entry["raw_chars"] = raw_chars
    stages.append(entry)


def _provider_for_model(model: str) -> str:
    if model.startswith("google/"):
        return "gemini"
    if model.startswith("deepseek/"):
        return "deepseek"
    return "openai_compatible"


def _log_invalid_json_payload(
    *,
    model: str,
    stage: str,
    trace_id: str,
    raw: str,
    error: ValueError,
) -> None:
    if not stage and not trace_id:
        return
    logger.warning(
        "Hotpost LLM JSON parse failed stage=%s model=%s trace_id=%s error=%s raw_head=%r raw_tail=%r",
        stage or "-",
        model,
        trace_id or "-",
        str(error)[:240],
        (raw or "")[:240],
        (raw or "")[-240:],
    )


def _coerce_llm_json_payload(raw: str) -> dict[str, Any]:
    payload = _loads_llm_json(raw)
    if isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict):
        payload = payload[0]
    if not isinstance(payload, dict):
        raise HotpostLLMJsonError("invalid_json", "LLM payload must be a JSON object")
    return payload


def _json_response_format_for_model(
    model: str, *, response_schema: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    if model.startswith("google/") and response_schema is not None:
        return {"type": "json_object", "schema": response_schema}
    return {"type": "json_object"}


def _invalid_json_retry_messages(
    messages: list[dict[str, str]],
    *,
    model: str,
    attempt: int,
) -> list[dict[str, str]]:
    if attempt == 1:
        instruction = (
            "上一轮输出不是合法 JSON。不要解释，不要返回数组，不要使用 Markdown。"
            "按同一输入重新输出一个完整 JSON object，字段保持 output_schema，不要截断字符串。"
        )
    elif model.startswith("google/"):
        instruction = (
            "上一轮 JSON 仍然不合法。现在只做一件事：重新输出一个完整、闭合、可解析的 JSON object。"
            "不要补说明，不要输出数组，不要使用 Markdown。"
            "所有字段写得更短一点，优先中文转述，少用引号包原话，不要留下半句英文。"
        )
    else:
        instruction = "上一轮 JSON 仍然不合法。重新输出一个完整 JSON object，不要解释。"
    return [
        *messages,
        {"role": "system", "content": instruction},
    ]


async def _repair_invalid_json_payload(
    *,
    client: Any,
    model: str,
    timeout: float,
    raw: str,
    response_schema: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    repair_messages = [
        {
            "role": "system",
            "content": (
                "你是一个 JSON 修复器。用户给你的是坏掉的模型输出。"
                "现在只做一件事：把它修成一个完整、闭合、可解析的 JSON object。"
                "不要解释，不要返回数组，不要使用 Markdown。"
                "如果原文里有英文引号、半句英文或截断片段，允许你改写成更短的中文转述，"
                "但不要删字段。"
            ),
        },
        {
            "role": "user",
            "content": raw,
        },
    ]
    repaired = await _call_llm_json_stage(
        client=client,
        model=model,
        timeout=timeout,
        name="json_repair",
        messages=repair_messages,
        response_format={"type": "json_object"},
        temperature=0.0,
        max_tokens=2048,
    )
    try:
        return _coerce_llm_json_payload(repaired)
    except ValueError as exc:
        raise HotpostLLMJsonError("json_repair_failed", str(exc)) from exc


async def _regenerate_json_for_validation_error(
    *,
    model: str,
    timeout: float,
    messages: list[dict[str, str]],
    client_factory: LLMClientFactory,
    max_tokens: int,
    error: ValueError,
    response_schema: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    retry_messages = [
        *messages,
        {
            "role": "system",
            "content": (
                f"上一轮 JSON 字段不合格：{error}。"
                "不要解释，不要返回数组，不要使用 Markdown。"
                "按同一输入重新输出完整 JSON object。"
                "必须避开报错里的词，保持字段含义不变，把话写得更短、更像真人转述。"
            ),
        },
    ]
    return await _generate_json(
        model=model,
        timeout=timeout,
        messages=retry_messages,
        client_factory=client_factory,
        max_tokens=max_tokens,
        response_schema=response_schema,
    )


def _max_tokens(rules: dict[str, Any], key: str, *, default: int) -> int:
    raw = rules.get("max_tokens") or {}
    if not isinstance(raw, dict):
        return default
    try:
        value = int(raw.get(key) or default)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _loads_llm_json(raw: str) -> Any:
    if not raw or not raw.strip():
        raise HotpostLLMJsonError("empty_response", "LLM returned empty response")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        normalized = _escape_json_string_control_chars(raw)
        if normalized != raw:
            try:
                return json.loads(normalized)
            except json.JSONDecodeError:
                pass
        extracted = _extract_first_json_object(normalized)
        if extracted:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass
        error_type = "json_extra_data" if exc.msg == "Extra data" else "invalid_json"
        raise HotpostLLMJsonError(
            error_type,
            f"LLM returned invalid JSON: {raw[:200]}",
        ) from exc


def _extract_first_json_object(raw: str) -> str | None:
    start = raw.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(raw)):
        char = raw[index]
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0:
                return raw[start : index + 1]
    return None


def _escape_json_string_control_chars(raw: str) -> str:
    output: list[str] = []
    in_string = False
    escaped = False
    for char in raw:
        if escaped:
            output.append(char)
            escaped = False
            continue
        if char == "\\" and in_string:
            output.append(char)
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            output.append(char)
            continue
        if in_string and char in {"\n", "\r", "\t"}:
            output.append({"\n": "\\n", "\r": "\\r", "\t": "\\t"}[char])
            continue
        output.append(char)
    return "".join(output)


def _apply_validation_content(
    draft: ValidationCardDraft | WritingCardDraft,
    payload: dict[str, Any],
    rules: dict[str, Any],
) -> ValidationCardDraft:
    detail_payload = payload.get("detail") or {}
    if not isinstance(detail_payload, dict):
        raise ValueError("signal detail payload is invalid")
    detail_payload = dict(detail_payload)
    why_now = _validated_text(payload.get("why_now"), "why_now", rules)
    detail_payload["why_test_now"] = _validated_text(
        detail_payload.get("why_test_now"),
        "why_test_now",
        rules,
    )
    detail_payload["continue_signal"] = _validated_text(
        detail_payload.get("continue_signal"),
        "continue_signal",
        rules,
    )
    detail_payload["stop_signal"] = _validated_text(
        detail_payload.get("stop_signal"),
        "stop_signal",
        rules,
    )
    detail_payload.pop("min_test_action", None)
    if draft.lane == "hot":
        detail_payload["flashpoint"] = _validated_text(
            detail_payload.get("flashpoint"),
            "flashpoint",
            rules,
        )
        detail_payload["fight_line"] = _validated_text(
            detail_payload.get("fight_line"),
            "fight_line",
            rules,
        )
    else:
        detail_payload["pain_point"] = _validated_text(
            detail_payload.get("pain_point"),
            "pain_point",
            rules,
        )
        detail_payload["target_user_and_scene"] = _validated_text(
            detail_payload.get("target_user_and_scene"),
            "target_user_and_scene",
            rules,
        )
        detail_payload["min_test_action"] = _validated_text(
            detail_payload.get("min_test_action") or "去看原始讨论",
            "min_test_action",
            rules,
        )
    signal_detail = build_validation_detail(draft.lane, detail_payload)
    preview_permalink = str(payload.get("preview_quote_permalink") or "").strip()
    reordered_quotes = _reorder_quotes(draft.evidence_quotes, preview_permalink)
    validate_draft = ValidationCardDraft(
        **_common_draft_payload(draft, card_type="validate"),
        title=_validated_text(payload.get("title"), "title", rules),
        summary_line=_validated_text(
            payload.get("summary_line"), "summary_line", rules
        ),
        audience=_validated_text(payload.get("audience"), "audience", rules),
        why_now=why_now,
        source_link=draft.source_link,
        source_links=draft.source_links,
        source_communities=draft.source_communities,
        evidence_quotes=reordered_quotes,
        detail=signal_detail,
    )
    return validate_draft


def _card_content_json_schema_for_draft(
    draft: ValidationCardDraft | WritingCardDraft,
) -> dict[str, Any]:
    if isinstance(draft, ValidationCardDraft) and draft.lane == "hot":
        detail_properties = {
            "flashpoint": {"type": "STRING"},
            "fight_line": {"type": "STRING"},
            "why_test_now": {"type": "STRING"},
            "continue_signal": {"type": "STRING"},
            "stop_signal": {"type": "STRING"},
        }
        required = [
            "flashpoint",
            "fight_line",
            "why_test_now",
            "continue_signal",
            "stop_signal",
        ]
    else:
        detail_properties = {
            "pain_point": {"type": "STRING"},
            "target_user_and_scene": {"type": "STRING"},
            "why_test_now": {"type": "STRING"},
            "continue_signal": {"type": "STRING"},
            "stop_signal": {"type": "STRING"},
        }
        required = [
            "pain_point",
            "target_user_and_scene",
            "why_test_now",
            "continue_signal",
            "stop_signal",
        ]
    return {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING"},
            "summary_line": {"type": "STRING"},
            "audience": {"type": "STRING"},
            "why_now": {"type": "STRING"},
            "preview_quote_permalink": {"type": "STRING"},
            "detail": {
                "type": "OBJECT",
                "properties": detail_properties,
                "required": required,
            },
        },
        "required": [
            "title",
            "summary_line",
            "audience",
            "why_now",
            "preview_quote_permalink",
            "detail",
        ],
    }


def _apply_breakdown_content(
    draft: ValidationCardDraft | WritingCardDraft,
    payload: dict[str, Any],
    rules: dict[str, Any],
) -> WritingCardDraft:
    supporting = [
        str(item).strip()
        for item in (payload.get("supporting_quote_permalinks") or [])
        if str(item).strip()
    ]
    reordered_quotes = _reorder_quotes(
        draft.evidence_quotes, supporting[0] if supporting else ""
    )
    detail = WritingDetail.model_validate(
        {
            "thesis": _validated_text(payload.get("thesis"), "thesis", rules),
            "writing_angle_or_perspective": _validated_text(
                payload.get("writing_angle_or_perspective"),
                "writing_angle_or_perspective",
                rules,
            ),
            "tension_point_or_why_it_matters": _validated_text(
                payload.get("tension_point_or_why_it_matters"),
                "tension_point_or_why_it_matters",
                rules,
            ),
            "title_hooks": [
                str(item).strip()
                for item in (payload.get("title_hooks") or [])
                if str(item).strip()
            ][:2],
            "quote_pack": [
                str(item).strip()
                for item in (payload.get("quote_pack") or [])
                if str(item).strip()
            ],
        }
    )
    return WritingCardDraft(
        **_common_draft_payload(draft, card_type="write"),
        title=_validated_text(payload.get("title"), "title", rules),
        summary_line=_validated_text(
            payload.get("summary_line"), "summary_line", rules
        ),
        audience=_validated_text(
            payload.get("audience") or draft.audience, "audience", rules
        ),
        why_now=_validated_text(
            payload.get("why_now") or draft.why_now, "why_now", rules
        ),
        source_link=draft.source_link,
        source_links=draft.source_links,
        source_communities=draft.source_communities,
        evidence_quotes=reordered_quotes,
        detail=detail,
    )


def _breakdown_json_schema() -> dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING"},
            "summary_line": {"type": "STRING"},
            "audience": {"type": "STRING"},
            "why_now": {"type": "STRING"},
            "thesis": {"type": "STRING"},
            "writing_angle_or_perspective": {"type": "STRING"},
            "tension_point_or_why_it_matters": {"type": "STRING"},
            "title_hooks": {"type": "ARRAY", "items": {"type": "STRING"}},
            "quote_pack": {"type": "ARRAY", "items": {"type": "STRING"}},
            "supporting_quote_permalinks": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
        },
        "required": [
            "title",
            "summary_line",
            "audience",
            "why_now",
            "thesis",
            "writing_angle_or_perspective",
            "tension_point_or_why_it_matters",
            "title_hooks",
            "quote_pack",
            "supporting_quote_permalinks",
        ],
    }


def _common_draft_payload(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    card_type: str,
) -> dict[str, Any]:
    payload = draft.model_dump(
        mode="python",
        exclude={
            "detail",
            "title",
            "summary_line",
            "audience",
            "why_now",
            "source_link",
            "source_links",
            "source_communities",
            "evidence_quotes",
            "card_type",
            "category_id",
            "draft_id",
            "card_id",
        },
    )
    payload["card_type"] = card_type
    payload["category_id"] = card_type
    if card_type == "write":
        payload["lane"] = "breakdown"
    payload["draft_id"] = _replace_card_type_suffix(draft.draft_id, card_type)
    payload["card_id"] = _replace_card_type_suffix(draft.card_id, card_type)
    return payload


def _replace_card_type_suffix(value: str, card_type: str) -> str:
    if value.endswith("-validate") or value.endswith("-write"):
        head = value.rsplit("-", 1)[0]
        return f"{head}-{card_type}"
    return value


def _guess_time_window(last_active_text: str) -> str:
    if "24" in last_active_text:
        return "24h"
    if "7" in last_active_text:
        return "7d"
    return "30d"


def _derive_signal_level(item: dict[str, Any]) -> str:
    why_now_reason = str(item.get("why_now_reason") or "")
    thread_count = int((item.get("source_module") or {}).get("thread_count") or 1)
    if why_now_reason == "new_threads_24h":
        return "hot"
    if why_now_reason == "switch_signal_7d" or thread_count >= 3:
        return "rising"
    return "sustained"


def _can_attempt_breakdown(draft: ValidationCardDraft, models: dict[str, Any]) -> bool:
    return (
        bool(models["reasoning_enabled"])
        and len(draft.evidence_quotes) >= 3
        and draft.thread_count >= 2
    )


def _reorder_quotes(
    quotes: list[QuotePreview], selected_permalink: str
) -> list[QuotePreview]:
    if not quotes or not selected_permalink:
        return quotes
    picked = next(
        (quote for quote in quotes if quote.permalink == selected_permalink), None
    )
    if picked is None:
        return quotes
    return [
        picked,
        *[quote for quote in quotes if quote.permalink != selected_permalink],
    ]


def _validated_text(value: Any, field_name: str, rules: dict[str, Any]) -> str:
    text = polish_generated_text(str(value or "").strip(), field_name=field_name)
    text = polish_generated_text(
        _rewrite_validated_text(text, rules).strip(), field_name=field_name
    )
    if not text:
        raise ValueError(f"{field_name} is empty")
    banned = [*_all_banned_patterns(rules), *_field_banned_patterns(rules, field_name)]
    hit = next((pattern for pattern in banned if pattern and pattern in text), None)
    if hit:
        raise ValueError(f"{field_name} contains banned pattern: {hit}")
    return text


def _rewrite_validated_text(text: str, rules: dict[str, Any]) -> str:
    rewrite_phrases = (rules.get("semantic_readout") or {}).get("rewrite_phrases") or {}
    if not isinstance(rewrite_phrases, dict):
        return text
    rewritten = text
    for source, target in rewrite_phrases.items():
        source_text = str(source or "")
        if not source_text:
            continue
        rewritten = rewritten.replace(source_text, str(target or ""))
    return re.sub(r"\s{2,}", " ", rewritten).strip()


def _all_banned_patterns(rules: dict[str, Any]) -> list[str]:
    patterns = rules.get("banned_patterns") or {}
    global_patterns = [
        str(item).strip() for item in patterns.get("global", []) if str(item).strip()
    ]
    return global_patterns


def _field_banned_patterns(rules: dict[str, Any], field_name: str) -> list[str]:
    patterns = rules.get("banned_patterns") or {}
    field_specific = patterns.get("field_specific") or {}
    if not isinstance(field_specific, dict):
        return []
    return [
        str(item).strip()
        for item in field_specific.get(field_name, [])
        if str(item).strip()
    ]


def _draft_topic_pack_id(
    draft: ValidationCardDraft | WritingCardDraft,
) -> Optional[str]:
    if getattr(draft, "topic_pack_id", None):
        return str(draft.topic_pack_id).strip() or None
    item = next(
        (
            row
            for row in load_candidates()
            if row.get("candidate_id") == draft.candidate_id
        ),
        None,
    )
    if item is None:
        return None
    return str(item.get("topic_pack_id") or "").strip() or None


__all__ = [
    "backfill_published_cards",
    "build_backfill_draft",
    "build_backfilled_published_card",
    "refresh_breakdown_content",
    "generate_card_content",
    "load_card_content_models",
    "load_card_content_rules",
    "should_be_breakdown",
]
