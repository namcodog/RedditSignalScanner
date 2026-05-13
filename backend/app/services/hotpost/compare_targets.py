from __future__ import annotations

import re
from typing import Optional, Any

from app.services.hotpost.rules import normalize_text


_CJK_TEXT_RE = re.compile(r"[\u3400-\u9fff]")
_EXPLICIT_ASCII_COMPARE_RE = re.compile(
    r"([A-Za-z][A-Za-z0-9+._ -]{1,30})\s*(?:vs\.?|versus|比)\s*([A-Za-z][A-Za-z0-9+._ -]{1,30})",
    re.IGNORECASE,
)
_EXPLICIT_CJK_COMPARE_RE = re.compile(r"([\u4e00-\u9fff]{2,12})\s*比\s*([\u4e00-\u9fff]{2,12})")
_MIXED_ENTITY_RE = re.compile(
    r"[A-Za-z][A-Za-z0-9+._-]*(?:\s+[A-Za-z0-9+._-]+){0,2}|[\u4e00-\u9fff]{2,12}"
)
_GENERIC_COMPARE_CONTEXT_MARKERS = (
    "项目",
    "管理",
    "任务",
    "场景",
    "流程",
    "体验",
    "问题",
    "指令",
    "代码仓",
    "代码库",
    "工作流",
)


def _normalize_query_parse_target(value:Optional[ str]) ->Optional[ str]:
    cleaned = str(value or "").strip("，。！？?!:：,.;'\"()[]{}<>《》")
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        return None
    if _CJK_TEXT_RE.search(cleaned):
        cleaned = re.split(r"(?:更|最|太|能|会|不|很|就|都|而|并|在|时|的时候)", cleaned, maxsplit=1)[0].strip()
    return cleaned or None


def _looks_like_compare_entity(value: str) -> bool:
    cleaned = str(value or "").strip()
    normalized = normalize_text(cleaned)
    if len(cleaned) < 2 or not normalized:
        return False
    if re.search(r"[A-Za-z]", cleaned):
        return cleaned.lower() not in {
            "project management",
            "long instructions",
            "large repos",
            "large codebase",
        }
    return not any(marker in cleaned for marker in _GENERIC_COMPARE_CONTEXT_MARKERS)


def _keyword_targets_in_query(query: str, keywords: list[str]) -> list[str]:
    normalized_query = normalize_text(query)
    ranked: list[tuple[int, str, str]] = []
    seen: set[str] = set()
    for keyword in keywords:
        cleaned = str(keyword or "").strip()
        normalized = normalize_text(cleaned)
        if len(cleaned) < 2 or not normalized or not _looks_like_compare_entity(cleaned):
            continue
        position = normalized_query.find(normalized)
        if position < 0 or normalized in seen:
            continue
        seen.add(normalized)
        ranked.append((position, cleaned, normalized))
    ranked.sort(key=lambda item: item[0])
    return [item[1] for item in ranked[:2]]


def _coerce_compare_target(candidate:Optional[ str], *, keywords: list[str]) ->Optional[ str]:
    cleaned = _normalize_query_parse_target(candidate)
    if not cleaned:
        return None
    normalized = normalize_text(cleaned)
    for keyword in _keyword_targets_in_query(cleaned, keywords):
        keyword_normalized = normalize_text(keyword)
        if keyword_normalized and keyword_normalized in normalized:
            return keyword
    for keyword in keywords:
        keyword_cleaned = str(keyword or "").strip()
        keyword_normalized = normalize_text(keyword_cleaned)
        if keyword_normalized and (keyword_normalized in normalized or normalized in keyword_normalized):
            return keyword_cleaned
    return cleaned


def infer_compare_targets(query: str, keywords: list[str]) -> list[str]:
    normalized_query = normalize_text(query)
    keyword_targets = _keyword_targets_in_query(query, keywords)
    explicit_ascii = _EXPLICIT_ASCII_COMPARE_RE.search(query)
    if explicit_ascii:
        left = _coerce_compare_target(explicit_ascii.group(1), keywords=keywords)
        right = _coerce_compare_target(explicit_ascii.group(2), keywords=keywords)
        if left and right and normalize_text(left) != normalize_text(right):
            return [left, right]
    explicit_cjk = _EXPLICIT_CJK_COMPARE_RE.search(query)
    if explicit_cjk:
        left = _coerce_compare_target(explicit_cjk.group(1), keywords=keywords)
        right = _coerce_compare_target(explicit_cjk.group(2), keywords=keywords)
        if left and right and normalize_text(left) != normalize_text(right):
            return [left, right]
    if len(keyword_targets) == 2:
        return keyword_targets
    for splitter in (" vs ", " versus ", " 比 ", " 跟 "):
        if splitter not in normalized_query:
            continue
        parts = [part.strip() for part in re.split(re.escape(splitter), query, maxsplit=1) if part.strip()]
        if len(parts) != 2:
            continue
        left = _coerce_compare_target(parts[0], keywords=keywords)
        right = _coerce_compare_target(parts[1], keywords=keywords)
        if left and right and normalize_text(left) != normalize_text(right):
            return [left, right]
    if "比" in query:
        left_text, right_text = query.split("比", 1)
        left_candidates = [
            _coerce_compare_target(item.group(0), keywords=keywords)
            for item in _MIXED_ENTITY_RE.finditer(left_text)
        ]
        right_candidates = [
            _coerce_compare_target(item.group(0), keywords=keywords)
            for item in _MIXED_ENTITY_RE.finditer(right_text)
        ]
        left = next((item for item in reversed(left_candidates) if item), None)
        right = next((item for item in right_candidates if item), None)
        if left and right and normalize_text(left) != normalize_text(right):
            return [left, right]
    targets: list[str] = []
    for keyword in keywords:
        cleaned = str(keyword or "").strip()
        if (
            len(cleaned) >= 2
            and _looks_like_compare_entity(cleaned)
            and cleaned.lower() not in {"why", "better", "than", "issue", "complaint"}
            and cleaned not in targets
        ):
            targets.append(cleaned)
        if len(targets) == 2:
            break
    return targets


def resolve_compare_targets(payload: dict[str, Any], *, query: str, keywords: list[str]) -> list[str]:
    query_parse = payload.get("query_parse")
    if isinstance(query_parse, dict):
        subject = _normalize_query_parse_target(query_parse.get("subject"))
        compare_target = _normalize_query_parse_target(query_parse.get("compare_target"))
        if subject and compare_target and normalize_text(subject) != normalize_text(compare_target):
            return [subject, compare_target]

    debug_info = payload.get("debug_info")
    if hasattr(debug_info, "model_dump"):
        debug_info = debug_info.model_dump()
    if isinstance(debug_info, dict):
        subject = _normalize_query_parse_target(debug_info.get("object"))
        compare_target = _normalize_query_parse_target(debug_info.get("compare_target"))
        if subject and compare_target and normalize_text(subject) != normalize_text(compare_target):
            return [subject, compare_target]

    return infer_compare_targets(query, keywords)


def infer_facet_target(*, text: str, query: str, keywords: list[str]) ->Optional[ str]:
    lowered_text = normalize_text(text)
    for candidate in infer_compare_targets(query, keywords):
        lowered_candidate = normalize_text(candidate)
        if lowered_candidate and lowered_candidate in lowered_text:
            return candidate
    for keyword in keywords:
        cleaned = str(keyword or "").strip()
        lowered_keyword = normalize_text(cleaned)
        if len(cleaned) >= 3 and lowered_keyword and lowered_keyword in lowered_text:
            return cleaned
    return None


__all__ = ["infer_compare_targets", "infer_facet_target", "resolve_compare_targets"]
