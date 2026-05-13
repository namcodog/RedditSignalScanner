from __future__ import annotations

import re
from typing import Optional, Any

from app.schemas.hotpost_card_drafts import ValidationCardDraft, WritingCardDraft
from app.schemas.hotpost_validate_details import HotValidationDetail, SignalValidationDetail


def semantic_prompt_extra(
    *,
    rules: dict[str, Any],
    lane: str,
    topic_pack_id:Optional[ str],
) -> str:
    config = _semantic_config(rules)
    sections: list[str] = []
    lane_instructions = config.get("lane_instructions") or {}
    sections.extend(_string_list(lane_instructions.get(lane)))
    pack_instructions = config.get("pack_instructions") or {}
    if topic_pack_id:
        sections.extend(_string_list(pack_instructions.get(topic_pack_id)))
    if not sections:
        return ""
    return "\n这张卡继续按这个口吻写：" + "".join(f"\n- {section}" for section in sections)


def finalize_signal_readout(
    draft: ValidationCardDraft,
    *,
    source_draft: ValidationCardDraft | WritingCardDraft,
    rules: dict[str, Any],
) -> ValidationCardDraft:
    config = _semantic_config(rules)
    rewrite_phrases = _string_mapping(config.get("rewrite_phrases"))
    anchor_config = _semantic_anchor_config(config)
    field_updates = {
        "title": _clean_readout_text(draft.title, rewrite_phrases=rewrite_phrases, ensure_sentence=False),
        "summary_line": _clean_readout_text(draft.summary_line, rewrite_phrases=rewrite_phrases, ensure_sentence=True),
        "audience": _clean_readout_text(draft.audience, rewrite_phrases=rewrite_phrases, ensure_sentence=False),
        "why_now": _clean_readout_text(draft.why_now, rewrite_phrases=rewrite_phrases, ensure_sentence=True),
    }
    detail = draft.detail.model_copy(
        update={
            "pain_point": _clean_readout_text(
                draft.detail.pain_point,
                rewrite_phrases=rewrite_phrases,
                ensure_sentence=True,
            ),
            "target_user_and_scene": _clean_readout_text(
                draft.detail.target_user_and_scene,
                rewrite_phrases=rewrite_phrases,
                ensure_sentence=True,
            ),
            "why_test_now": _clean_readout_text(
                _anchor_why_test_now(
                    draft.detail.why_test_now,
                    target_draft=draft,
                    source_draft=source_draft,
                    anchor_config=anchor_config,
                ),
                rewrite_phrases=rewrite_phrases,
                ensure_sentence=True,
            ),
            "continue_signal": _clean_readout_text(
                _anchor_continue_signal(
                    draft.detail.continue_signal,
                    source_draft=source_draft,
                    anchor_config=anchor_config,
                ),
                rewrite_phrases=rewrite_phrases,
                ensure_sentence=True,
            ),
            "stop_signal": _clean_readout_text(
                draft.detail.stop_signal,
                rewrite_phrases=rewrite_phrases,
                ensure_sentence=True,
            ),
        }
    )
    guarded = draft.model_copy(update={**field_updates, "detail": detail})
    _assert_no_unsupported_terms(guarded, source_draft=source_draft, rules=rules)
    return guarded


def finalize_hot_readout(
    draft: ValidationCardDraft,
    *,
    source_draft: ValidationCardDraft | WritingCardDraft,
    rules: dict[str, Any],
) -> ValidationCardDraft:
    config = _semantic_config(rules)
    rewrite_phrases = _string_mapping(config.get("rewrite_phrases"))
    anchor_config = _semantic_anchor_config(config)
    hot_detail = draft.detail
    if not isinstance(hot_detail, HotValidationDetail):
        raise ValueError("hot readout requires hot validation detail")
    field_updates = {
        "title": _normalize_hot_readout_text(
            _clean_readout_text(draft.title, rewrite_phrases=rewrite_phrases, ensure_sentence=False),
            field="title",
        ),
        "summary_line": _normalize_hot_readout_text(
            _clean_readout_text(draft.summary_line, rewrite_phrases=rewrite_phrases, ensure_sentence=True),
            field="summary_line",
        ),
        "audience": _normalize_hot_readout_text(
            _clean_readout_text(draft.audience, rewrite_phrases=rewrite_phrases, ensure_sentence=False),
            field="audience",
        ),
        "why_now": _normalize_hot_readout_text(
            _clean_readout_text(draft.why_now, rewrite_phrases=rewrite_phrases, ensure_sentence=True),
            field="why_now",
        ),
    }
    detail = hot_detail.model_copy(
        update={
            "flashpoint": _normalize_hot_readout_text(
                _clean_readout_text(
                    hot_detail.flashpoint,
                    rewrite_phrases=rewrite_phrases,
                    ensure_sentence=True,
                ),
                field="flashpoint",
            ),
            "fight_line": _normalize_hot_readout_text(
                _clean_readout_text(
                    hot_detail.fight_line,
                    rewrite_phrases=rewrite_phrases,
                    ensure_sentence=True,
                ),
                field="fight_line",
            ),
            "why_test_now": _normalize_hot_readout_text(
                _clean_readout_text(
                    _anchor_why_test_now(
                        hot_detail.why_test_now,
                        target_draft=draft,
                        source_draft=source_draft,
                        anchor_config=anchor_config,
                    ),
                    rewrite_phrases=rewrite_phrases,
                    ensure_sentence=True,
                ),
                field="why_test_now",
            ),
            "continue_signal": _normalize_hot_readout_text(
                _clean_readout_text(
                    _anchor_continue_signal(
                        hot_detail.continue_signal,
                        source_draft=source_draft,
                        anchor_config=anchor_config,
                    ),
                    rewrite_phrases=rewrite_phrases,
                    ensure_sentence=True,
                ),
                field="continue_signal",
            ),
            "stop_signal": _normalize_hot_readout_text(
                _clean_readout_text(
                    hot_detail.stop_signal,
                    rewrite_phrases=rewrite_phrases,
                    ensure_sentence=True,
                ),
                field="stop_signal",
            ),
        }
    )
    guarded = draft.model_copy(update={**field_updates, "detail": detail})
    _assert_no_unsupported_terms(guarded, source_draft=source_draft, rules=rules)
    return guarded


def finalize_validation_readout(
    draft: ValidationCardDraft,
    *,
    source_draft: ValidationCardDraft | WritingCardDraft,
    rules: dict[str, Any],
) -> ValidationCardDraft:
    if draft.lane == "hot":
        return finalize_hot_readout(draft, source_draft=source_draft, rules=rules)
    if not isinstance(draft.detail, SignalValidationDetail):
        raise ValueError("signal readout requires signal validation detail")
    return finalize_signal_readout(draft, source_draft=source_draft, rules=rules)


def clean_readout_text_for_client(text: str, *, rules: dict[str, Any], ensure_sentence: bool) -> str:
    config = _semantic_config(rules)
    rewrite_phrases = _string_mapping(config.get("rewrite_phrases"))
    return _clean_readout_text(text, rewrite_phrases=rewrite_phrases, ensure_sentence=ensure_sentence)


def _semantic_config(rules: dict[str, Any]) -> dict[str, Any]:
    config = rules.get("semantic_readout") or {}
    if not isinstance(config, dict):
        raise ValueError("card_content_rules.yaml semantic_readout must be a mapping")
    return config


def _semantic_anchor_config(config: dict[str, Any]) -> dict[str, Any]:
    anchoring = config.get("anchoring") or {}
    if not isinstance(anchoring, dict):
        return {}
    return anchoring


def _clean_readout_text(text: str, *, rewrite_phrases: dict[str, str], ensure_sentence: bool) -> str:
    cleaned = str(text or "").strip()
    for source, target in rewrite_phrases.items():
        cleaned = cleaned.replace(source, target)
    cleaned = cleaned.replace("  ", " ")
    cleaned = cleaned.strip("，。 ")
    if ensure_sentence and cleaned and cleaned[-1] not in "。！？":
        return cleaned + "。"
    return cleaned


def _normalize_hot_readout_text(text: str, *, field: str) -> str:
    cleaned = _strip_ellipsis(text)
    if field == "why_test_now":
        cleaned = _rewrite_hot_why_test_now_translationese(cleaned)
    return cleaned


def _assert_no_unsupported_terms(
    draft: ValidationCardDraft,
    *,
    source_draft: ValidationCardDraft | WritingCardDraft,
    rules: dict[str, Any],
) -> None:
    config = _semantic_config(rules)
    term_rules = config.get("unsupported_term_guard") or {}
    if not isinstance(term_rules, dict):
        return
    guarded_terms = _string_list(term_rules.get("terms"))
    if not guarded_terms:
        return
    evidence_text = _source_evidence_text(source_draft)
    generated = " ".join([draft.title, draft.summary_line, draft.audience, draft.why_now]).lower()
    for term in guarded_terms:
        normalized = term.lower()
        if normalized in generated and normalized not in evidence_text:
            raise ValueError(f"semantic readout introduced unsupported term: {term}")


def _anchor_why_test_now(
    text: str,
    *,
    target_draft: ValidationCardDraft |Optional[ WritingCardDraft] = None,
    source_draft: ValidationCardDraft | WritingCardDraft,
    anchor_config: dict[str, Any],
) -> str:
    cleaned = str(text or "").strip()
    template_source = target_draft or source_draft
    template = _why_test_now_template_for_draft(template_source, anchor_config=anchor_config)
    if not template or _has_evidence_anchor(cleaned, source_draft=source_draft, anchor_config=anchor_config):
        return cleaned
    quote = _best_quote_anchor(source_draft, anchor_config=anchor_config)
    if not quote:
        return cleaned
    return template.format(quote=quote, text=cleaned)


def _anchor_continue_signal(
    text: str,
    *,
    source_draft: ValidationCardDraft | WritingCardDraft,
    anchor_config: dict[str, Any],
) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return cleaned
    template = str(anchor_config.get("continue_signal_template") or "").strip()
    if not template:
        return cleaned
    if _has_explicit_tracking_terms(cleaned):
        return cleaned
    anchor_terms = _source_anchor_terms(source_draft, anchor_config=anchor_config)
    if not anchor_terms or _contains_any_anchor(cleaned, anchor_terms):
        return cleaned
    max_terms = _positive_int(anchor_config.get("max_continue_terms"), default=3)
    readable_terms = "、".join(anchor_terms[:max_terms])
    return template.format(text=cleaned.rstrip("。！？"), terms=readable_terms)


def _has_evidence_anchor(
    text: str,
    *,
    source_draft: ValidationCardDraft | WritingCardDraft,
    anchor_config: dict[str, Any],
) -> bool:
    markers = _string_list(anchor_config.get("evidence_markers"))
    if markers and any(marker in text for marker in markers):
        return True
    return _contains_any_anchor(text, _source_anchor_terms(source_draft, anchor_config=anchor_config))


def _contains_any_anchor(text: str, anchor_terms: list[str]) -> bool:
    normalized = text.lower()
    return any(term.lower() in normalized for term in anchor_terms)


def _has_explicit_tracking_terms(text: str) -> bool:
    if any(marker in text for marker in ("观察", "继续看", "后面看", "后续看", "接下来看")):
        return True
    quoted_terms = re.findall(r"[『“\"]([^『』“”\"]{2,40})[』”\"]", text)
    if len(quoted_terms) >= 2:
        return True
    english_terms = re.findall(r"[A-Za-z][A-Za-z0-9+._-]*(?:\s+[A-Za-z][A-Za-z0-9+._-]*)?", text)
    useful_terms = [term for term in english_terms if len(term.replace(" ", "")) >= 5]
    return len(useful_terms) >= 2


def _best_quote_anchor(draft: ValidationCardDraft | WritingCardDraft, *, anchor_config: dict[str, Any]) -> str:
    fallback = ""
    for quote in draft.evidence_quotes:
        text = str(quote.text or "").strip()
        if not text:
            continue
        trimmed = _trim_quote_anchor(text, limit=_positive_int(anchor_config.get("quote_char_limit"), default=92))
        if not fallback:
            fallback = trimmed
        if _looks_like_auto_summary_quote(text):
            continue
        return trimmed
    return fallback


def _looks_like_auto_summary_quote(text: str) -> bool:
    normalized = " ".join(text.split()).lower()
    return "tl;dr of the discussion" in normalized or "generated automatically after" in normalized


def _trim_quote_anchor(text: str, *, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip(" ,，。")


def _strip_ellipsis(text: str) -> str:
    cleaned = re.sub(r"(?:\.\.\.+|…+)", "", str(text or ""))
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def _rewrite_hot_why_test_now_translationese(text: str) -> str:
    cleaned = str(text or "").strip()
    patterns = [
        r"^原话里那句\s*(?P<quote>.+?)\s*说明(?P<rest>.+)$",
        r"^原话里那句\s*(?P<quote>.+?)\s*戳中了痛点(?:。(?P<rest>.+))?$",
        r"^原话里那句\s*(?P<quote>.+?)\s*戳中了大家(?:。(?P<rest>.+))?$",
        r"^原话里最关键的是\s*(?P<quote>.+?)(?:。(?P<rest>.+))?$",
        r"^原话里最扎心的是\s*(?P<quote>.+?)(?:。(?P<rest>.+))?$",
        r"^原话里提到\s*(?P<quote>.+?)(?:。(?P<rest>.+))?$",
        r"^原话里的关键是\s*(?P<quote>.+?)(?:。(?P<rest>.+))?$",
        r"^原话里的\s*(?P<quote>.+?)\s*是关键(?:。(?P<rest>.+))?$",
        r"^原话里的\s*(?P<quote>.+?)\s*杀伤力太强(?:。(?P<rest>.+))?$",
        r"^原话里的\s*(?P<quote>.+?)\s*很有杀伤力(?:。(?P<rest>.+))?$",
        r"^原文里那句\s*(?P<quote>.+?)\s*说明(?P<rest>.+)$",
        r"^原文里那句\s*(?P<quote>.+?)\s*戳中了痛点(?:。(?P<rest>.+))?$",
        r"^原文里那句\s*(?P<quote>.+?)\s*戳中了大家(?:。(?P<rest>.+))?$",
        r"^原文里最关键的是\s*(?P<quote>.+?)(?:。(?P<rest>.+))?$",
        r"^原文里最扎心的是\s*(?P<quote>.+?)(?:。(?P<rest>.+))?$",
        r"^原文里提到\s*(?P<quote>.+?)(?:。(?P<rest>.+))?$",
        r"^原文里的关键是\s*(?P<quote>.+?)(?:。(?P<rest>.+))?$",
        r"^原文里的\s*(?P<quote>.+?)\s*是关键(?:。(?P<rest>.+))?$",
        r"^原文里的\s*(?P<quote>.+?)\s*杀伤力太强(?:。(?P<rest>.+))?$",
        r"^原文里的\s*(?P<quote>.+?)\s*很有杀伤力(?:。(?P<rest>.+))?$",
    ]
    for pattern in patterns:
        match = re.match(pattern, cleaned)
        if not match:
            continue
        quote = _strip_ellipsis(match.group("quote")).strip("“”\"' ，。")
        rest = _strip_ellipsis(match.groupdict().get("rest") or "")
        if not quote:
            return rest or cleaned
        if rest:
            return f"关键证据是“{quote}”。{rest}"
        return f"关键证据是“{quote}”。"
    return cleaned


def _why_test_now_template_for_draft(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    anchor_config: dict[str, Any],
) -> str:
    if getattr(draft, "lane", None) == "hot":
        return "关键证据是“{quote}”。{text}"
    return str(anchor_config.get("why_test_now_template") or "").strip()


def _source_anchor_terms(
    draft: ValidationCardDraft | WritingCardDraft,
    *,
    anchor_config: dict[str, Any],
) -> list[str]:
    texts = [
        draft.title,
        draft.summary_line,
        *(quote.text for quote in draft.evidence_quotes),
    ]
    terms: list[str] = []
    seen: set[str] = set()
    stopwords = {item.lower() for item in _string_list(anchor_config.get("anchor_stopwords"))}
    for text in texts:
        for term in _english_anchor_terms(str(text or ""), stopwords=stopwords):
            normalized = term.lower()
            if normalized in seen:
                continue
            if _covered_by_existing_anchor(term, terms):
                continue
            seen.add(normalized)
            terms.append(term)
            if len(terms) >= 6:
                return terms
    return terms


def _english_anchor_terms(text: str, *, stopwords: set[str]) -> list[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+._-]{2,}", text)
    filtered = [token for token in tokens if token.lower() not in stopwords]
    terms: list[str] = []
    for left, right in zip(filtered, filtered[1:]):
        if left[0].isupper() or right[0].isupper() or len(left) >= 5 or len(right) >= 5:
            terms.append(f"{left} {right}")
            break
    terms.extend(filtered)
    return terms


def _covered_by_existing_anchor(term: str, existing_terms: list[str]) -> bool:
    normalized = term.lower()
    return any(normalized != item.lower() and normalized in item.lower().split() for item in existing_terms)


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _source_evidence_text(draft: ValidationCardDraft | WritingCardDraft) -> str:
    parts = [
        draft.title,
        draft.summary_line,
        draft.audience,
        draft.why_now,
        *(quote.text for quote in draft.evidence_quotes),
    ]
    return " ".join(parts).lower()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _string_mapping(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if str(key)}


def _style_smell_contract_lines(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    lines: list[str] = []
    for key, raw in value.items():
        if key == "rewrite_principle":
            continue
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("label") or key).strip()
        terms = _string_list(raw.get("terms"))
        if label and terms:
            lines.append(f"避开{label}：{', '.join(terms)}。")
    principle = str(value.get("rewrite_principle") or "").strip()
    if principle:
        lines.append(principle)
    return lines


__all__ = ["clean_readout_text_for_client", "finalize_signal_readout", "semantic_prompt_extra"]
