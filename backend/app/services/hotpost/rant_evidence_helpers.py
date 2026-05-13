from __future__ import annotations

import re
from typing import Any

from app.services.hotpost.compare_targets import infer_compare_targets
from app.services.hotpost.rules import normalize_text


ASCII_TERM_RE = re.compile(r"[a-z0-9]")
CJK_TEXT_RE = re.compile(r"[\u3400-\u9fff]")

TARGET_TERM_STOPWORDS = {
    "why",
    "issue",
    "issues",
    "problem",
    "problems",
    "complaint",
    "complaints",
    "users",
    "people",
    "大家",
    "用户",
    "问题",
    "抱怨",
    "吐槽",
    "比较",
    "对比",
    "更能",
    "指令",
    "场景",
}

FOCUS_TRANSLATION_HINTS: dict[str, tuple[str, ...]] = {
    "长指令": (
        "long instruction",
        "long prompt",
        "constraints",
        "instruction following",
        "full brief",
        "whole brief",
        "keeps the whole task",
        "retains context",
        "context retention",
        "multi-step prompt",
        "follows all requirements",
        "only does the first half",
        "drops constraints",
        "forgets earlier requirements",
        "loses context mid-task",
        "misses parts of the brief",
        "ignores parts of the prompt",
    ),
    "听懂指令": (
        "follow instructions",
        "instruction following",
        "constraints",
        "keeps track of earlier instructions",
        "retains context",
        "full brief",
        "whole task",
        "multi-step prompts",
        "drops constraints",
        "forgets earlier requirements",
        "loses context",
        "derails after a few steps",
    ),
    "改写成空话": ("generic fluff", "rewriting", "rewrite", "vague output", "boilerplate"),
    "导出崩溃": ("export crash", "crashes", "freezing", "hangs"),
    "退款流程": ("refund process", "refund", "support", "cancel subscription"),
    "项目管理": (
        "project management",
        "issue tracking",
        "task tracking",
        "ticket workflow",
        "planning workflow",
    ),
    "大代码仓": (
        "large repo",
        "large codebase",
        "repo-level",
        "repository scale",
        "big codebase",
    ),
    "大代码库": (
        "large repo",
        "large codebase",
        "repo-level",
        "repository scale",
        "big codebase",
    ),
}


def get_payload_value(item: Any, field: str) -> Any:
    if isinstance(item, dict):
        return item.get(field)
    return getattr(item, field, None)


def looks_like_complaint_quote(text: str) -> bool:
    normalized = normalize_text(text)
    if not normalized:
        return False
    complaint_terms = (
        "bad",
        "broken",
        "broke",
        "bug",
        "bugs",
        "crash",
        "crashes",
        "crashing",
        "confusing",
        "confused",
        "confuse",
        "confuses",
        "expensive",
        "freeze",
        "freezes",
        "freezing",
        "frustrating",
        "generic",
        "fluff",
        "gamble",
        "hard",
        "hate",
        "useless",
        "lose",
        "losing",
        "lost",
        "drop",
        "drops",
        "dropping",
        "dropped",
        "miss",
        "missing",
        "rewrite",
        "rewriting",
        "refund",
        "slow",
        "support",
        "can't trust",
        "cannot trust",
        "usage limit",
        "usage limits",
        "too expensive",
        "unusable",
        "worse",
        "worst",
        "不",
        "不如",
        "崩",
        "很差",
        "客服",
        "空话",
        "退款",
        "难用",
        "听不懂",
    )
    return any(term in normalized for term in complaint_terms)


def normalize_thread_key(value: Any) -> str:
    return normalize_text(str(value or ""))


def extract_focus_hint(payload: dict[str, Any]) -> str:
    debug_info = payload.get("debug_info")
    if isinstance(debug_info, dict):
        return str(debug_info.get("focus") or "").strip()
    return str(getattr(debug_info, "focus", "") or "").strip()


def build_focus_terms(*, query: str, keywords: list[str], focus_hint: str) -> list[str]:
    # 这里不是简单翻译，而是把用户焦点扩成 Reddit 上真实会出现的口语表达。
    raw_terms: list[str] = []
    hint_source = f"{focus_hint} {query}".strip()
    for anchor, translations in FOCUS_TRANSLATION_HINTS.items():
        if anchor in hint_source:
            raw_terms.append(anchor)
            raw_terms.extend(translations)
    if focus_hint:
        raw_terms.extend(re.findall(r"[\u4e00-\u9fff]{2,10}", focus_hint))
        raw_terms.extend(re.findall(r"[a-z0-9][a-z0-9\-/]{2,}", focus_hint.lower()))
    if not raw_terms:
        raw_terms.extend(term for term in re.findall(r"[\u4e00-\u9fff]{2,10}", query) if len(term) >= 2)
        raw_terms.extend(term for term in re.findall(r"[a-z0-9][a-z0-9\-/]{2,}", query.lower()) if len(term) >= 4)
    blocked = {
        normalize_text(term)
        for term in list(keywords)
        + ["为什么", "大家", "什么", "问题", "抱怨", "吐槽", "比较", "更", "最近", "why", "users", "people"]
    }
    terms: list[str] = []
    seen: set[str] = set()
    for term in raw_terms:
        cleaned = str(term or "").strip()
        normalized = normalize_text(cleaned)
        if any(marker in cleaned for marker in ("为什么", "大家", "更能", "大家说")) and cleaned not in FOCUS_TRANSLATION_HINTS:
            continue
        if len(cleaned) < 2 or not normalized or normalized in blocked or normalized in seen:
            continue
        seen.add(normalized)
        terms.append(cleaned)
        if len(terms) >= 14:
            break
    return terms


def build_target_terms(*, query: str, keywords: list[str], compare_requested: bool) -> list[str]:
    candidates = infer_compare_targets(query, keywords) if compare_requested else list(keywords)
    terms: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        cleaned = str(raw or "").strip()
        normalized = normalize_text(cleaned)
        if len(cleaned) < 2 or not normalized or normalized in seen or normalized in TARGET_TERM_STOPWORDS:
            continue
        if not ASCII_TERM_RE.search(normalized) and not CJK_TEXT_RE.search(cleaned):
            continue
        seen.add(normalized)
        terms.append(cleaned)
        if len(terms) >= 4:
            break
    return terms


def contains_term(text: str, term: str) -> bool:
    normalized_term = normalize_text(term)
    if not normalized_term:
        return False
    if not ASCII_TERM_RE.search(normalized_term):
        return normalized_term in text
    pattern = re.escape(normalized_term).replace(r"\ ", r"[\s\-_\/]+")
    return re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", text) is not None


def _ascii_focus_stem(token: str) -> str:
    stem = normalize_text(token)
    if not stem:
        return ""
    for suffix in ("ations", "ation", "ments", "ment", "ingly", "edly", "ing", "ed", "es", "s"):
        if len(stem) - len(suffix) >= 4 and stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def focus_matches_quote(*, normalized_quote: str, focus_terms: list[str]) -> bool:
    # compare 的焦点命中必须尽量稳，先做 literal，再做词干级兜底，避免被表面词形干掉。
    if not focus_terms:
        return True
    quote_stems = {
        _ascii_focus_stem(token)
        for token in re.findall(r"[a-z0-9]+", normalized_quote)
        if len(token) >= 3
    }
    quote_stems.discard("")
    for term in focus_terms:
        normalized_term = normalize_text(term)
        if not normalized_term:
            continue
        if contains_term(normalized_quote, term):
            return True
        if not ASCII_TERM_RE.search(normalized_term):
            continue
        term_stems = [
            _ascii_focus_stem(token)
            for token in re.findall(r"[a-z0-9]+", normalized_term)
            if len(token) >= 3
        ]
        if term_stems and all(token in quote_stems for token in term_stems if token):
            return True
    return False
